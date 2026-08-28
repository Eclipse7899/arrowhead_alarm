"""Exceptions related to the Arrowhead Alarm protocol."""

from enum import Enum

from .models import ProtocolMode


class ProtocolErrorCode(Enum):
    """Enumeration of protocol error codes."""

    COMMAND_NOT_UNDERSTOOD = 1
    INVALID_PARAMETERS = 2
    COMMAND_NOT_ALLOWED = 3
    RX_BUFFER_OVERFLOW = 4
    TX_BUFFER_OVERFLOW = 5
    XMODEM_SESSION_FAILED = 6
    MODE_OPERATION_UNSUPPORTED = 7
    INVALID_RESPONSE = 8
    UNKNOWN = 0

    @classmethod
    def _missing_(cls, value: object) -> "ProtocolErrorCode":
        return cls.UNKNOWN


class ProtocolError(Exception):
    """Base class for protocol-related errors."""

    def __init__(self, message: str) -> None:
        """Initialize ProtocolError.

        Args:
            message: Error command describing the protocol error.

        """
        self.message = message

    def __str__(self) -> str:
        """Return string representation of the ProtocolError."""
        return f"ProtocolError: {self.message}"


class ModeOperationUnsupportedError(ProtocolError):
    """Raised when the arming_mode does not support an operation."""

    def __init__(self, operation: str, mode: ProtocolMode) -> None:
        """Initialize OperationUnsupportedInModeError.

        Args:
            operation: The operation that caused the error.
            mode: The protocol arming_mode in which the operation is unsupported.

        """
        super().__init__(
            f"Operation '{operation}' not supported in arming_mode {mode.value} ."
        )


class InvalidResponseError(ProtocolError):
    """Raised when an unexpected response is received from the device."""

    def __init__(self, received: str, expected: str | list[str]) -> None:
        """Initialize InvalidResponseError.

        Args:
            received: The response received from the device.
            expected: The expected response(s) from the device.

        """
        if isinstance(expected, list):
            expected_str = ", ".join(expected)
        else:
            expected_str = expected
        super().__init__(
            f"Waiting response received: '{received}'. Expected: '{expected_str}'."
        )


class CommandError(ProtocolError):
    """Raised when an error response is received from the device."""

    def __init__(self, error: str, command: str, response: str) -> None:
        """Initialize ErrorResponse.

        Args:
            error: The error command.
            command: The cmd that caused the error.
            response: The response received from the device.

        """
        super().__init__(
            f"CommandPayload '{command}' failed with error {error}: '{response}'"
        )
        self.error = error
        self.command = command
        self.response = response


class XModemSessionFailedError(CommandError):
    """Raised when an XModem _session fails."""

    def __init__(self, command: str, response: str) -> None:
        """Initialize XModemSessionFailedError.

        Args:
            command: The cmd that initiated the XModem _session.
            response: The response received from the device.

        """
        super().__init__("XModem _session failed", command, response)


class CommandNotUnderstoodError(CommandError):
    """Raised when the device does not understand the cmd."""

    def __init__(self, command: str, response: str) -> None:
        """Initialize CommandNotUnderstoodError.

        Args:
            command: The cmd that was not understood.
            response: The response received from the device.

        """
        super().__init__("CommandPayload not understood", command, response)


class InvalidParameterError(CommandError):
    """Raised when the alarm reports an invalid parameter for a cmd."""

    def __init__(self, request: str, response: str) -> None:
        """Initialize InvalidParameterError.

        Args:
            request: The cmd with invalid parameters.
            response: The response received from the alarm.

        """
        super().__init__("Waiting parameters", request, response)


class CommandNotAllowedError(CommandError):
    """Raised when a cmd is not allowed in the current alarm state."""

    def __init__(self, command: str, response: str) -> None:
        """Initialize CommandNotAllowedError.

        Args:
            command: The cmd that is not allowed.
            response: The response received from the alarm.

        """
        super().__init__("CommandPayload not allowed", command, response)


class RxBufferOverflowError(CommandError):
    """Raised when the alarm panel rx buffer overflows."""

    def __init__(self, command: str, response: str) -> None:
        """Initialize RxBufferOverflowError.

        Args:
            command: The cmd that caused the overflow.
            response: The response received from the alarm.

        """
        super().__init__("Receive buffer overflow", command, response)


class TxBufferOverflowError(CommandError):
    """Raised when the alarm panel's tx buffer overflows."""

    def __init__(self, command: str, response: str) -> None:
        """Initialize TxBufferOverflowError.

        Args:
            command: The cmd that caused the overflow.
            response: The response received from the alarm.

        """
        super().__init__("Transmit buffer overflow", command, response)
