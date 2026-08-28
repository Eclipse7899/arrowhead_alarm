"""Protocol-specific _collector helpers for Arrowhead alarm commands."""

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
)
from .types import (
    Failure,
    Result,
    ResultTransformer,
    Success,
    Transformer,
)
from .util import (
    parse_panel_version_string,
    parse_status_response,
)


def get_cmd_keyword_transformer(
        keyword: str
) -> ResultTransformer[Response, Response, ProtocolErrorCode]:
    """Create an _collector that checks a Response keyword."""

    def cmd_keyword_evaluator(resp: Response) -> Result[Response, ProtocolErrorCode]:
        match resp:
            case OkResponse() if resp.keyword == keyword:
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
    return parse_panel_version_string(data).map_error(
        lambda _: ProtocolErrorCode.INVALID_RESPONSE
    )


def get_line_join_transformer(
        delimiter: str,
) -> Transformer[list[str], str]:
    """Return a transformer that joins a list of _lines into a single string using the delimiter."""

    def line_join_transformer(lines: list[str]) -> str:
        return delimiter.join(lines)

    return line_join_transformer


def get_line_split_transformer(
        delimiter: str,
) -> Transformer[str, list[str]]:
    """Return a transformer that splits a string into a list of _lines using the delimiter."""

    def line_split_transformer(data: str) -> list[str]:
        return data.split(delimiter)

    return line_split_transformer


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


def panel_operation_list_transformer(
        data: list[str],
) -> Result[list[Transformer[PanelState, None]], ProtocolErrorCode]:
    """Parse a panel operation response and return a list of operations."""
    operations = []

    for result in [panel_operation_transformer(line) for line in data]:
        if isinstance(result, Failure):
            return Failure(result.error)
        else:
            operations.append(result.value)

    return Success(operations)


def panel_operation_transformer(
        data: str,
) -> Result[Transformer[PanelState, None], ProtocolErrorCode]:
    """Parse a panel operation response and return a callable that modifies the PanelState."""
    return (
        parse_status_response(data)
        .map(get_status_operation)
        .map_error(lambda _: ProtocolErrorCode.INVALID_RESPONSE)
    )
