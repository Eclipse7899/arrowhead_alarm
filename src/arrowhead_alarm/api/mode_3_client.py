"""Mode 3 client implementation for Arrowhead alarm systems."""

import logging

from ..protocol.commands import (
    arm_button_command,
    arm_no_pin_command,
    arm_user_command,
    disarm_user_command,
)
from ..protocol.models import ArmingMode, ProtocolMode
from ..util import LoginCredentials
from .protocol_client import ProtocolClient

_LOGGER = logging.getLogger(__name__)


class Mode3Client(ProtocolClient):
    """Client for interacting with the alarm system via Protocol Mode 3."""

    mode = ProtocolMode.MODE_3
    delimiter = "\n\r"

    def __init__(
        self, host: str, port: int, credentials: LoginCredentials | None
    ) -> None:
        """Initialize the Mode 3 client.

        Args:
            host: Hostname or IP address of the alarm panel.
            port: TCP port number of the alarm panel.
            credentials: Login credentials for authentication, or None.
        """
        super().__init__(host, port, credentials)

    async def arm_button(self, arm_mode: ArmingMode) -> None:
        """Arm the system using single button arming without a user code.

        Args:
            arm_mode: The arming mode (e.g., AWAY, STAY).

        Raises:
            Exception: If arming fails.
        """
        _LOGGER.info(
            "Arming in %s mode without user code",
            arm_mode,
        )

        result = await self._client.request(arm_button_command(arm_mode))

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
        """Arm the system using a specific user ID and PIN.

        Args:
            arm_mode: The arming mode (e.g., AWAY, STAY).
            user: The user slot/ID number.
            pin: The user's PIN code.

        Raises:
            Exception: If arming fails.
        """
        _LOGGER.info(
            "Arming in %s mode as user %d",
            arm_mode,
            user,
        )

        result = await self._client.request(arm_user_command(user, pin, arm_mode))

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
        """Arm the system as a specific user without requiring a PIN.

        Args:
            user: The user slot/ID number.
            mode: The arming mode (e.g., AWAY, STAY).

        Raises:
            Exception: If arming fails.
        """
        _LOGGER.info(
            "Arming in %s mode as user %d (no PIN)",
            mode,
            user,
        )

        result = await self._client.request(arm_no_pin_command(user, mode))

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

    async def disarm(
        self,
        user: int,
        pin: int,
    ) -> None:
        """Disarm the system using a user ID and PIN.

        Args:
            user: The user slot/ID number.
            pin: The user's PIN code.

        Raises:
            Exception: If disarming fails.
        """
        _LOGGER.info(
            "Disarming as user %d",
            user,
        )

        result = await self._client.request(disarm_user_command(user, pin))

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
