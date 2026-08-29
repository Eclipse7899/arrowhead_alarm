"""Protocol-specific _collector helpers for Arrowhead alarm commands."""

from typing import Callable

from .exceptions import (
    ProtocolErrorCode,
)
from .messages import get_status_operation
from .models import (
    ErrorResponse,
    OkResponse,
    PanelState,
    PanelVersion,
    ProtocolMode,
    Response,
    StatusResponse,
)
from .types import (
    Failure,
    Result,
    Success,
    Transformer,
)
from .util import (
    parse_panel_version_string,
    parse_status_response,
)


def get_cmd_keyword_transformer(
    keyword: str,
) -> Callable[[Response], Result[Response, ProtocolErrorCode]]:
    """Create an _collector that checks a Response keyword."""

    def cmd_keyword_evaluator(resp: Response) -> Result[Response, ProtocolErrorCode]:
        match resp:
            case OkResponse() if resp.keyword.lower() == keyword.lower():
                return Success(resp)
            case OkResponse():
                return Failure(ProtocolErrorCode.INVALID_RESPONSE)
            case ErrorResponse():
                protocol_code = ProtocolErrorCode(resp.error_code)
                return Failure(protocol_code)

    return cmd_keyword_evaluator


def cmd_result_transformer(
    resp: Response,
) -> Result[str, ProtocolErrorCode]:
    """Transform a command response into a Result with the appropriate error handling."""
    match resp:
        case OkResponse():
            return Success(resp.data)
        case ErrorResponse(error_code=error_code):
            return Failure(ProtocolErrorCode(error_code))


def create_version_transformer(data: str) -> Result[PanelVersion, ProtocolErrorCode]:
    """Create a transformer that parses a version response into a PanelVersion object."""
    new = data.strip().strip('"')
    return parse_panel_version_string(new).map_error(lambda _: ProtocolErrorCode.INVALID_RESPONSE)


def get_line_join_transformer(
    delimiter: str,
) -> Transformer[list[str], str]:
    """Return a transformer that joins a list of _lines into a single string using the delimiter."""

    def line_join_transformer(lines: list[str]) -> str:
        return delimiter.join(lines)

    return line_join_transformer


def mode_response_transformer(
    mode_int: int,
) -> Result[ProtocolMode, ProtocolErrorCode]:
    """Parse a mode response and return the value."""
    try:
        mode = ProtocolMode(mode_int)
        return Success(mode)
    except ValueError:
        return Failure(ProtocolErrorCode.INVALID_RESPONSE)


def int_response_transformer(
    data: str,
) -> Result[int, ProtocolErrorCode]:
    """Parse an integer response and return the value."""
    try:
        int_data = int(data)
        return Success(int_data)
    except ValueError:
        return Failure(ProtocolErrorCode.INVALID_RESPONSE)


def boolean_response_transformer(
    data: str,
) -> Result[bool, ProtocolErrorCode]:
    """Parse a boolean response (ON/OFF) and return the value."""
    data_upper = data.strip().upper()
    if data_upper == "ON":
        return Success(True)
    elif data_upper == "OFF":
        return Success(False)
    else:
        return Failure(ProtocolErrorCode.INVALID_RESPONSE)


def get_int_prefix_transformer(
        expected_int: int
) -> Callable[[str], Result[str, ProtocolErrorCode]]:
    """Return a transformer that checks for an expected integer followed by a string."""

    def transformer(
        data: str,
    ) -> Result[str, ProtocolErrorCode]:
        try:
            int_data, other_data = data.split(" ", 1)
            if int(int_data) != expected_int:
                return Failure(ProtocolErrorCode.INVALID_RESPONSE)
            return Success(other_data)
        except ValueError:
            return Failure(ProtocolErrorCode.INVALID_RESPONSE)

    return transformer


def panel_operation_transformer(
    data: str,
) -> Result[Transformer[PanelState, PanelState], ProtocolErrorCode]:
    """Parse a panel operation response and return a callable that modifies the PanelState."""

    def status_op_wrapper(
        code: StatusResponse,
    ) -> Result[Callable[[PanelState], PanelState], ValueError]:
        try:
            return Success(get_status_operation(code))
        except ValueError as e:
            return Failure(e)

    return (
        parse_status_response(data)
        .bind(status_op_wrapper)
        .map_error(lambda _: ProtocolErrorCode.INVALID_RESPONSE)
    )
