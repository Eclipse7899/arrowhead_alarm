import logging

from ..util import LoginCredentials
from .protocol_client import ProtocolClient
from ..protocol.commands import arm_area_command_mode_2, disarm_area_command
from ..protocol.models import ProtocolMode, ArmingMode

_LOGGER = logging.getLogger(__name__)


class Mode2Client(ProtocolClient):
    mode = ProtocolMode.MODE_2
    delimiter = "\n\r"

    def __init__(self, host: str, port: int, credentials: LoginCredentials | None) -> None:
        super().__init__(host, port, credentials)

    async def arm_area(self, area: int, mode: ArmingMode) -> None:
        _LOGGER.info("Arming area %d in %s mode", area, mode)

        result = await self._client.request(
            arm_area_command_mode_2(area, mode)
        )

        if result.is_ok:
            _LOGGER.info(
                "Successfully armed area %d in %s mode",
                area,
                mode,
            )
        else:
            _LOGGER.error(
                "Error arming area %d in %s mode: %s",
                area,
                mode,
                result.error,
            )
            raise result.error

    async def disarm(self, area: int, pin: int) -> None:
        _LOGGER.info("Disarming area %d", area)

        result = await self._client.request(
            disarm_area_command(area, pin)
        )

        if result.is_ok:
            _LOGGER.info("Successfully disarmed area %d", area)
        else:
            _LOGGER.error(
                "Error disarming area %d: %s",
                area,
                result.error,
            )
            raise result.error
