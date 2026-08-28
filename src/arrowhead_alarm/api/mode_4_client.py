import logging

from ..util import LoginCredentials
from .protocol_client import ProtocolClient
from ..protocol.commands import arm_area_command_mode_4
from ..protocol.commands import arm_button_command, disarm_user_command, arm_no_pin_command, \
    arm_user_command
from ..protocol.models import ProtocolMode, ArmingMode

_LOGGER = logging.getLogger(__name__)


class Mode4Client(ProtocolClient):
    mode = ProtocolMode.MODE_4
    delimiter = "\n\r"

    def __init__(self, host: str, port: int, credentials: LoginCredentials | None) -> None:
        super().__init__(host, port, credentials)

    async def arm_button(self, arm_mode: ArmingMode) -> None:
        _LOGGER.info(
            "Arming in %s mode without user code",
            arm_mode,
        )

        result = await self._client.request(
            arm_button_command(arm_mode)
        )

        if result.is_ok:
            _LOGGER.info(
                "Successfully armed in %s mode",
                arm_mode,
            )
        else:
            _LOGGER.error(
                "Error arming without user code: %s",
                result.error,
            )
            raise result.error

    async def arm_user_pin(
            self,
            arm_mode: ArmingMode,
            user: int,
            pin: int,
    ) -> None:
        _LOGGER.info(
            "Arming in %s mode as user %d",
            arm_mode,
            user,
        )

        result = await self._client.request(
            arm_user_command(user, pin, arm_mode)
        )

        if result.is_ok:
            _LOGGER.info(
                "Successfully armed as user %d",
                user,
            )
        else:
            _LOGGER.error(
                "Error arming as user %d: %s",
                user,
                result.error,
            )
            raise result.error

    async def arm_as_user(
            self,
            user: int,
            mode: ArmingMode,
    ) -> None:
        _LOGGER.info(
            "Arming in %s mode as user %d (no PIN)",
            mode,
            user,
        )

        result = await self._client.request(
            arm_no_pin_command(user, mode)
        )

        if result.is_ok:
            _LOGGER.info(
                "Successfully armed as user %d",
                user,
            )
        else:
            _LOGGER.error(
                "Error arming as user %d: %s",
                user,
                result.error,
            )
            raise result.error

    async def arm_area(
            self,
            area: int,
            mode: ArmingMode,
    ) -> None:
        _LOGGER.info(
            "Arming area %d in %s mode",
            area,
            mode,
        )

        command = arm_area_command_mode_4(area, mode)
        result = await self._client.request(command)

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

    async def disarm(
            self,
            user: int,
            pin: int,
    ) -> None:
        _LOGGER.info(
            "Disarming as user %d",
            user,
        )

        result = await self._client.request(
            disarm_user_command(user, pin)
        )

        if result.is_ok:
            _LOGGER.info(
                "Successfully disarmed as user %d",
                user,
            )
        else:
            _LOGGER.error(
                "Error disarming as user %d: %s",
                user,
                result.error,
            )
            raise result.error
