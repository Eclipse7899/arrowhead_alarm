"""Commands for interacting with the Arrowhead alarm panel."""
from typing import TypeVar, Callable

from arrowhead_alarm.protocol import ProtocolError
from .const import CMD_DISARM, CMD_MODE, CMD_OUTPUT, CMD_ARM_AWAY, CMD_ARM_STAY, \
    CMD_BYPASS, CMD_UNBYPASS, CMD_OUTPUT_ON, CMD_OUTPUT_OFF, CMD_VERSION
from .exceptions import ProtocolErrorCode
from .models import (
    PanelVersion,
    ProtocolMode, ArmingMode, CommandPayload,
)
from .transformers import (
    boolean_response_transformer,
    cmd_result_transformer,
    create_version_transformer,
    int_response_transformer,
    mode_response_transformer, get_cmd_keyword_transformer
)
from .types import ResultPipeline, Collector, CollectorPipeline, Result, Success, CollectorContext, Command
from .util import convert_to_response, get_protocol_exception

_T = TypeVar("_T")


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


def _get_cmd_command(request: str, transformer: Callable[[str], Result[_T, ProtocolErrorCode]]) -> Collector[
    str, Result[_T, ProtocolError]]:
    return (
        CollectorPipeline.of_string()
        .map(CollectorContext.of_value)
        .map(
            lambda context: context.map(transformer)
        )
        .map(
            lambda context: context.data.map_error(
                lambda error: get_protocol_exception(
                    error,
                    request,
                    context.original
                )
            )
        )
        .unwrap()
    )


def _get_cmd_result_pipeline(
        command_keyword: str,
) -> ResultPipeline[str, str, ProtocolErrorCode]:
    """Create an _collector that processes a cmd response."""
    return (
        ResultPipeline(convert_to_response)
        .map_error(lambda error: ProtocolErrorCode.INVALID_RESPONSE)
        .bind(get_cmd_keyword_transformer(command_keyword))
        .bind(cmd_result_transformer)
    )


def _get_int_command(keyword: str, payload: str) -> Command[Result[int, ProtocolError]]:
    response_parser = (
        _get_cmd_result_pipeline(keyword)
        .bind(int_response_transformer)
        .unwrap()
    )

    return Command(
        payload,
        _get_cmd_command(payload, response_parser)
    )


def version_command() -> Command[Result[PanelVersion, ProtocolError]]:
    response_parser = (
        _get_cmd_result_pipeline(CMD_VERSION)
        .bind(create_version_transformer)
        .unwrap()
    )

    payload = CMD_VERSION

    return Command(
        payload,
        _get_cmd_command(payload, response_parser)
    )


def mode_command(mode: ProtocolMode) -> Command[Result[ProtocolMode, ProtocolError]]:
    response_parser = (
        _get_cmd_result_pipeline(CMD_MODE)
        .bind(int_response_transformer)
        .bind(mode_response_transformer)
        .unwrap()
    )

    payload = CommandPayload(CMD_MODE, [mode.value]).build()

    return Command(
        payload,
        _get_cmd_command(payload, response_parser)
    )


def arm_button_command(mode: ArmingMode) -> Command[Result[None, ProtocolError]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, []).build()

    evaluator = (
        _get_cmd_result_pipeline(keyword)
        .bind(lambda _: Success(None))
        .unwrap()
    )

    return Command(
        payload,
        _get_cmd_command(payload, evaluator)
    )


def arm_user_command(user_id: int, pin: int, mode: ArmingMode) -> Command[Result[int, ProtocolError]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, [user_id, pin]).build()

    return _get_int_command(keyword, payload)


def arm_no_pin_command(user: int, mode: ArmingMode) -> Command[Result[int, ProtocolError]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, [user]).build()
    return _get_int_command(keyword, payload)


def arm_area_command(area: int, mode: ArmingMode) -> Command[Result[int, ProtocolError]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, [area]).build()

    return _get_int_command(keyword, payload)


def disarm_user_command(user: int, pin: int) -> Command[Result[int, ProtocolError]]:
    payload = CommandPayload(CMD_DISARM, [user, pin]).build()
    return _get_int_command(CMD_DISARM, payload)


def disarm_area_command(area: int, pin: int) -> Command[Result[int, ProtocolError]]:
    payload = CommandPayload(CMD_DISARM, [area, pin]).build()
    return _get_int_command(CMD_DISARM, payload)


def bypass_zone_command(zone: int) -> Command[Result[int, ProtocolError]]:
    payload = CommandPayload(CMD_BYPASS, [zone]).build()
    return _get_int_command(CMD_BYPASS, payload)


def unbypass_zone_command(zone: int) -> Command[Result[int, ProtocolError]]:
    payload = CommandPayload(CMD_UNBYPASS, [zone]).build()
    return _get_int_command(CMD_UNBYPASS, payload)


def set_output_command(output: int, on: bool) -> Command[Result[int, ProtocolError]]:
    if on:
        keyword = CMD_OUTPUT_ON
    else:
        keyword = CMD_OUTPUT_OFF

    payload = CommandPayload(keyword, [output]).build()

    return _get_int_command(keyword, payload)


def output_state_command(output: int) -> Command[Result[bool, ProtocolError]]:
    payload = CommandPayload(CMD_OUTPUT, [output]).build()
    evaluator = (
        _get_cmd_result_pipeline(CMD_OUTPUT)
        .bind(boolean_response_transformer)
        .unwrap()
    )

    return Command(
        payload,
        _get_cmd_command(payload, evaluator)
    )
