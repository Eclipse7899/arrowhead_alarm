import logging
from abc import ABC

from ..protocol.commands import version_command, set_output_command, bypass_zone_command, \
    unbypass_zone_command, \
    output_state_command
from ..protocol.models import ProtocolMode, PanelVersion
from ..transport.authenticated_session import AuthenticatedSession
from ..transport.command_client import CommandClient
from ..transport.tcp import TcpTransport
from ..util import LoginCredentials

_LOGGER = logging.getLogger(__name__)


class ProtocolClient(ABC):
    """Base client for a specific ECI protocol mode."""

    mode: ProtocolMode

    def __init__(self, host: str, port: int, credentials: LoginCredentials | None) -> None:
        session = AuthenticatedSession(TcpTransport(host, port), credentials)
        self._client = CommandClient(session)

    async def query_version(self) -> PanelVersion:
        resp = await self._client.request(version_command())
        if resp.is_ok:
            return resp.value
        raise resp.error

    async def output_on(self, output_number: int) -> None:
        _LOGGER.info("Turning on output %d", output_number)
        result = await self._client.request(set_output_command(output_number, True))
        if result.is_ok:
            _LOGGER.info("Output %d turned on", output_number)
        else:
            _LOGGER.error("Error turning on output %d: %s", output_number, result.error)
            raise result.error

    async def output_off(self, output_number: int) -> None:
        _LOGGER.info("Turning off output %d", output_number)
        result = await self._client.request(set_output_command(output_number, False))
        if result.is_ok:
            _LOGGER.info("Output %d turned off", output_number)
        else:
            _LOGGER.error("Error turning off output %d: %s", output_number, result.error)
            raise result.error

    async def query_output(self, output_number: int) -> bool:
        _LOGGER.info("Querying output %d state", output_number)
        result = await self._client.request(output_state_command(output_number))
        if result.is_ok:
            return result.value
        _LOGGER.error("Error querying output %d: %s", output_number, result.error)
        raise result.error

    async def bypass_zone(self, zone_number: int) -> None:
        _LOGGER.info("Bypassing zone %d", zone_number)
        result = await self._client.request(bypass_zone_command(zone_number))
        if result.is_ok:
            _LOGGER.info("Zone %d bypassed", zone_number)
        else:
            _LOGGER.error("Error bypassing zone %d: %s", zone_number, result.error)
            raise result.error

    async def unbypass_zone(self, zone_number: int) -> None:
        _LOGGER.info("Unbypassing zone %d", zone_number)
        result = await self._client.request(unbypass_zone_command(zone_number))
        if result.is_ok:
            _LOGGER.info("Zone %d unbypassed", zone_number)
        else:
            _LOGGER.error("Error unbypassing zone %d: %s", zone_number, result.error)
            raise result.error
