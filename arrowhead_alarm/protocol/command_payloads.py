"""Build protocol cmd strings for the Arrowhead alarm panel."""

from arrowhead_alarm.protocol.const import (
    CMD_ARM_AWAY,
    CMD_ARM_STAY,
    CMD_BYPASS,
    CMD_DISARM,
    CMD_MODE,
    CMD_OUTPUT,
    CMD_OUTPUT_OFF,
    CMD_OUTPUT_ON,
    CMD_STATUS,
    CMD_UNBYPASS,
    CMD_VERSION,
)
from arrowhead_alarm.protocol.models import ArmingMode, CommandPayload, ProtocolMode


def build_version_payload() -> CommandPayload:
    """Return the version cmd string."""
    return CommandPayload(CMD_VERSION)


def build_mode_command(mode: ProtocolMode) -> CommandPayload:
    """Return the protocol arming_mode cmd string."""
    return CommandPayload(CMD_MODE, [mode.value])


def build_status_command() -> CommandPayload:
    """Return the status_response cmd string."""
    return CommandPayload(CMD_STATUS)


def build_arm_user_command(user_id: int, pin: int, mode: ArmingMode) -> CommandPayload:
    """Return the user-arm cmd string."""
    keyword = CMD_ARM_AWAY if mode == ArmingMode.AWAY else CMD_ARM_STAY
    return CommandPayload(keyword, [user_id, pin])


def build_disarm_user_command(user_id: int, pin: int) -> CommandPayload:
    """Return the user-disarm cmd string."""
    return CommandPayload(CMD_DISARM, [user_id, pin])


def build_disarm_area_command(area_id: int, pin: int) -> CommandPayload:
    """Return the area-disarm cmd string."""
    return CommandPayload(CMD_DISARM, [area_id, pin])


def build_arm_no_pin_command(mode: ArmingMode) -> CommandPayload:
    """Return the one-push arm cmd string."""
    return CommandPayload(CMD_ARM_AWAY if mode == ArmingMode.AWAY else CMD_ARM_STAY)


def build_arm_area_command(area_id: int, mode: ArmingMode) -> CommandPayload:
    """Return the area-arm cmd string."""
    keyword = CMD_ARM_AWAY if mode == ArmingMode.AWAY else CMD_ARM_STAY
    return CommandPayload(keyword, [area_id])


def build_set_zone_bypass_command(zone_id: int, bypass: bool) -> CommandPayload:
    """Return the zone bypass/unbypass cmd string."""
    return CommandPayload(CMD_BYPASS if bypass else CMD_UNBYPASS, [zone_id])


def build_unbypass_zone_command(zone_id: int) -> CommandPayload:
    """Return the zone unbypass cmd string."""
    return CommandPayload(CMD_UNBYPASS, [zone_id])


def build_set_output_state_command(output_id: int, on: bool) -> CommandPayload:
    """Return the output on/off cmd string."""
    return CommandPayload(CMD_OUTPUT_ON if on else CMD_OUTPUT_OFF, [output_id])


def build_get_output_state_command(output_id: int) -> CommandPayload:
    """Return the output state cmd string."""
    return CommandPayload(CMD_OUTPUT, [output_id])
