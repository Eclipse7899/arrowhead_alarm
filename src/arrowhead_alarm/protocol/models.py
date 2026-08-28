"""Types used in the Arrowhead Alarm protocol."""
import sys
from dataclasses import dataclass
from enum import Enum, IntFlag, auto
from functools import total_ordering
from typing import (
    TypeAlias,
    TypeVar,
)

if sys.version_info >= (3, 11):
    pass
else:
    pass

_T = TypeVar("_T")


class StatusFlags(IntFlag):
    """Parts of a CombinedStatusCode command."""

    CODE = auto()
    NUMBER = auto()
    EXPANDER_CODE = auto()
    EXPANDER_NUMBER = auto()
    USER_NUMBER = auto()
    TIMESTAMP = auto()


STATUS_CODE = StatusFlags.CODE

NUMBERED_STATUS = STATUS_CODE | StatusFlags.NUMBER

EXPANDER_STATUS = STATUS_CODE | StatusFlags.EXPANDER_CODE | StatusFlags.EXPANDER_NUMBER

USER_STATUS = NUMBERED_STATUS | StatusFlags.USER_NUMBER

TIMESTAMPED_STATUS = NUMBERED_STATUS | StatusFlags.TIMESTAMP


@dataclass
class UserPin:
    """User ID and PIN for arming/disarming."""

    user_id: int
    pin: int


class ProtocolMode(Enum):
    """Protocol modes."""

    MODE_1 = 1  # Default, no acknowledgments
    MODE_2 = 2  # AAP arming_mode, with acknowledgments
    MODE_3 = 3  # Permaconn arming_mode, with acknowledgments
    MODE_4 = 4  # Home Automation arming_mode, no acknowledgments (ECi FW 10.3.50+)


@total_ordering
@dataclass
class VersionInfo:
    """Version information."""

    major_version: int
    minor_version: int
    patch_version: int

    def _as_tuple(self) -> tuple[int, int, int]:
        return self.major_version, self.minor_version, self.patch_version

    def __lt__(self, other: "VersionInfo") -> bool:
        """Check if this VersionInfo is less than another.

        Args:
            other: The other VersionInfo instance to compare.

        Returns: True if this instance is less than the other, False otherwise.

        """
        return self._as_tuple() < other._as_tuple()

    def __gt__(self, other: "VersionInfo") -> bool:
        """Check if this VersionInfo is greater than another.

        Args:
            other: The other VersionInfo instance to compare.

        Returns: True if this instance is greater than the other, False otherwise.

        """
        return self._as_tuple() > other._as_tuple()

    def __le__(self, other: "VersionInfo") -> bool:
        """Check if this VersionInfo is less than or equal to another.

        Args:
            other: The other VersionInfo instance to compare.
        Returns: True if this instance is less than or \
        equal to the other, False otherwise.

        """
        return self._as_tuple() <= other._as_tuple()

    def __ge__(self, other: "VersionInfo") -> bool:
        """Check if this VersionInfo is greater than or equal to another.

        Args:
            other: The other VersionInfo instance to compare.

        Returns: True if this instance is greater than or \
        equal to the other, False otherwise.

        """
        return self._as_tuple() >= other._as_tuple()


@dataclass
class PanelVersion:
    """Panel version information."""

    model: str
    firmware_version: VersionInfo
    serial_number: str


@dataclass(frozen=True)
class CommandPayload:
    """Represents a cmd to the alarm panel."""

    keyword: str
    args: list[int | str] | None = None

    def build(self) -> str:
        """Build the command string.

        Returns:
            The formatted command string.
        """
        line = self.keyword
        if self.args:
            joined = " ".join(str(arg) for arg in self.args)
            line = f"{line} {joined}"
        return line


@dataclass
class ErrorResponse:
    """Represents an error response from a cmd."""
    error_code: int


@dataclass
class OkResponse:
    """Represents a successful response of type A from a cmd."""
    keyword: str
    data: str


Response: TypeAlias = ErrorResponse | OkResponse


class AlarmState(Enum):
    """Alarm states."""

    DISARMED = "disarmed"
    ARMED_AWAY = "armed_away"
    ARMED_STAY = "armed_stay"
    ARMING_AWAY = "arming_away"
    ARMING_STAY = "arming_stay"
    ALARM_TRIGGERED = "alarm_triggered"


@dataclass
class Area:
    """Alarm Area status_response."""

    area_number: int
    state: AlarmState
    ready_to_arm: bool


@dataclass
class Zone:
    """Alarm Zone status_response."""

    zone_number: int
    supervise_alarm: bool
    trouble_alarm: bool
    bypassed: bool
    alarm: bool
    radio_battery_low: bool
    zone_closed: bool
    sensor_watch_alarm: bool


@dataclass
class Expander:
    """Expander state."""

    expander_id: int
    tamper_alarm_triggered: bool
    mains_fault: bool
    battery_fault: bool
    fuse_fault: bool


@dataclass
class Output:
    """Alarm Output status_response."""

    output_number: int
    on: bool


class ArmingMode(Enum):
    """Arming modes."""

    AWAY = "away"
    STAY = "stay"


@dataclass
class PanelState:
    """Overall status_response of the alarm panel."""

    ready_to_arm: bool
    battery_fault: bool
    mains_fault: bool
    tamper_alarm_triggered: bool
    line_fault: bool
    dialer_fault: bool
    dialer_line_fault: bool
    fuse_fault: bool
    monitoring_station_active: bool
    dialer_active: bool
    code_tamper: bool
    receiver_fault: bool | None
    pendant_battery_fault: bool | None
    rf_battery_low: bool | None
    sensor_watch_alarm: bool | None
    zones: dict[int, Zone]
    outputs: dict[int, Output]
    areas: dict[int, Area]
    zone_expanders: dict[int, Expander]
    output_expanders: dict[int, Expander]
    prox_expanders: dict[int, Expander]


@dataclass
class StatusResponse:
    """Status response from the panel."""

    code: str
    number: int | None = None
    expander_code: str | None = None
    expander_number: int | None = None
    user_number: int | None = None
    timestamp: float | None = None

    @property
    def flags(self) -> StatusFlags:
        """Determine the StatusFlags for this StatusResponse instance.

        Returns: The combined StatusFlags represent the fields present.

        """
        flags = StatusFlags.CODE
        if self.number is not None:
            flags |= StatusFlags.NUMBER
        if self.expander_code is not None:
            flags |= StatusFlags.EXPANDER_CODE
        if self.expander_number is not None:
            flags |= StatusFlags.EXPANDER_NUMBER
        if self.user_number is not None:
            flags |= StatusFlags.USER_NUMBER
        if self.timestamp is not None:
            flags |= StatusFlags.TIMESTAMP
        return flags
