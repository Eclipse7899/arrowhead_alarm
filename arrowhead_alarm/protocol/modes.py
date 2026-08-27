"""Protocol mode capabilities, and resolution for Arrowhead alarm panels."""

from dataclasses import dataclass
from typing import Final

from arrowhead_alarm.protocol.models import ProtocolMode, VersionInfo
from arrowhead_alarm.types import (
    AlarmCapabilities,
    ArmingCapabilities,
    DisarmingCapabilities,
)


@dataclass(frozen=True)
class ModeCapabilities:
    """Encapsulates all capabilities and metadata for a protocol mode.

    This object represents the complete configuration of a protocol mode,
    including the mode itself, its delimiter, and supported capabilities.
    """

    mode: ProtocolMode
    delimiter: str
    capabilities: AlarmCapabilities

    def supports_user_commands(self) -> bool:
        """Check if this arming_mode supports user ID/PIN-based commands.

        User commands include arm_user, disarm with user credentials.

        Returns:
            True if user commands are supported, False otherwise.

        """
        return self.mode == ProtocolMode.MODE_1

    def supports_area_commands(self) -> bool:
        """Check if this arming_mode supports area-based commands.

        Area commands include arm_area, disarm_area.

        Returns:
            True if area commands are supported, False otherwise.

        """
        return self.mode in (ProtocolMode.MODE_2, ProtocolMode.MODE_4)

    def supports_one_push_arm(self) -> bool:
        """Check if this arming_mode supports one-push arming.

        One-push arming allows arming without specifying user ID or area.

        Returns:
            True if one-push arming is supported, False otherwise.

        """
        return ArmingCapabilities.ONE_PUSH in self.capabilities.arming

    def supports_individual_area_arming(self) -> bool:
        """Check if individual area arming is supported.

        Returns:
            True if individual area arming is supported, False otherwise.

        """
        return ArmingCapabilities.INDIVIDUAL_AREA in self.capabilities.arming

    def supports_all_zones_ready_status(self) -> bool:
        """Check if all zones ready status_response is available.

        Returns:
            True if all zones ready status_response is available, False otherwise.

        """
        return self.capabilities.all_zones_ready_status

    def __str__(self) -> str:
        """Return string representation of arming_mode capabilities."""
        return (
            f"ModeCapabilities("
            f"arming_mode={self.mode.value}, "
            f"delimiter={repr(self.delimiter)}"
            f")"
        )


class ModeResolver:
    """Resolves and provides protocol arming_mode information.

    This class serves as the single factory for creating ModeCapabilities
    instances and determining the best arming_mode for a given panel.
    """

    # Mapping of ProtocolMode to their corresponding delimiters
    DELIMITERS: Final[dict[ProtocolMode, str]] = {
        ProtocolMode.MODE_1: "\r\n",
        ProtocolMode.MODE_2: "\n",
        ProtocolMode.MODE_3: "\n",
        ProtocolMode.MODE_4: "\n",
    }

    @staticmethod
    def get_mode_capabilities(mode: ProtocolMode) -> ModeCapabilities:
        """Get complete arming_mode capabilities for a protocol arming_mode.

        Args:
            mode: The protocol arming_mode to get capabilities for.

        Returns:
            ModeCapabilities object containing all arming_mode-specific information.

        Raises:
            NotImplementedError: If the arming_mode is not supported.

        """
        return ModeCapabilities(
            mode=mode,
            delimiter=ModeResolver.get_delimiter(mode),
            capabilities=ModeResolver.get_capabilities(mode),
        )

    @staticmethod
    def get_delimiter(mode: ProtocolMode) -> str:
        r"""Get the line delimiter for a protocol arming_mode.

        Args:
            mode: The protocol arming_mode.

        Returns:
            The line delimiter string (e.g., "\r\n" or "\n").

        Raises:
            NotImplementedError: If the arming_mode is not supported.

        """
        if mode not in ModeResolver.DELIMITERS:
            raise NotImplementedError(f"Unsupported protocol arming_mode: {mode}")
        return ModeResolver.DELIMITERS[mode]

    @staticmethod
    def get_capabilities(mode: ProtocolMode) -> AlarmCapabilities:
        r"""Get the alarm capabilities for a protocol arming_mode.

        Each protocol arming_mode has different capabilities for arming, disarming,
        and status_response monitoring.

        Args:
            mode: The protocol arming_mode.

        Returns:
            AlarmCapabilities object describing what this arming_mode can do.

        Raises:
            NotImplementedError: If the arming_mode is not supported.

        """
        capabilities = AlarmCapabilities()

        match mode:
            case ProtocolMode.MODE_1:
                # Mode 1: Default arming_mode, no acknowledgments
                # Supports user ID/PIN commands and one-push arming
                # Provides zone ready status_response
                capabilities.all_zones_ready_status = True
                capabilities.arming = (
                        ArmingCapabilities.USER_ID_AND_PIN | ArmingCapabilities.ONE_PUSH
                )
                capabilities.disarming = DisarmingCapabilities.USER_ID_AND_PIN

            case ProtocolMode.MODE_2:
                # Mode 2: AAP arming_mode, with acknowledgments
                # Supports area-based commands only
                capabilities.all_zones_ready_status = False
                capabilities.arming = ArmingCapabilities.INDIVIDUAL_AREA
                capabilities.disarming = (
                    DisarmingCapabilities.INDIVIDUAL_AREA_WITH_USER_PIN
                )

            case ProtocolMode.MODE_3:
                # Mode 3: Permaconn arming_mode, with acknowledgments
                # Similar to Mode 2 but maintains persistent connection
                capabilities.all_zones_ready_status = False
                capabilities.arming = ArmingCapabilities.INDIVIDUAL_AREA
                capabilities.disarming = (
                    DisarmingCapabilities.INDIVIDUAL_AREA_WITH_USER_PIN
                )

            case ProtocolMode.MODE_4:
                # Mode 4: Home Automation arming_mode, no acknowledgments
                # Supports both user ID/PIN and area-based commands
                # Available in ECi FW 10.3.50+
                capabilities.all_zones_ready_status = False
                capabilities.arming = (
                        ArmingCapabilities.INDIVIDUAL_AREA
                        | ArmingCapabilities.USER_ID_AND_PIN
                )
                capabilities.disarming = DisarmingCapabilities.USER_ID_AND_PIN

            case _:
                raise NotImplementedError(f"Unsupported protocol arming_mode: {mode}")

        return capabilities

    @staticmethod
    def resolve_best_mode(firmware_version: VersionInfo) -> ProtocolMode:
        """Resolve the best protocol arming_mode for a given firmware version.

        This method determines which protocol arming_mode to use based on the panel's
        firmware version. Newer firmware supports more advanced modes.

        Args:
            firmware_version: The panel's firmware version.

        Returns:
            The recommended ProtocolMode for this firmware version.

        """
        # Mode 4 (Home Automation) is available from firmware 10.3.50 onwards
        if ModeResolver.is_mode_4_supported(firmware_version):
            return ProtocolMode.MODE_4
        return ProtocolMode.MODE_2

    @staticmethod
    def is_mode_4_supported(firmware_version: VersionInfo) -> bool:
        """Check if Protocol Mode 4 is supported by the firmware version.

        Args:
            firmware_version: The panel's firmware version.

        Returns:
            True if Mode 4 is supported, False otherwise.

        """
        return firmware_version >= VersionInfo(10, 3, 50)
