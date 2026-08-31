"""Types used in the Arrowhead Alarm protocol."""

from dataclasses import dataclass, replace
from enum import Enum, IntFlag, auto
from functools import total_ordering
from typing import (
    TypeAlias,
)


class StatusFlags(IntFlag):
    """Parts of a CombinedStatusCode command."""

    CODE = auto()
    NUMBER = auto()
    EXPANDER_CODE = auto()
    EXPANDER_NUMBER = auto()
    USER_NUMBER = auto()
    TIMESTAMP = auto()


CODE_STATUS = StatusFlags.CODE

NUMBERED_STATUS = CODE_STATUS | StatusFlags.NUMBER

EXPANDER_STATUS = CODE_STATUS | StatusFlags.EXPANDER_CODE | StatusFlags.EXPANDER_NUMBER

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

    major: int
    minor: int
    patch: int

    def _as_tuple(self) -> tuple[int, int, int]:
        return (
            self.major,
            self.minor,
            self.patch,
        )

    def __lt__(self, other: "VersionInfo") -> bool:
        """Check if this version is less than another."""
        return self._as_tuple() < other._as_tuple()


@dataclass
class PanelInfo:
    """Information about the alarm panel."""

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


class ArmingMode(Enum):
    """Arming modes."""

    AWAY = "away"
    STAY = "stay"


@dataclass
class Area:
    """Alarm area state."""

    number: int
    state: AlarmState
    ready_to_arm: bool

    def set_state(self, state: AlarmState) -> "Area":
        """Set the area state."""
        return replace(self, state=state)

    def set_ready_to_arm(self, value: bool) -> "Area":
        """Set whether the area is ready to arm."""
        return replace(self, ready_to_arm=value)


@dataclass
class Zone:
    """Alarm zone state."""

    number: int
    supervise_alarm: bool
    trouble_alarm: bool
    bypassed: bool
    alarm: bool
    radio_battery_low: bool
    closed: bool
    sensor_watch_alarm: bool

    def set_supervise_alarm(self, value: bool) -> "Zone":
        """Set the supervise alarm state."""
        return replace(self, supervise_alarm=value)

    def set_trouble_alarm(self, value: bool) -> "Zone":
        """Set the trouble alarm state."""
        return replace(self, trouble_alarm=value)

    def set_bypassed(self, value: bool) -> "Zone":
        """Set the bypassed state."""
        return replace(self, bypassed=value)

    def set_alarm(self, value: bool) -> "Zone":
        """Set the alarm state."""
        return replace(self, alarm=value)

    def set_radio_battery_low(self, value: bool) -> "Zone":
        """Set the radio battery low state."""
        return replace(self, radio_battery_low=value)

    def set_closed(self, value: bool) -> "Zone":
        """Set the zone closed state."""
        return replace(self, closed=value)

    def set_sensor_watch_alarm(self, value: bool) -> "Zone":
        """Set the sensor watch alarm state."""
        return replace(self, sensor_watch_alarm=value)


@dataclass
class Expander:
    """Expander state."""

    number: int
    tamper_fault: bool
    mains_fault: bool
    battery_fault: bool
    fuse_fault: bool

    def set_tamper_fault(self, value: bool) -> "Expander":
        """Set the tamper fault state."""
        return replace(self, tamper_fault=value)

    def set_mains_fault(self, value: bool) -> "Expander":
        """Set the mains fault state."""
        return replace(self, mains_fault=value)

    def set_battery_fault(self, value: bool) -> "Expander":
        """Set the battery fault state."""
        return replace(self, battery_fault=value)

    def set_fuse_fault(self, value: bool) -> "Expander":
        """Set the fuse fault state."""
        return replace(self, fuse_fault=value)


@dataclass
class Output:
    """Alarm Output model."""

    number: int
    on: bool

    def set_on(self, value: bool) -> "Output":
        """Set the output state."""
        return replace(self, on=value)


@dataclass
class PanelState:
    """Overall status of the alarm panel."""

    info: PanelInfo | None
    ready_to_arm: bool
    battery_fault: bool
    mains_fault: bool
    tamper_fault: bool
    dialer_fault: bool
    dialer_line_fault: bool
    fuse_fault: bool
    monitoring_station_active: bool
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

    def set_info(self, info: PanelInfo) -> "PanelState":
        """Set the panel info."""
        return replace(self, info=info)

    def set_ready_to_arm(self, value: bool) -> "PanelState":
        """Set whether the panel is ready to arm."""
        return replace(self, ready_to_arm=value)

    def set_battery_fault(self, value: bool) -> "PanelState":
        """Set the panel battery fault state."""
        return replace(self, battery_fault=value)

    def set_mains_fault(self, value: bool) -> "PanelState":
        """Set the panel mains fault state."""
        return replace(self, mains_fault=value)

    def set_tamper_fault(self, value: bool) -> "PanelState":
        """Set the panel tamper fault state."""
        return replace(self, tamper_fault=value)

    def set_dialer_fault(self, value: bool) -> "PanelState":
        """Set the panel dialer fault state."""
        return replace(self, dialer_fault=value)

    def set_dialer_line_fault(self, value: bool) -> "PanelState":
        """Set the panel dialer line fault state."""
        return replace(self, dialer_line_fault=value)

    def set_fuse_fault(self, value: bool) -> "PanelState":
        """Set the panel fuse fault state."""
        return replace(self, fuse_fault=value)

    def set_monitoring_station_active(self, value: bool) -> "PanelState":
        """Set whether the monitoring station is active."""
        return replace(self, monitoring_station_active=value)

    def set_receiver_fault(self, value: bool | None) -> "PanelState":
        """Set the receiver fault state."""
        return replace(self, receiver_fault=value)

    def set_pendant_battery_fault(self, value: bool | None) -> "PanelState":
        """Set the pendant battery fault state."""
        return replace(self, pendant_battery_fault=value)

    def set_rf_battery_low(self, value: bool | None) -> "PanelState":
        """Set the RF battery low state."""
        return replace(self, rf_battery_low=value)

    def set_sensor_watch_alarm(self, value: bool | None) -> "PanelState":
        """Set the panel sensor watch alarm state."""
        return replace(self, sensor_watch_alarm=value)

    def set_area_state(
        self,
        area_number: int,
        state: AlarmState,
    ) -> "PanelState":
        """Set the state of an area."""
        if area_number not in self.areas:
            return self

        area = self.areas[area_number].set_state(state)

        return replace(
            self,
            areas=self.areas | {area_number: area},
        )

    def set_area_ready(
        self,
        area_number: int,
        value: bool,
    ) -> "PanelState":
        """Set whether an area is ready to arm."""
        if area_number not in self.areas:
            return self

        area = self.areas[area_number].set_ready_to_arm(value)

        return replace(
            self,
            areas=self.areas | {area_number: area},
        )

    def set_zone_alarm(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the alarm state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_alarm(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_zone_radio_battery_low(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the radio battery low state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_radio_battery_low(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_zone_bypassed(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the bypassed state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_bypassed(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_zone_closed(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the closed state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_closed(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_zone_sensor_watch_alarm(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the sensor watch alarm state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_sensor_watch_alarm(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_zone_trouble_alarm(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the trouble alarm state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_trouble_alarm(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_zone_supervise_alarm(
        self,
        zone_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the supervise alarm state of a zone."""
        if zone_number not in self.zones:
            return self

        zone = self.zones[zone_number].set_supervise_alarm(value)

        return replace(
            self,
            zones=self.zones | {zone_number: zone},
        )

    def set_output_on(
        self,
        output_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the output state."""
        if output_number not in self.outputs:
            return self

        output = self.outputs[output_number].set_on(value)

        return replace(
            self,
            outputs=self.outputs | {output_number: output},
        )

    def set_zone_expander_battery_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the battery fault state of a zone expander."""
        if expander_number not in self.zone_expanders:
            return self

        expander = self.zone_expanders[expander_number].set_battery_fault(value)

        return replace(
            self,
            zone_expanders=self.zone_expanders | {expander_number: expander},
        )

    def set_zone_expander_mains_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the mains fault state of a zone expander."""
        if expander_number not in self.zone_expanders:
            return self

        expander = self.zone_expanders[expander_number].set_mains_fault(value)

        return replace(
            self,
            zone_expanders=self.zone_expanders | {expander_number: expander},
        )

    def set_zone_expander_fuse_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the fuse fault state of a zone expander."""
        if expander_number not in self.zone_expanders:
            return self

        expander = self.zone_expanders[expander_number].set_fuse_fault(value)

        return replace(
            self,
            zone_expanders=self.zone_expanders | {expander_number: expander},
        )

    def set_zone_expander_tamper_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the tamper fault state of a zone expander."""
        if expander_number not in self.zone_expanders:
            return self

        expander = self.zone_expanders[expander_number].set_tamper_fault(value)

        return replace(
            self,
            zone_expanders=self.zone_expanders | {expander_number: expander},
        )

    def set_output_expander_battery_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the battery fault state of an output expander."""
        if expander_number not in self.output_expanders:
            return self

        expander = self.output_expanders[expander_number].set_battery_fault(value)

        return replace(
            self,
            output_expanders=self.output_expanders | {expander_number: expander},
        )

    def set_output_expander_mains_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the mains fault state of an output expander."""
        if expander_number not in self.output_expanders:
            return self

        expander = self.output_expanders[expander_number].set_mains_fault(value)

        return replace(
            self,
            output_expanders=self.output_expanders | {expander_number: expander},
        )

    def set_output_expander_fuse_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the fuse fault state of an output expander."""
        if expander_number not in self.output_expanders:
            return self

        expander = self.output_expanders[expander_number].set_fuse_fault(value)

        return replace(
            self,
            output_expanders=self.output_expanders | {expander_number: expander},
        )

    def set_output_expander_tamper_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the tamper fault state of an output expander."""
        if expander_number not in self.output_expanders:
            return self

        expander = self.output_expanders[expander_number].set_tamper_fault(value)

        return replace(
            self,
            output_expanders=self.output_expanders | {expander_number: expander},
        )

    def set_prox_expander_battery_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the battery fault state of a prox expander."""
        if expander_number not in self.prox_expanders:
            return self

        expander = self.prox_expanders[expander_number].set_battery_fault(value)

        return replace(
            self,
            prox_expanders=self.prox_expanders | {expander_number: expander},
        )

    def set_prox_expander_mains_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the mains fault state of a prox expander."""
        if expander_number not in self.prox_expanders:
            return self

        expander = self.prox_expanders[expander_number].set_mains_fault(value)

        return replace(
            self,
            prox_expanders=self.prox_expanders | {expander_number: expander},
        )

    def set_prox_expander_fuse_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the fuse fault state of a prox expander."""
        if expander_number not in self.prox_expanders:
            return self

        expander = self.prox_expanders[expander_number].set_fuse_fault(value)

        return replace(
            self,
            prox_expanders=self.prox_expanders | {expander_number: expander},
        )

    def set_prox_expander_tamper_fault(
        self,
        expander_number: int,
        value: bool,
    ) -> "PanelState":
        """Set the tamper fault state of a prox expander."""
        if expander_number not in self.prox_expanders:
            return self

        expander = self.prox_expanders[expander_number].set_tamper_fault(value)

        return replace(
            self,
            prox_expanders=self.prox_expanders | {expander_number: expander},
        )


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
