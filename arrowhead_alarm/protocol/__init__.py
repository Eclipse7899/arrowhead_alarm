"""Arrow Head Alarm Protocol module."""

from .commands import (
    arm_area_command_mode_4,
    arm_area_command_mode_2,
    arm_button_command,
    arm_no_pin_command,
    arm_user_command,
    bypass_zone_command,
    disarm_area_command,
    disarm_user_command,
    mode_command,
    output_state_command,
    set_output_command,
    unbypass_zone_command,
    version_command,
)
from .defaults import get_default_state
from .exceptions import (
    CommandError,
    CommandNotAllowedError,
    CommandNotUnderstoodError,
    InvalidParameterError,
    InvalidResponseError,
    ModeOperationUnsupportedError,
    ProtocolError,
    RxBufferOverflowError,
    TxBufferOverflowError,
    XModemSessionFailedError,
)
from .models import (
    AlarmState,
    Area,
    ArmingMode,
    CommandPayload,
    ErrorResponse,
    Expander,
    OkResponse,
    Output,
    PanelState,
    PanelVersion,
    ProtocolMode,
    VersionInfo,
    Zone,
    UserPin
)
from .types import Failure, Result, Success, Collector, CollectionResult, Command

__all__ = [
    "CommandPayload",
    "ProtocolMode",
    "ArmingMode",
    "PanelVersion",
    "VersionInfo",
    "OkResponse",
    "ErrorResponse",
    "PanelState",
    "Expander",
    "Output",
    "Zone",
    "AlarmState",
    "Area",
    "UserPin",
    "get_default_state"
    # Commands
    "build_arm_user_command",
    "version_command",
    "mode_command",
    "arm_button_command",
    "arm_user_command",
    "arm_no_pin_command",
    "arm_area_command_mode_2",
    "disarm_user_command",
    "disarm_area_command",
    "bypass_zone_command",
    "unbypass_zone_command",
    "set_output_command",
    "output_state_command",
    # Exceptions
    "ProtocolError",
    "CommandError",
    "ModeOperationUnsupportedError",
    "InvalidResponseError",
    "XModemSessionFailedError",
    "CommandNotUnderstoodError",
    "InvalidParameterError",
    "CommandNotAllowedError",
    "RxBufferOverflowError",
    "TxBufferOverflowError",
    # Types
    "Result",
    "Success",
    "Failure",
    "Collector",
    "CollectionResult",
    "Command"
]
