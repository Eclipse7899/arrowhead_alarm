"""Base protocol client module for Arrowhead alarm systems."""

import asyncio
import logging
from abc import ABC
from dataclasses import replace
from typing import Callable, TypeVar

from arrowhead_alarm.protocol.types import Command

from ..protocol.commands import (
    bypass_zone_command,
    mode_command,
    output_state_command,
    set_output_command,
    unbypass_zone_command,
    version_command,
)
from ..protocol.defaults import get_default_state
from ..protocol.models import PanelState, PanelVersion, ProtocolMode
from ..protocol.transformers import panel_operation_transformer
from ..transport.authenticated_session import AuthenticatedSession
from ..transport.command_client import CommandClient
from ..transport.tcp import TcpTransport
from ..util import LoginCredentials, Publisher

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


class ProtocolClient(ABC):
    """The base client for a specific ECI protocol mode."""

    mode: ProtocolMode

    def __init__(
        self,
        host: str,
        port: int,
        credentials: LoginCredentials | None,
        command_timeout: float,
        connection_timeout: float,
    ) -> None:
        """Initialize the protocol client.

        Args:
            host: Hostname or IP address of the alarm panel.
            port: TCP port number of the alarm panel.
            credentials: Login credentials for authentication, or None.
            command_timeout: The timeout for command operations.
            connection_timeout: The timeout for connection operations.
        """
        session = AuthenticatedSession(TcpTransport(host, port), credentials)
        self._timeout = command_timeout
        self._connection_timeout = connection_timeout

        self._state: PanelState = get_default_state()
        self._client = CommandClient(session)
        self.version: PanelVersion | None = None
        self.state_publisher: Publisher[PanelState] = Publisher()

    @property
    def state(self) -> PanelState:
        """Get the current state of the panel."""
        return self._state

    def _update_state(self, mutate_func: Callable[[PanelState], PanelState]) -> None:
        """Update the internal state of the panel."""
        new_state = mutate_func(self._state)
        self._state = new_state
        self.state_publisher.dispatch(new_state)

    async def connect(self) -> None:
        """Connect the protocol client to the alarm panel."""
        await asyncio.wait_for(self._client.connect(), timeout=self._connection_timeout)
        await self._set_mode()
        self.version = await self.query_version()
        self._client.subscribe(self._handle_event)

    async def disconnect(self) -> None:
        """Disconnect from the alarm panel."""
        await asyncio.wait_for(self._client.disconnect(), timeout=self._connection_timeout)
        self._client.unsubscribe(self._handle_event)

    async def _send_command(self, command: Command[_T]) -> _T:
        """Send a command to the alarm panel."""
        return await asyncio.wait_for(self._client.request(command), timeout=self._timeout)

    def _handle_event(self, data: str) -> None:
        """Handle incoming events from the panel."""
        _LOGGER.debug("Received event: %s", data)

        result = panel_operation_transformer(data)
        if result.is_ok:
            self._update_state(result.value)
        else:
            _LOGGER.warning("Message was not parsed as an event: %s, error: %s", data, result.error)

    async def _set_mode(self) -> None:
        """Set the protocol mode."""
        _LOGGER.info("Setting protocol mode to %s", self.mode)
        result = await self._send_command(mode_command(self.mode))
        if result.is_ok:
            _LOGGER.info("Protocol mode set to %s", self.mode)
        else:
            _LOGGER.error("Error setting protocol mode: %s", result.error)
            raise result.error

    async def query_version(self) -> PanelVersion:
        """Query the alarm panel version.

        Returns:
            The panel version information.

        Raises:
            Exception: If querying the version fails.
        """
        resp = await self._send_command(version_command())
        if resp.is_ok:
            return resp.value
        raise resp.error

    async def output_on(self, output_number: int) -> None:
        """Turn on a specific output.

        Args:
            output_number: The output number to turn on.

        Raises:
            Exception: If turning on the output fails.
        """
        _LOGGER.info("Turning on output %d", output_number)

        if output_number not in self._state.outputs:
            _LOGGER.error("Output %d does not exist in the current state", output_number)
            raise ValueError(f"Output {output_number} does not exist in the current state")

        result = await self._send_command(set_output_command(output_number, True))
        if result.is_ok:
            _LOGGER.info("Output %d turned on", output_number)
            self._update_state(
                lambda state: replace(
                    state,
                    outputs={
                        **state.outputs,
                        output_number: replace(state.outputs[output_number], on=True),
                    },
                )
            )
        else:
            _LOGGER.error("Error turning on output %d: %s", output_number, result.error)
            raise result.error

    async def output_off(self, output_number: int) -> None:
        """Turn off a specific output.

        Args:
            output_number: The output number to turn off.

        Raises:
            Exception: If turning the output off fails.
        """
        _LOGGER.info("Turning off output %d", output_number)

        if output_number not in self._state.outputs:
            _LOGGER.error("Output %d does not exist in the current state", output_number)
            raise ValueError(f"Output {output_number} does not exist in the current state")

        result = await self._send_command(set_output_command(output_number, False))
        if result.is_ok:
            _LOGGER.info("Output %d turned off", output_number)
            self._state.outputs[output_number].on = False
        else:
            _LOGGER.error("Error turning off output %d: %s", output_number, result.error)
            raise result.error

    async def query_output(self, output_number: int) -> bool:
        """Query the state of a specific output.

        Args:
            output_number: The output number to query.

        Returns:
            True if the output is active, False otherwise.

        Raises:
            Exception: If querying the output fails.
        """
        _LOGGER.info("Querying output %d state", output_number)

        if output_number not in self._state.outputs:
            _LOGGER.error("Output %d does not exist in the current state", output_number)
            raise ValueError(f"Output {output_number} does not exist in the current state")

        result = await self._send_command(output_state_command(output_number))
        if result.is_ok:
            _LOGGER.info("Output %d state queried", output_number)
            self._state.outputs[output_number].on = result.value
            return result.value
        _LOGGER.error("Error querying output %d: %s", output_number, result.error)
        raise result.error

    async def bypass_zone(self, zone_number: int) -> None:
        """Bypass a specific zone.

        Args:
            zone_number: The zone number to bypass.

        Raises:
            Exception: If bypassing the zone fails.
        """
        _LOGGER.info("Bypassing zone %d", zone_number)

        if zone_number not in self._state.zones:
            _LOGGER.error("Zone %d does not exist in the current state", zone_number)
            raise ValueError(f"Zone {zone_number} does not exist in the current state")

        result = await self._send_command(bypass_zone_command(zone_number))
        if result.is_ok:
            _LOGGER.info("Zone %d bypassed", zone_number)
            self._state.zones[zone_number].bypassed = True
        else:
            _LOGGER.error("Error bypassing zone %d: %s", zone_number, result.error)
            raise result.error

    async def unbypass_zone(self, zone_number: int) -> None:
        """Unbypass a specific zone.

        Args:
            zone_number: The zone number to unbypass.

        Raises:
            Exception: If unbypassing the zone fails.
        """
        if zone_number not in self._state.zones:
            _LOGGER.error("Zone %d does not exist in the current state", zone_number)
            raise ValueError(f"Zone {zone_number} does not exist in the current state")

        _LOGGER.info("Unbypassing zone %d", zone_number)
        result = await self._send_command(unbypass_zone_command(zone_number))
        if result.is_ok:
            _LOGGER.info("Zone %d unbypassed", zone_number)
            self._state.zones[zone_number].bypassed = False
        else:
            _LOGGER.error("Error unbypassing zone %d: %s", zone_number, result.error)
            raise result.error
