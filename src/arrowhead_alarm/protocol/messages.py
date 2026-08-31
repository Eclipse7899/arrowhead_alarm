"""Module for parsing alarm messages with various formats."""

from typing import Callable, Final

from .models import (
    CODE_STATUS,
    EXPANDER_STATUS,
    NUMBERED_STATUS,
    TIMESTAMPED_STATUS,
    USER_STATUS,
    AlarmState,
    PanelState,
    StatusResponse,
)

EXPANDER_CODE_DISPATCHER: Final[dict[tuple[str, str], Callable[[int, PanelState], PanelState]]] = {
    ("BF", "ZX"): lambda expander_number, panel: panel.set_zone_expander_battery_fault(
        expander_number, True
    ),
    ("BF", "OX"): lambda expander_number, panel: panel.set_output_expander_battery_fault(
        expander_number, True
    ),
    ("BF", "PX"): lambda expander_number, panel: panel.set_prox_expander_battery_fault(
        expander_number, True
    ),
    ("BR", "ZX"): lambda expander_number, panel: panel.set_zone_expander_battery_fault(
        expander_number, False
    ),
    ("BR", "OX"): lambda expander_number, panel: panel.set_output_expander_battery_fault(
        expander_number, False
    ),
    ("BR", "PX"): lambda expander_number, panel: panel.set_prox_expander_battery_fault(
        expander_number, False
    ),
    ("MR", "PX"): lambda expander_number, panel: panel.set_prox_expander_mains_fault(
        expander_number, False
    ),
    ("MR", "ZX"): lambda expander_number, panel: panel.set_zone_expander_mains_fault(
        expander_number, False
    ),
    ("MR", "OX"): lambda expander_number, panel: panel.set_output_expander_mains_fault(
        expander_number, False
    ),
    ("MF", "PX"): lambda expander_number, panel: panel.set_prox_expander_mains_fault(
        expander_number, True
    ),
    ("MF", "ZX"): lambda expander_number, panel: panel.set_zone_expander_mains_fault(
        expander_number, True
    ),
    ("MF", "OX"): lambda expander_number, panel: panel.set_output_expander_mains_fault(
        expander_number, True
    ),
    ("FR", "OX"): lambda expander_number, panel: panel.set_output_expander_fuse_fault(
        expander_number, False
    ),
    ("FR", "ZX"): lambda expander_number, panel: panel.set_zone_expander_fuse_fault(
        expander_number, False
    ),
    ("FR", "PX"): lambda expander_number, panel: panel.set_prox_expander_fuse_fault(
        expander_number, False
    ),
    ("FF", "OX"): lambda expander_number, panel: panel.set_output_expander_fuse_fault(
        expander_number, True
    ),
    ("FF", "ZX"): lambda expander_number, panel: panel.set_zone_expander_fuse_fault(
        expander_number, True
    ),
    ("FF", "PX"): lambda expander_number, panel: panel.set_prox_expander_fuse_fault(
        expander_number, True
    ),
    ("TR", "PX"): lambda expander_number, panel: panel.set_prox_expander_tamper_fault(
        expander_number, False
    ),
    ("TR", "ZX"): lambda expander_number, panel: panel.set_zone_expander_tamper_fault(
        expander_number, False
    ),
    ("TR", "OX"): lambda expander_number, panel: panel.set_output_expander_tamper_fault(
        expander_number, False
    ),
    ("TA", "PX"): lambda expander_number, panel: panel.set_prox_expander_tamper_fault(
        expander_number, True
    ),
    ("TA", "ZX"): lambda expander_number, panel: panel.set_zone_expander_tamper_fault(
        expander_number, True
    ),
    ("TA", "OX"): lambda expander_number, panel: panel.set_output_expander_tamper_fault(
        expander_number, True
    ),
}


def get_expander_status_operation(
    status: StatusResponse,
) -> Callable[[PanelState], PanelState]:
    """Return a function that mutates PanelState based on the expander status_response.

    Args:
        status: Status object.

    Returns: Function that mutates PanelState based on the expander status_response.

    """
    if status.expander_code is None or status.expander_number is None:
        raise ValueError(
            "Extender status_response, expander number are required for\
             expander status_response operations"
        )
    key = (status.code, status.expander_code)
    expander_num = status.expander_number
    operation = EXPANDER_CODE_DISPATCHER.get(key)
    if not operation:
        raise ValueError(f"Unsupported expander status_response: {key}")

    def panel_state_operation(panel: PanelState) -> PanelState:
        return operation(expander_num, panel)

    return panel_state_operation


NUMBERED_STATUS_DISPATCHER: Final[dict[str, Callable[[int, PanelState], PanelState]]] = {
    "A": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.ARMED_AWAY),
    "D": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.DISARMED),
    "AA": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.ALARM_TRIGGERED),
    "AR": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.DISARMED),
    "S": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.ARMED_STAY),
    "NR": lambda area_number, panel: panel.set_area_ready(area_number, False),
    "RO": lambda area_number, panel: panel.set_area_ready(area_number, True),
    "ZA": lambda zone_number, panel: panel.set_zone_alarm(zone_number, True),
    "ZBL": lambda zone_number, panel: panel.set_zone_radio_battery_low(zone_number, True),
    "ZBR": lambda zone_number, panel: panel.set_zone_radio_battery_low(zone_number, False),
    "ZBY": lambda zone_number, panel: panel.set_zone_bypassed(zone_number, True),
    "ZBYR": lambda zone_number, panel: panel.set_zone_bypassed(zone_number, False),
    "ZC": lambda zone_number, panel: panel.set_zone_closed(zone_number, True),
    "ZIA": lambda zone_number, panel: panel.set_zone_sensor_watch_alarm(zone_number, True),
    "ZIR": lambda zone_number, panel: panel.set_zone_sensor_watch_alarm(zone_number, False),
    "ZO": lambda zone_number, panel: panel.set_zone_closed(zone_number, False),
    "ZR": lambda zone_number, panel: panel.set_zone_alarm(zone_number, False),
    "ZT": lambda zone_number, panel: panel.set_zone_trouble_alarm(zone_number, True),
    "ZTR": lambda zone_number, panel: panel.set_zone_trouble_alarm(zone_number, False),
    "ZSA": lambda zone_number, panel: panel.set_zone_supervise_alarm(zone_number, True),
    "ZSR": lambda zone_number, panel: panel.set_zone_supervise_alarm(zone_number, False),
    "OO": lambda output_number, panel: panel.set_output_on(output_number, True),
    "OR": lambda output_number, panel: panel.set_output_on(output_number, False),
}


def get_numbered_status_operation(
    numbered_status: StatusResponse,
) -> Callable[[PanelState], PanelState]:
    """Return a function that mutates PanelState based on the numbered status_response.

    Args:
        numbered_status: Status object.

    Returns: Function that mutates PanelState based on the numbered status_response.

    """
    if numbered_status.code not in NUMBERED_STATUS_DISPATCHER:
        raise ValueError(f"Unsupported numbered status_response: {numbered_status.code}")
    if numbered_status.number is None:
        raise ValueError("Area number is required for numbered status_response operations")

    operation = NUMBERED_STATUS_DISPATCHER[numbered_status.code]
    number = numbered_status.number

    def panel_state_operation(panel: PanelState) -> PanelState:
        return operation(number, panel)

    return panel_state_operation


USER_STATUS_DISPATCHER: Final[dict[str, Callable[[int, PanelState], PanelState]]] = {
    "A": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.ARMED_AWAY),
    "D": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.DISARMED),
    "S": lambda area_number, panel: panel.set_area_state(area_number, AlarmState.ARMED_STAY),
}


def get_user_status_operation(
    status: StatusResponse,
) -> Callable[[PanelState], PanelState]:
    """Return a function that mutates PanelState based on the user status_response.

    Args:
        status: Status object.

    Returns: Function that mutates PanelState based on the user status_response.

    """
    if status.code not in USER_STATUS_DISPATCHER:
        raise ValueError(f"Unsupported user status_response: {status.code}")
    if status.number is None:
        raise ValueError("Area number is required for user status_response operations")
    if status.user_number is None:
        raise ValueError("User number is required for user status_response operations")

    operation = USER_STATUS_DISPATCHER[status.code]
    number = status.number

    def panel_state_operation(panel: PanelState) -> PanelState:
        return operation(number, panel)

    return panel_state_operation


TIMESTAMPED_STATUS_DISPATCHER: Final[dict[str, Callable[[int, float, PanelState], PanelState]]] = {
    "EDA": lambda area, timestamp, panel: panel.set_area_state(area, AlarmState.ARMING_AWAY),
    "EDS": lambda area, timestamp, panel: panel.set_area_state(area, AlarmState.ARMING_STAY),
    "ZEDS": lambda zone, timestamp, panel: panel,
}


def get_timestamped_status_operation(
    status_response: StatusResponse,
) -> Callable[[PanelState], PanelState]:
    """Return a function that mutates PanelState based on the timestamped status_response.

    Args:
        status_response: Status object.

    Returns: Function that mutates PanelState based on the timestamped status_response.

    """
    if status_response.code not in TIMESTAMPED_STATUS_DISPATCHER:
        raise ValueError(f"Unsupported timestamped status_response: {status_response.code}")
    if status_response.number is None:
        raise ValueError("Area number is required for timestamped status_response operations")
    if status_response.timestamp is None:
        raise ValueError("Timestamp is required for timestamped status_response operations")

    operation = TIMESTAMPED_STATUS_DISPATCHER[status_response.code]
    number = status_response.number
    timestamp = status_response.timestamp

    def panel_state_operation(panel: PanelState) -> PanelState:
        return operation(number, timestamp, panel)

    return panel_state_operation


STATUS_CODE_DISPATCHER: Final[dict[str, Callable[[PanelState], PanelState]]] = {
    "RO": lambda panel: panel.set_ready_to_arm(True),
    "NR": lambda panel: panel.set_ready_to_arm(False),
    "BF": lambda panel: panel.set_battery_fault(True),
    "BR": lambda panel: panel.set_battery_fault(False),
    "CAL": lambda panel: panel.set_monitoring_station_active(True),
    "CLF": lambda panel: panel.set_monitoring_station_active(False),
    "DF": lambda panel: panel.set_dialer_fault(True),
    "DR": lambda panel: panel.set_dialer_fault(False),
    "LF": lambda panel: panel.set_dialer_line_fault(True),
    "LR": lambda panel: panel.set_dialer_line_fault(False),
    "MF": lambda panel: panel.set_mains_fault(True),
    "MR": lambda panel: panel.set_mains_fault(False),
    "TA": lambda panel: panel.set_tamper_fault(True),
    "TR": lambda panel: panel.set_tamper_fault(False),
    "FF": lambda panel: panel.set_fuse_fault(True),
    "FR": lambda panel: panel.set_fuse_fault(False),
    "RIF": lambda panel: panel.set_receiver_fault(True),
    "RIR": lambda panel: panel.set_receiver_fault(False),
}


def get_status_code_operation(
    status_response: StatusResponse,
) -> Callable[[PanelState], PanelState]:
    """Return a function that mutates PanelState based on the status_response.

    Args:
        status_response: Status object.

    Returns: Function that mutates PanelState based on the status_response.

    """
    panel_state_operation = STATUS_CODE_DISPATCHER.get(status_response.code)
    if not panel_state_operation:
        raise ValueError(f"Unsupported status_response: {status_response.code}")
    return panel_state_operation


Status = None
STATUS_TYPE_DISPATCHER: Final[
    dict[int, Callable[[StatusResponse], Callable[[PanelState], PanelState]]]
] = {
    CODE_STATUS: get_status_code_operation,
    NUMBERED_STATUS: get_numbered_status_operation,
    EXPANDER_STATUS: get_expander_status_operation,
    USER_STATUS: get_user_status_operation,
    TIMESTAMPED_STATUS: get_timestamped_status_operation,
}


def get_status_operation(
    status_response: StatusResponse,
) -> Callable[[PanelState], PanelState]:
    """Return a function that mutates PanelState based on the status_response type.

    Args:
        status_response: Status object.

    Returns: Function that mutates PanelState based on the status_response type.

    """
    operation_getter = STATUS_TYPE_DISPATCHER.get(status_response.flags)
    if not operation_getter:
        raise ValueError(f"Unsupported status_response type: {status_response.flags}")
    return operation_getter(status_response)
