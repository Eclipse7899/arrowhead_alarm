"""Default data structures and constants for Arrowhead alarm panels."""

from typing import Dict

from .models import AlarmState, Area, Expander, Output, PanelState, VersionInfo, Zone

DEFAULT_MAX_ZONES = 8
DEFAULT_MAX_USERS = 2000
DEFAULT_MAX_OUTPUTS = 4
DEFAULT_MAX_AREAS = 16

DEFAULT_VIRTUAL_KEYPAD_NUM = 32

ZONE_EXPANDER_COUNT = 32
OUTPUT_EXPANDER_COUNT = 8
PROX_EXPANDER_COUNT = 32

MINIMUM_MODE_4_PANEL_VERSION = VersionInfo(major=10, minor=3, patch=50)


def get_default_zones() -> Dict[int, Zone]:
    """Generate default zones based on default constants.

    Returns:
        A dictionary mapping zone numbers to default Zone objects.
    """
    return {
        i: Zone(
            number=i,
            supervise_alarm=False,
            bypassed=False,
            trouble_alarm=False,
            alarm=False,
            radio_battery_low=False,
            closed=True,
            sensor_watch_alarm=False,
        )
        for i in range(1, DEFAULT_MAX_ZONES + 1)
    }


def get_default_areas() -> Dict[int, Area]:
    """Generate default areas based on default constants.

    Returns:
        A dictionary mapping area numbers to default Area objects.
    """
    return {
        i: Area(number=i, state=AlarmState.DISARMED, ready_to_arm=True)
        for i in range(1, DEFAULT_MAX_AREAS + 1)
    }


def get_expanders(count: int) -> Dict[int, Expander]:
    """Generate default expanders based on default constants.

    Args:
        count: The number of expanders to generate.

    Returns:
        A dictionary mapping expander IDs to default Expander objects.
    """
    return {
        i: Expander(
            number=i,
            tamper_fault=False,
            mains_fault=False,
            battery_fault=False,
            fuse_fault=False,
        )
        for i in range(1, count + 1)
    }


def get_default_outputs() -> Dict[int, Output]:
    """Generate default outputs based on default constants.

    Returns:
        A dictionary mapping output numbers to default Output objects.
    """
    return {i: Output(number=i, on=False) for i in range(1, DEFAULT_MAX_OUTPUTS + 1)}


def get_default_state() -> PanelState:
    """Generate the default panel state.

    Returns:
        A PanelState initialized with default values.
    """
    return PanelState(
        info=None,
        ready_to_arm=False,
        battery_fault=False,
        mains_fault=False,
        tamper_fault=False,
        dialer_fault=False,
        dialer_line_fault=False,
        fuse_fault=False,
        monitoring_station_active=False,
        receiver_fault=None,
        pendant_battery_fault=None,
        rf_battery_low=None,
        sensor_watch_alarm=None,
        zones=get_default_zones(),
        outputs=get_default_outputs(),
        areas=get_default_areas(),
        zone_expanders=get_expanders(ZONE_EXPANDER_COUNT),
        output_expanders=get_expanders(OUTPUT_EXPANDER_COUNT),
        prox_expanders=get_expanders(PROX_EXPANDER_COUNT),
    )
