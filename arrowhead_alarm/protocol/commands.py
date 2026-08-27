"""Commands for interacting with the Arrowhead alarm panel."""
from arrowhead_alarm import ArmingMode
from arrowhead_alarm.collectors import LineCountCollector
from arrowhead_alarm.protocol.const import CMD_DISARM, CMD_MODE, CMD_OUTPUT, CMD_ARM_AWAY, CMD_ARM_STAY, \
    CMD_BYPASS, CMD_UNBYPASS, CMD_OUTPUT_ON, CMD_OUTPUT_OFF, CMD_VERSION
from arrowhead_alarm.protocol.exceptions import ProtocolErrorCode
from arrowhead_alarm.protocol.models import (
    PanelVersion,
    ProtocolMode,
)
from arrowhead_alarm.protocol.transformers import (
    boolean_response_transformer,
    cmd_result_transformer,
    create_version_transformer,
    int_response_transformer,
    mode_response_transformer, get_cmd_keyword_transformer, get_line_join_transformer,
)
from arrowhead_alarm.protocol.util import convert_to_response
from arrowhead_alarm.types import ResultPipeline, Collector, CollectorPipeline, Result, Success


def _get_cmd_collector_pipeline(
        command_keyword: str,
) -> ResultPipeline[str, str, ProtocolErrorCode]:
    """Create an _collector that processes a cmd response."""
    return (
        ResultPipeline(convert_to_response)
        .map_error(lambda error: ProtocolErrorCode.INVALID_RESPONSE)
        .bind(get_cmd_keyword_transformer(command_keyword))
        .bind(cmd_result_transformer)
    )


def version_response_collector() -> Collector[str, Result[PanelVersion, ProtocolErrorCode]]:
    response_evaluator = (
        _get_cmd_collector_pipeline(CMD_VERSION)
        .bind(create_version_transformer)
        .flatten()
    )

    return (
        CollectorPipeline.of_string()
        .map(response_evaluator)
        .flatten()
    )


def mode_collector() -> Collector[str, Result[ProtocolMode, ProtocolErrorCode]]:
    evaluator = (
        _get_cmd_collector_pipeline(CMD_MODE)
        .bind(int_response_transformer)
        .bind(mode_response_transformer)
        .flatten()
    )

    return (
        CollectorPipeline.of_string()
        # Expecting 2 lines: "OK" and "Mode <mode>"
        # Join them together and pass to the collector
        .bind(LineCountCollector(expected=2).feed)
        .map(get_line_join_transformer(" "))
        .map(evaluator)
        .flatten()
    )


def int_response_collector(keyword: str) -> Collector[str, Result[int, ProtocolErrorCode]]:
    evaluator = (
        _get_cmd_collector_pipeline(keyword)
        .bind(int_response_transformer)
        .flatten()
    )

    return (
        CollectorPipeline.of_string()
        .map(evaluator)
        .flatten()
    )


def arm_button_collector(mode: ArmingMode) -> Collector[str, Result[None, ProtocolErrorCode]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    evaluator = (
        _get_cmd_collector_pipeline(keyword)
        .bind(lambda _: Success(None))
        .flatten()
    )

    return (
        CollectorPipeline.of_string()
        .map(evaluator)
        .flatten()
    )


def arm_user_collector(mode: ArmingMode) -> Collector[str, Result[int, ProtocolErrorCode]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    return int_response_collector(keyword)


def arm_area_collector(mode: ArmingMode) -> Collector[str, Result[int, ProtocolErrorCode]]:
    match mode:
        case ArmingMode.AWAY:
            keyword = CMD_ARM_AWAY
        case ArmingMode.STAY:
            keyword = CMD_ARM_STAY

    return int_response_collector(keyword)


def disarm_user_collector() -> Collector[str, Result[int, ProtocolErrorCode]]:
    return int_response_collector(CMD_DISARM)


def disarm_area_collector() -> Collector[str, Result[int, ProtocolErrorCode]]:
    return int_response_collector(CMD_DISARM)


def bypass_zone_collector() -> Collector[str, Result[int, ProtocolErrorCode]]:
    return int_response_collector(CMD_BYPASS)


def unbypass_zone_collector() -> Collector[str, Result[int, ProtocolErrorCode]]:
    return int_response_collector(CMD_UNBYPASS)


def set_output_collector(on: bool) -> Collector[str, Result[int, ProtocolErrorCode]]:
    if on:
        keyword = CMD_OUTPUT_ON
    else:
        keyword = CMD_OUTPUT_OFF

    return int_response_collector(keyword)


def output_state_collector() -> Collector[str, Result[bool, ProtocolErrorCode]]:
    evaluator = (
        _get_cmd_collector_pipeline(CMD_OUTPUT)
        .bind(boolean_response_transformer)
        .flatten()
    )

    return (
        CollectorPipeline.of_string()
        .map(evaluator)
        .flatten()
    )
