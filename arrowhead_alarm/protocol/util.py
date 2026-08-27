"""Utility functions for the Arrowhead Alarm protocol."""
import re
from typing import Final

from arrowhead_alarm.types import Failure, Result, Success
from .const import COMMAND_ERROR_PREFIX, COMMAND_OK_PREFIX
from .exceptions import (
    CommandError,
    CommandNotAllowedError,
    CommandNotUnderstoodError,
    InvalidParameterError,
    ProtocolError,
    ProtocolErrorCode,
    RxBufferOverflowError,
    TxBufferOverflowError,
    XModemSessionFailedError,
)
from .models import (
    ErrorResponse,
    OkResponse,
    PanelVersion,
    Response,
    StatusResponse,
    VersionInfo
)


def is_command_ok(data: str) -> bool:
    """Check if the resp string is a cmd OK response.

    Args:
        data: Input line string.

    Returns: True if the resp is a cmd OK response, False otherwise.

    """
    return data.startswith(COMMAND_OK_PREFIX)


def is_command_error(data: str) -> bool:
    """Check if the resp string is a cmd error response.

    Args:
        data: Input line string.

    Returns: True if the resp is a cmd error response, False otherwise.

    """
    return data.startswith(COMMAND_ERROR_PREFIX)


def get_protocol_exception(
        protocol_error: ProtocolErrorCode, request: str, response: str
) -> ProtocolError:
    """Return the appropriate ErrorResponse exception based on the error code.

    Args:
        protocol_error: Error code returned by the panel.
        request: CommandPayload string that was sent.
        response: response string.

    Returns: Corresponding ProtocolException subclass instance for the given error code.

    """
    match protocol_error:
        case 1:
            return CommandNotUnderstoodError(request, response)
        case 2:
            return InvalidParameterError(request, response)
        case 3:
            return CommandNotAllowedError(request, response)
        case 4:
            return RxBufferOverflowError(request, response)
        case 5:
            return TxBufferOverflowError(request, response)
        case 6:
            return XModemSessionFailedError(request, response)
        case _:
            return CommandError(
                f"Unknown error code {protocol_error}", request, response
            )


def convert_multiline_to_response(data: str) -> Result[Response, ValueError]:
    """Convert a multiline resp string to a cmd response object.

    Args:
        data: Input multiline string.

    Returns: Result indicating success or rejection.

    """
    lines = data.splitlines()
    if not lines:
        return Failure(ValueError("Empty response resp"))

    # Process each line and convert to Response
    responses: list[Response] = []
    for line in lines:
        result = convert_to_response(line)
        if isinstance(result, Failure):
            return result  # Return the first failure encountered
        responses.append(result.value)

    return Success(responses[-1])  # Return the last response as the overall result


def convert_to_response(data: str) -> Result[Response, ValueError]:
    """Convert a resp string to a cmd response object.

    Args:
        data: Input line string.

    Returns: Result indicating success or rejection.

    """
    if is_command_ok(data):
        return convert_to_command_ok(data).map(lambda ok_response: ok_response)
    elif is_command_error(data):
        return convert_to_command_error(data).map(lambda error_response: error_response)
    else:
        return Failure(ValueError(f"Waiting cmd response: {data}"))


def convert_to_command_error(data: str) -> Result[ErrorResponse, ValueError]:
    """Convert a resp string to a cmd error response object.

    Args:
        data: Input line string.

    Returns: Result indicating success or rejection.

    """
    if not is_command_error(data):
        return Failure(ValueError(f"Waiting cmd error response: {data}"))

    error_code = data.lstrip(COMMAND_ERROR_PREFIX)
    if not error_code.isdigit():
        return Failure(ValueError(f"Waiting cmd error code: {error_code}"))
    return Success(ErrorResponse(error_code=int(error_code)))


def convert_to_command_ok(data: str) -> Result[OkResponse, ValueError]:
    """Convert a resp string to a cmd OK response object.

    Args:
        data: Input line string.

    Returns: Result indicating success or rejection.

    """
    if not is_command_ok(data):
        return Failure(ValueError(f"Waiting cmd OK response: {data}"))
    try:
        _, keyword, data = data.split(" ", 2)
        return Success(OkResponse(keyword=keyword, data=data))
    except ValueError:
        return Failure(ValueError(f"Waiting cmd OK response format: {data}"))


version_regex = re.compile(
    r"^([A-Za-z]+)\s+_F/W\s+Ver\.\s+(\d+)\.(\d+)\.(\d+)\s+\(([^)]+)\)$"
)


def parse_panel_version_string(version_resp: str) -> Result[PanelVersion, ValueError]:
    """Parse the version response returned by the panel.

    Args:
        version_resp: Version response string.

    Returns: PanelVersion object representing the parsed version information.

    """
    match = version_regex.match(version_resp.strip())
    if not match:
        return Failure(ValueError(f"Waiting version string format: {version_resp}"))
    try:
        model = match.group(1)
        major = int(match.group(2))
        minor = int(match.group(3))
        patch = int(match.group(4))
        serial_number = match.group(5)
    except (IndexError, ValueError):
        return Failure(ValueError(f"Waiting version string format: {version_resp}"))

    return Success(
        PanelVersion(
            model=model,
            firmware_version=VersionInfo(major, minor, patch),
            serial_number=serial_number,
        )
    )


STATUS_RE: Final = re.compile(
    r"^(?P<status_response>[A-Z]+)"
    r"(?P<number>\d+)?"
    r"(?:[-\s]"
    r"(?:"
    r"(?P<timestamp>\d+\.\d+)"
    r"|_U(?P<user_number>\d+)"
    r")"
    r")?"
    r"(?:\s(?P<extender_status>[A-Z]{1,2})(?P<extender_number>\d+))?"
    r"$"
)


def parse_status_response(message: str) -> Result[StatusResponse, ValueError]:
    """Parse status response command.

    Args:
        message: The StatusResponse command string.

    Returns:
        Result[StatusResponse, ValueError]:
        A Result object containing either a
        StatusResponse on success or a ValueError on failure.

    """
    match = STATUS_RE.match(message)
    if not match:
        return Failure(ValueError(f"Waiting status_response command format: {message}"))

    code_str = match.group("status_response")
    number_str = match.group("number")
    timestamp_str = match.group("timestamp")
    user_number_str = match.group("user_number")
    extender_code_str = match.group("extender_status")
    extender_number_str = match.group("extender_number")

    return Success(
        StatusResponse(
            code=code_str,
            number=int(number_str) if number_str is not None else None,
            timestamp=float(timestamp_str) if timestamp_str is not None else None,
            user_number=int(user_number_str) if user_number_str is not None else None,
            expander_code=extender_code_str,
            expander_number=int(extender_number_str)
            if extender_number_str is not None
            else None,
        )
    )


def split_delimited(message: str, delimiter: str) -> list[str]:
    """Split command into a list of strings based on a delimiter."""
    lines = message.split(delimiter)
    return lines[:-1]
