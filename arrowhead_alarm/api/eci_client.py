import asyncio
import logging
from asyncio import Future
from typing import Callable, TypeVar

from arrowhead_alarm.collectors import LineCollector
from arrowhead_alarm.protocol import ProtocolMode, Request, ProtocolError, CommandPayload
from arrowhead_alarm.protocol.command_payloads import (
    build_arm_area_command,
    build_arm_no_pin_command,
    build_arm_user_command,
    build_mode_command,
    build_set_output_state_command,
    build_set_zone_bypass_command,
)
from arrowhead_alarm.protocol.commands import (
    arm_area_collector,
    arm_user_collector,
    output_state_collector,
    version_response_collector,
    bypass_zone_collector, set_output_collector, mode_collector,
)
from arrowhead_alarm.protocol.defaults import get_default_state
from arrowhead_alarm.protocol.exceptions import ProtocolErrorCode
from arrowhead_alarm.protocol.models import ResponseHandler, PanelVersion, ArmingMode
from arrowhead_alarm.protocol.modes import ModeResolver
from arrowhead_alarm.protocol.transformers import panel_operation_transformer
from arrowhead_alarm.protocol.util import get_protocol_exception
from arrowhead_alarm.transport.authenticated_session import AuthenticatedSession
from arrowhead_alarm.transport.request_client import RequestClient
from arrowhead_alarm.transport.tcp import TcpTransport
from arrowhead_alarm.types import LoginCredentials, Collector, Result, Done, Waiting, UserPin, CollectorPipeline, \
    Success, Failure
from arrowhead_alarm.util import is_mode_4_supported

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")
_U = TypeVar("_U")

class EciClient:
    def __init__(
        self,
        host: str,
        port: int,
        credentials: LoginCredentials | None = None
    ):
        self.request_client = RequestClient(
            AuthenticatedSession(
                TcpTransport(host, port),
                credentials
            )
        )

        self.mode = ProtocolMode.MODE_1
        self.version: PanelVersion | None = None
        self._state = get_default_state()


    async def connect(self) -> None:
        """Connect to the panel."""
        await self.request_client.connect()
        await self._auto_set_mode()
        self.register_state_callback()

    async def disconnect(self) -> None:
        """Disconnect from the panel."""
        await self.request_client.disconnect()


    def register_state_callback(self) -> None:
        """Register a callback to be called when the panel version changes."""
        delimiter = ModeResolver.get_delimiter(self.mode)
        collector = (
            CollectorPipeline.of_string()
            .bind(LineCollector(delimiter=delimiter).feed)
            .map(panel_operation_transformer)
            .flatten()
        )

        def feed(response: str) -> None:
            collection_result = collector(response)
            match collection_result:
                case Done(line):
                    match line:
                        case Success(state_transformer):
                            state_transformer(self._state)
                        case Failure():
                            pass
                case Waiting():
                    pass

        self.request_client.subscribe(feed)


    @staticmethod
    def get_collector_callback(request: str, collector: Collector[str, Result[_T, ProtocolErrorCode]], callback: Callable[[Result[_T, ProtocolError]], None]) -> Callable[[str], None]:
        def feed(response: str) -> None:
            collection_result = collector(response)
            match collection_result:
                case Done(result):
                    callback(
                        result.map_error(
                            lambda code: get_protocol_exception(code, request, response)
                        )
                    )
                case Waiting():
                    pass
        return feed


    async def _send_request(self, payload: CommandPayload, collector: Collector[str, Result[_T, ProtocolErrorCode]], mode: ProtocolMode) -> Result[_T, ProtocolError]:
        """Return a request that resolves with the transformed response."""
        delimiter = ModeResolver.get_delimiter(mode)
        new_collector = (CollectorPipeline.of_string()
            .bind(LineCollector(delimiter=delimiter).feed)
            .bind(collector)
            .flatten()
        )
        future: Future[Result[_T, ProtocolError]] = asyncio.get_running_loop().create_future()
        request_data = payload.build()
        callback = self.get_collector_callback(
            request_data,
            new_collector,
            lambda value: future.set_result(value)
        )
        req = Request(
            request_data=request_data,
            response=ResponseHandler(
                callback=callback,
                future=future
            )
        )
        return await self.request_client.request(req)


    async def query_panel_version(self) -> PanelVersion:
        """Query the panel for its firmware version."""
        _LOGGER.info("Querying panel version")
        command = build_mode_command(self.mode)
        collector = version_response_collector()

        resp = await self._send_request(command, collector, self.mode)
        if resp.is_ok:
            _LOGGER.info("Panel version: %s", resp.value)
            return resp.value
        else:
            _LOGGER.error("Error querying panel version: %s", resp.error)
            raise resp.error

    async def arm_no_pin(self, mode: ArmingMode) -> None:
        """Arm the alarm in away mode."""
        _LOGGER.info("Attempting to arm in away mode without user code")
        if self.mode != ProtocolMode.MODE_1:
            _LOGGER.error(
                "Protocol mode %d does not support user commands",
                self.mode,
            )
            return
        command = build_arm_no_pin_command(mode)
        collector = arm_user_collector(mode)

        result = await self._send_request(command, collector, self.mode)
        if result.is_ok:
            _LOGGER.info("Successfully armed in away mode without user code")
        else:
            _LOGGER.error(
                "Error sending ARMUSER command without user code: %s",
                result.error,
            )
            raise result.error

    async def arm_user(self, user: UserPin, mode: ArmingMode) -> None:
        """Arm the alarm in away mode using specific user credentials."""
        _LOGGER.info(
            "Attempting to arm in away mode using user code: %s, pin: %s",
            user.user_id,
            user.pin,
        )
        if self.mode != ProtocolMode.MODE_1:
            _LOGGER.error(
                "Protocol mode %d does not support user commands",
                self.mode,
            )
            return
        command = build_arm_user_command(user.user_id, user.pin, mode)
        collector = arm_user_collector(mode)

        result = await self._send_request(command, collector, self.mode)
        if result.is_ok:
            _LOGGER.info("Successfully armed in away mode using user code: %s", user.user_id)
        else:
            _LOGGER.error(
                "Error sending ARMUSER command for user code %s: %s",
                user.user_id,
                result.error,
            )
            raise result.error

    async def arm_area(self, area_number: int, mode: ArmingMode) -> None:
        """Arm a specific area in away mode."""
        _LOGGER.info("Attempting to arm area %d in away mode", area_number)
        if self.mode != ProtocolMode.MODE_1:
            _LOGGER.error(
                "Protocol mode %d does not support area commands",
                self.mode,
            )
            return
        command = build_arm_area_command(area_number, mode)
        collector = arm_area_collector(mode)

        result = await self._send_request(command, collector, self.mode)
        if result.is_ok:
            _LOGGER.info("Successfully armed area %d in away mode", area_number)
        else:
            _LOGGER.error(
                "Error sending ARMAREA command for area %d: %s",
                area_number,
                result.error,
            )
            raise result.error

    async def set_zone_bypass(self, zone_number: int, bypass: bool) -> None:
        """Bypass a zone.

        Args:
            zone_number: Zone number to bypass.
            bypass: True to bypass, False to unbypass.

        """
        _LOGGER.info(
            "%s bypass for zone %d",
            "Setting" if bypass else "Removing",
            zone_number,
        )

        if self.mode != ProtocolMode.MODE_1:
            _LOGGER.error(
                "Protocol mode %d does not support zone bypass commands",
                self.mode,
            )
            return
        command = build_set_zone_bypass_command(zone_number, bypass)
        collector = bypass_zone_collector()

        result = await self._send_request(command, collector, self.mode)
        if result.is_ok:
            _LOGGER.info(
                "%s bypass for zone %d successful",
                "Setting" if bypass else "Removing",
                zone_number,
            )
        else:
            _LOGGER.error(
                "Error sending SETZONEBYPASS command for zone %d: %s",
                zone_number,
                result.error,
            )
            raise result.error

    async def set_output_state(self, output_number: int, on: bool) -> None:
        """Turn output on permanently."""
        _LOGGER.info("Turning on output %d", output_number)
        if output_number > len(self._state.outputs):
            _LOGGER.warning(
                "Output number %d exceeds max outputs %d",
                output_number,
                len(self._state.outputs),
            )
        req = build_set_output_state_command(output_number, on)
        collector = set_output_collector(on)
        resp = await self._send_request(req, collector, self.mode)
        if resp.is_ok:
            _LOGGER.info("Output %d turned on", output_number)
            self._state.outputs[output_number].on = on
        else:
            _LOGGER.error(
                "Error turning on output %d: %s",
                output_number,
                resp.error,
            )
            raise resp.error

    async def get_output_state(self, output_number: int) -> bool:
        """Get the current state of an output."""
        _LOGGER.info("Getting state of output %d", output_number)
        if output_number > len(self._state.outputs):
            _LOGGER.warning(
                "Output number %d exceeds max outputs %d",
                output_number,
                len(self._state.outputs),
            )
        req = build_set_output_state_command(output_number, False)
        collector = output_state_collector()
        resp = await self._send_request(req, collector, self.mode)
        if resp.is_ok:
            _LOGGER.info("Output %d state: %s", output_number, resp.value)
            self._state.outputs[output_number].on = resp.value
            return resp.value
        else:
            _LOGGER.error(
                "Error getting state of output %d: %s",
                output_number,
                resp.error,
            )
            raise resp.error

    async def _auto_set_mode(self) -> None:
        """Automatically set the best protocol mode based on panel capabilities."""
        if self.version is None:
            _LOGGER.error("Cannot set protocol mode: panel version unknown")
            raise RuntimeError("Panel version unknown")
        if is_mode_4_supported(self.version.firmware_version):
            _LOGGER.info("Panel supports Mode 4, setting protocol mode to 4")
            return await self._set_mode(ProtocolMode.MODE_4)
        else:
            _LOGGER.info("Panel does not support Mode 4, setting protocol mode to 2")
            return await self._set_mode(ProtocolMode.MODE_2)

    async def _set_mode(self, mode: ProtocolMode) -> None:
        """Set the protocol mode of the panel."""
        _LOGGER.info("Setting protocol mode to %d", mode.value)
        command = build_mode_command(mode)
        collector = mode_collector()
        resp = await self._send_request(command, collector, mode)
        if resp.is_ok:
            _LOGGER.info("Protocol mode set to %d", mode.value)
            self.mode = mode
        else:
            _LOGGER.error("Error setting protocol mode to %d: %s", mode.value, resp.error)
            raise resp.error




