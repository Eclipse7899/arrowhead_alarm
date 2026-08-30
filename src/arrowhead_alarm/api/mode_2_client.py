"""Mode 2 client implementation for Arrowhead alarm systems."""

import logging

from ..protocol.commands import arm_area_command_mode_2, disarm_area_command
from ..protocol.models import ArmingMode, ProtocolMode
from ..util import LoginCredentials
from .protocol_client import ProtocolClient

_LOGGER = logging.getLogger(__name__)


class Mode2Client(ProtocolClient):
    """Client for interacting with the alarm system via Protocol Mode 2."""

    mode = ProtocolMode.MODE_2
    delimiter = "\n\r"

    def __init__(
        self,
        host: str,
        port: int,
        credentials: LoginCredentials | None,
        command_timeout: float = 3.0,
        connection_timeout: float = 5.0,
    ) -> None:
        """Initialize the Mode 2 client.

        Args:
            host: Hostname or IP address of the alarm panel.
            port: TCP port number of the alarm panel.
            credentials: Login credentials for authentication, or None.
            command_timeout: The timeout for command operations.
            connection_timeout: The timeout for connection operations.
        """
        super().__init__(host, port, credentials, command_timeout, connection_timeout)

    async def arm_area(self, area: int, mode: ArmingMode) -> None:
        """Arm a specific area in the specified arming mode.

        Args:
            area: The area number to arm.
            mode: The arming mode (e.g., AWAY, STAY).

        Raises:
            Exception: If arming the area fails.
        """
        _LOGGER.info("Arming area %d in %s mode", area, mode)

        result = await self._send_command(arm_area_command_mode_2(area, mode))

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
        """Disarm a specific area using a PIN code.

        Args:
            area: The area number to disarm.
            pin: The PIN code for disarming.

        Raises:
            Exception: If disarming the area fails.
        """
        _LOGGER.info("Disarming area %d", area)

        result = await self._send_command(disarm_area_command(area, pin))

        if result.is_ok:
            _LOGGER.info("Successfully disarmed area %d", area)
        else:
            _LOGGER.error(
                "Error disarming area %d: %s",
                area,
                result.error,
            )
            raise result.error
