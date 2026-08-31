"""Commands for interacting with the Arrowhead alarm panel."""

from typing import Callable, TypeVar

from .const import (
    CMD_ARM_AREA_AWAY,
    CMD_ARM_AREA_STAY,
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
from .exceptions import ProtocolError, ProtocolErrorCode
from .models import (
    ArmingMode,
    CommandPayload,
    PanelInfo,
    ProtocolMode,
)
from .transformers import (
    boolean_response_transformer,
    cmd_result_transformer,
    create_version_transformer,
    get_cmd_keyword_transformer,
    get_int_prefix_transformer,
    int_response_transformer,
    mode_response_transformer,
)
from .types import (
    CollectionResult,
    Collector,
    CollectorContext,
    CollectorPipeline,
    Command,
    Done,
    Result,
    ResultPipeline,
    Success,
    Waiting,
)
from .util import convert_to_response, get_protocol_exception, is_command_error, is_command_ok

_T = TypeVar("_T")


def _is_command_response(data: str) -> CollectionResult[str]:
    """Return Done for command response lines (OK/ERR), Waiting for everything else."""
    if is_command_ok(data) or is_command_error(data):
        return Done(data)
    return Waiting()


def _get_command_collector(
    request: str, transformer: Callable[[str], Result[_T, ProtocolErrorCode]]
) -> Collector[str, Result[_T, ProtocolError]]:
    return (
        CollectorPipeline(_is_command_response)
        .map(CollectorContext.of_value)
        .map(lambda context: context.map(transformer))
        .map(
            lambda context: context.data.map_error(
                lambda error: get_protocol_exception(error, request, context.original)
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
    response_parser = _get_cmd_result_pipeline(keyword).bind(int_response_transformer).unwrap()

    return Command(payload, _get_command_collector(payload, response_parser))


def version_command() -> Command[Result[PanelInfo, ProtocolError]]:
    """Create a command to query the panel info.

    Returns:
        A command object that resolves to the panel info or a protocol error.
    """
    response_parser = (
        _get_cmd_result_pipeline(CMD_VERSION).bind(create_version_transformer).unwrap()
    )

    payload = CMD_VERSION

    return Command(payload, _get_command_collector(payload, response_parser))


def status_command() -> Command[Result[None, ProtocolError]]:
    """Create a command to query the panel status."""
    response_parser = (
        _get_cmd_result_pipeline(CMD_STATUS).bind(lambda _: Success(None)).unwrap()
    )

    payload = CMD_STATUS

    return Command(payload, _get_command_collector(payload, response_parser))


def mode_command(mode: ProtocolMode) -> Command[Result[ProtocolMode, ProtocolError]]:
    """Create a command to set the protocol mode.

    Args:
        mode: The protocol mode to set.

    Returns:
        A command object that resolves to the set protocol mode or a protocol error.
    """
    response_parser = (
        _get_cmd_result_pipeline(CMD_MODE)
        .bind(int_response_transformer)
        .bind(mode_response_transformer)
        .unwrap()
    )

    payload = CommandPayload(CMD_MODE, [mode.value]).build()

    return Command(payload, _get_command_collector(payload, response_parser))


def arm_button_command(mode: ArmingMode) -> Command[Result[None, ProtocolError]]:
    """Create a command to arm the system without a user code.

    Args:
        mode: The arming mode (AWAY or STAY).

    Returns:
        A command object that resolves to None on success or a protocol error.
    """
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, []).build()

    evaluator = _get_cmd_result_pipeline(keyword).bind(lambda _: Success(None)).unwrap()

    return Command(payload, _get_command_collector(payload, evaluator))


def arm_user_command(
    user_id: int, pin: int, mode: ArmingMode
) -> Command[Result[int, ProtocolError]]:
    """Create a command to arm the system with a user ID and PIN.

    Args:
        user_id: The user slot/ID number.
        pin: The user's PIN code.
        mode: The arming mode (AWAY or STAY).

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, [user_id, pin]).build()

    return _get_int_command(keyword, payload)


def arm_no_pin_command(user: int, mode: ArmingMode) -> Command[Result[int, ProtocolError]]:
    """Create a command to arm the system as a user without PIN.

    Args:
        user: The user slot/ID number.
        mode: The arming mode (AWAY or STAY).

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, [user]).build()
    return _get_int_command(keyword, payload)


def arm_area_command_mode_2(area: int, mode: ArmingMode) -> Command[Result[int, ProtocolError]]:
    """Create a command to arm an area in Mode 2.

    Args:
        area: The area number to arm.
        mode: The arming mode (AWAY or STAY).

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    payload = CommandPayload(keyword, [area]).build()

    return _get_int_command(keyword, payload)


def arm_area_command_mode_4(area: int, mode: ArmingMode) -> Command[Result[int, ProtocolError]]:
    """Create a command to arm an area in Mode 4.

    Args:
        area: The area number to arm.
        mode: The arming mode (AWAY or STAY).

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AREA_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_AREA_STAY

    payload = CommandPayload(keyword, [area]).build()
    return _get_int_command(keyword, payload)


def disarm_user_command(user: int, pin: int) -> Command[Result[int, ProtocolError]]:
    """Create a command to disarm as a user with PIN.

    Args:
        user: The user slot/ID number.
        pin: The user's PIN code.

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    payload = CommandPayload(CMD_DISARM, [user, pin]).build()
    return _get_int_command(CMD_DISARM, payload)


def disarm_area_command(area: int, pin: int) -> Command[Result[int, ProtocolError]]:
    """Create a command to disarm an area with PIN.

    Args:
        area: The area number to disarm.
        pin: The PIN code.

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    payload = CommandPayload(CMD_DISARM, [area, pin]).build()
    return _get_int_command(CMD_DISARM, payload)


def bypass_zone_command(zone: int) -> Command[Result[int, ProtocolError]]:
    """Create a command to bypass a zone.

    Args:
        zone: The zone number to bypass.

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    payload = CommandPayload(CMD_BYPASS, [zone]).build()
    return _get_int_command(CMD_BYPASS, payload)


def unbypass_zone_command(zone: int) -> Command[Result[int, ProtocolError]]:
    """Create a command to unbypass a zone.

    Args:
        zone: The zone number to unbypass.

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    payload = CommandPayload(CMD_UNBYPASS, [zone]).build()
    return _get_int_command(CMD_UNBYPASS, payload)


def set_output_command(output: int, on: bool) -> Command[Result[int, ProtocolError]]:
    """Create a command to set the state of an output.

    Args:
        output: The output number to configure.
        on: True to turn on, False to turn off.

    Returns:
        A command object that resolves to the result integer or a protocol error.
    """
    if on:
        keyword = CMD_OUTPUT_ON
    else:
        keyword = CMD_OUTPUT_OFF

    payload = CommandPayload(keyword, [output]).build()

    return _get_int_command(keyword, payload)


def output_state_command(output: int) -> Command[Result[bool, ProtocolError]]:
    """Create a command to query the state of an output.

    Args:
        output: The output number to query.

    Returns:
        A command object that resolves to a boolean state or a protocol error.
    """
    payload = CommandPayload(CMD_OUTPUT, [output]).build()
    evaluator = (
        _get_cmd_result_pipeline(CMD_OUTPUT)
        .bind(get_int_prefix_transformer(output))
        .bind(boolean_response_transformer)
        .unwrap()
    )

    return Command(payload, _get_command_collector(payload, evaluator))
