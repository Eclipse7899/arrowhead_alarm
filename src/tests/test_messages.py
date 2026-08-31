"""Comprehensive unit tests for alarm status operation dispatchers."""
from typing import Callable
from unittest.mock import MagicMock, sentinel

import pytest

from arrowhead_alarm.protocol.messages import (
    EXPANDER_CODE_DISPATCHER,
    EXPANDER_STATUS,
    NUMBERED_STATUS,
    CODE_STATUS,
    STATUS_TYPE_DISPATCHER,
    TIMESTAMPED_STATUS,
    USER_STATUS,
    get_expander_status_operation,
    get_numbered_status_operation,
    get_status_code_operation,
    get_status_operation,
    get_timestamped_status_operation,
    get_user_status_operation,
)
from arrowhead_alarm.protocol.models import AlarmState, StatusResponse, StatusFlags, PanelState


def make_status(
    code: str,
    number: int | None = None,
    expander_code: str | None = None,
    expander_number: int | None = None,
    user_number: int | None = None,
    timestamp: float | None = None,
) -> StatusResponse:
    return StatusResponse(
        code=code,
        number=number,
        expander_code=expander_code,
        expander_number=expander_number,
        user_number=user_number,
        timestamp=timestamp,
    )


@pytest.fixture
def panel():
    return MagicMock()


@pytest.mark.parametrize(
    ("code", "method_name", "argument"),
    [
        ("RO", "set_ready_to_arm", True),
        ("NR", "set_ready_to_arm", False),
        ("BF", "set_battery_fault", True),
        ("BR", "set_battery_fault", False),
        ("CAL", "set_monitoring_station_active", True),
        ("CLF", "set_monitoring_station_active", False),
        ("DF", "set_dialer_fault", True),
        ("DR", "set_dialer_fault", False),
        ("LF", "set_dialer_line_fault", True),
        ("LR", "set_dialer_line_fault", False),
        ("MF", "set_mains_fault", True),
        ("MR", "set_mains_fault", False),
        ("TA", "set_tamper_fault", True),
        ("TR", "set_tamper_fault", False),
        ("FF", "set_fuse_fault", True),
        ("FR", "set_fuse_fault", False),
        ("RIF", "set_receiver_fault", True),
        ("RIR", "set_receiver_fault", False),
    ],
)
def test_get_status_code_operation(
    panel,
    code,
    method_name,
    argument,
):
    expected = sentinel.result
    getattr(panel, method_name).return_value = expected

    operation = get_status_code_operation(make_status(code))

    assert operation(panel) is expected
    getattr(panel, method_name).assert_called_once_with(argument)


@pytest.mark.parametrize(
    "code",
    [
        "PBF1",
        "PBR1",
        "PA",
        "PC",
        "FA",
        "FC",
        "MA",
        "MC",
        "UNKNOWN",
    ],
)
def test_get_status_code_operation_rejects_unsupported_codes(code):
    with pytest.raises(
        ValueError,
        match=rf"Unsupported status_response: {code}",
    ):
        get_status_code_operation(make_status(code))


@pytest.mark.parametrize(
    (
        "status_code",
        "expander_code",
        "method_name",
        "expander_number",
        "expected_value",
    ),
    [
        ("BF", "ZX", "set_zone_expander_battery_fault", 1, True),
        ("BF", "OX", "set_output_expander_battery_fault", 2, True),
        ("BF", "PX", "set_prox_expander_battery_fault", 3, True),
        ("BR", "ZX", "set_zone_expander_battery_fault", 4, False),
        ("BR", "OX", "set_output_expander_battery_fault", 5, False),
        ("BR", "PX", "set_prox_expander_battery_fault", 6, False),
        ("MF", "PX", "set_prox_expander_mains_fault", 7, True),
        ("MF", "ZX", "set_zone_expander_mains_fault", 8, True),
        ("MF", "OX", "set_output_expander_mains_fault", 9, True),
        ("MR", "PX", "set_prox_expander_mains_fault", 10, False),
        ("MR", "ZX", "set_zone_expander_mains_fault", 11, False),
        ("MR", "OX", "set_output_expander_mains_fault", 12, False),
        ("FR", "OX", "set_output_expander_fuse_fault", 13, False),
        ("FR", "ZX", "set_zone_expander_fuse_fault", 14, False),
        ("FR", "PX", "set_prox_expander_fuse_fault", 15, False),
        ("FF", "OX", "set_output_expander_fuse_fault", 16, True),
        ("FF", "ZX", "set_zone_expander_fuse_fault", 17, True),
        ("FF", "PX", "set_prox_expander_fuse_fault", 18, True),
        ("TR", "PX", "set_prox_expander_tamper_fault", 19, False),
        ("TR", "ZX", "set_zone_expander_tamper_fault", 20, False),
        ("TR", "OX", "set_output_expander_tamper_fault", 21, False),
        ("TA", "PX", "set_prox_expander_tamper_fault", 22, True),
        ("TA", "ZX", "set_zone_expander_tamper_fault", 23, True),
        ("TA", "OX", "set_output_expander_tamper_fault", 24, True),
    ],
)
def test_get_expander_status_operation(
    panel,
    status_code,
    expander_code,
    method_name,
    expander_number,
    expected_value,
):
    expected = sentinel.result
    getattr(panel, method_name).return_value = expected

    status = make_status(
        code=status_code,
        expander_code=expander_code,
        expander_number=expander_number,
    )

    operation = get_expander_status_operation(status)

    assert operation(panel) is expected
    getattr(panel, method_name).assert_called_once_with(
        expander_number,
        expected_value,
    )


@pytest.mark.parametrize(
    ("expander_code", "expander_number"),
    [
        (None, 1),
        ("ZX", None),
        (None, None),
    ],
)
def test_get_expander_status_operation_requires_expander_fields(
    expander_code,
    expander_number,
):
    status = make_status(
        code="BF",
        expander_code=expander_code,
        expander_number=expander_number,
    )

    with pytest.raises(
        ValueError,
        match="Extender status_response, expander number are required",
    ):
        get_expander_status_operation(status)


@pytest.mark.parametrize(
    ("code", "expander_code"),
    [
        ("BF", "XX"),
        ("BF", "ZX2"),
        ("RO", "ZX"),
        ("CAL", "ZX"),
    ],
)
def test_get_expander_status_operation_rejects_unsupported_pairs(
    code,
    expander_code,
):
    status = make_status(
        code=code,
        expander_code=expander_code,
        expander_number=1,
    )

    with pytest.raises(
        ValueError,
        match=r"Unsupported expander status_response:",
    ):
        get_expander_status_operation(status)


@pytest.mark.parametrize(
    ("code", "method_name", "expected_value"),
    [
        ("A", "set_area_state", AlarmState.ARMED_AWAY),
        ("D", "set_area_state", AlarmState.DISARMED),
        ("AA", "set_area_state", AlarmState.ALARM_TRIGGERED),
        ("AR", "set_area_state", AlarmState.DISARMED),
        ("S", "set_area_state", AlarmState.ARMED_STAY),
        ("NR", "set_area_ready", False),
        ("RO", "set_area_ready", True),
        ("ZA", "set_zone_alarm", True),
        ("ZBL", "set_zone_radio_battery_low", True),
        ("ZBR", "set_zone_radio_battery_low", False),
        ("ZBY", "set_zone_bypassed", True),
        ("ZBYR", "set_zone_bypassed", False),
        ("ZC", "set_zone_closed", True),
        ("ZIA", "set_zone_sensor_watch_alarm", True),
        ("ZIR", "set_zone_sensor_watch_alarm", False),
        ("ZO", "set_zone_closed", False),
        ("ZR", "set_zone_alarm", False),
        ("ZT", "set_zone_trouble_alarm", True),
        ("ZTR", "set_zone_trouble_alarm", False),
        ("ZSA", "set_zone_supervise_alarm", True),
        ("ZSR", "set_zone_supervise_alarm", False),
        ("OO", "set_output_on", True),
        ("OR", "set_output_on", False),
    ],
)
def test_get_numbered_status_operation(
    panel,
    code,
    method_name,
    expected_value,
):
    expected = sentinel.result
    getattr(panel, method_name).return_value = expected

    number = 37
    operation = get_numbered_status_operation(
        make_status(
            code=code,
            number=number,
        )
    )

    assert operation(panel) is expected
    getattr(panel, method_name).assert_called_once_with(
        number,
        expected_value,
    )


@pytest.mark.parametrize(
    "code",
    [
        "EA",
        "ES",
        "UNKNOWN",
    ],
)
def test_get_numbered_status_operation_rejects_unsupported_codes(code):
    with pytest.raises(
        ValueError,
        match=rf"Unsupported numbered status_response: {code}",
    ):
        get_numbered_status_operation(
            make_status(
                code=code,
                number=1,
            )
        )


@pytest.mark.parametrize(
    "code",
    [
        "A",
        "D",
        "AA",
        "AR",
        "S",
        "NR",
        "RO",
        "ZA",
        "ZBL",
        "ZBR",
        "ZBY",
        "ZBYR",
        "ZC",
        "ZIA",
        "ZIR",
        "ZO",
        "ZR",
        "ZT",
        "ZTR",
        "ZSA",
        "ZSR",
        "OO",
        "OR",
    ],
)
def test_get_numbered_status_operation_requires_number(code):
    with pytest.raises(
        ValueError,
        match="Area number is required for numbered status_response operations",
    ):
        get_numbered_status_operation(
            make_status(code=code)
        )


@pytest.mark.parametrize(
    ("code", "expected_state"),
    [
        ("A", AlarmState.ARMED_AWAY),
        ("D", AlarmState.DISARMED),
        ("S", AlarmState.ARMED_STAY),
    ],
)
def test_get_user_status_operation(
    panel,
    code,
    expected_state,
):
    panel.set_area_state.return_value = sentinel.result

    area_number = 4
    user_number = 27

    operation = get_user_status_operation(
        make_status(
            code=code,
            number=area_number,
            user_number=user_number,
        )
    )

    assert operation(panel) is sentinel.result
    panel.set_area_state.assert_called_once_with(
        area_number,
        expected_state,
    )


@pytest.mark.parametrize(
    "code",
    ["X", "EA", "UNKNOWN"],
)
def test_get_user_status_operation_rejects_unsupported_codes(code):
    with pytest.raises(
        ValueError,
        match=rf"Unsupported user status_response: {code}",
    ):
        get_user_status_operation(
            make_status(
                code=code,
                number=1,
                user_number=2,
            )
        )


def test_get_user_status_operation_requires_area_number():
    with pytest.raises(
        ValueError,
        match="Area number is required for user status_response operations",
    ):
        get_user_status_operation(
            make_status(
                code="A",
                user_number=2,
            )
        )


def test_get_user_status_operation_requires_user_number():
    with pytest.raises(
        ValueError,
        match="User number is required for user status_response operations",
    ):
        get_user_status_operation(
            make_status(
                code="A",
                number=1,
            )
        )


@pytest.mark.parametrize(
    ("code", "expected_state"),
    [
        ("EDA", AlarmState.ARMING_AWAY),
        ("EDS", AlarmState.ARMING_STAY),
    ],
)
def test_get_timestamped_status_operation(
    panel,
    code,
    expected_state,
):
    panel.set_area_state.return_value = sentinel.result

    number = 2
    timestamp = 123.456

    operation = get_timestamped_status_operation(
        make_status(
            code=code,
            number=number,
            timestamp=timestamp,
        )
    )

    assert operation(panel) is sentinel.result
    panel.set_area_state.assert_called_once_with(
        number,
        expected_state,
    )


def test_get_timestamped_status_operation_zeds_is_noop(panel):
    operation = get_timestamped_status_operation(
        make_status(
            code="ZEDS",
            number=12,
            timestamp=456.789,
        )
    )

    assert operation(panel) is panel
    panel.assert_not_called()


@pytest.mark.parametrize(
    "code",
    ["EA", "ES", "UNKNOWN"],
)
def test_get_timestamped_status_operation_rejects_unsupported_codes(code):
    with pytest.raises(
        ValueError,
        match=rf"Unsupported timestamped status_response: {code}",
    ):
        get_timestamped_status_operation(
            make_status(
                code=code,
                number=1,
                timestamp=1.0,
            )
        )


@pytest.mark.parametrize(
    "code",
    ["EDA", "EDS", "ZEDS"],
)
def test_get_timestamped_status_operation_requires_number(code):
    with pytest.raises(
        ValueError,
        match="Area number is required for timestamped status_response operations",
    ):
        get_timestamped_status_operation(
            make_status(
                code=code,
                timestamp=1.0,
            )
        )


@pytest.mark.parametrize(
    "code",
    ["EDA", "EDS", "ZEDS"],
)
def test_get_timestamped_status_operation_requires_timestamp(code):
    with pytest.raises(
        ValueError,
        match="Timestamp is required for timestamped status_response operations",
    ):
        get_timestamped_status_operation(
            make_status(
                code=code,
                number=1,
            )
        )


@pytest.mark.parametrize(
    ("flags", "status"),
    [
        (CODE_STATUS, make_status("RO")),
        (NUMBERED_STATUS, make_status("A", number=1)),
        (
            EXPANDER_STATUS,
            make_status(
                "BF",
                expander_code="ZX",
                expander_number=1,
            ),
        ),
        (
            USER_STATUS,
            make_status(
                "A",
                number=1,
                user_number=2,
            ),
        ),
        (
            TIMESTAMPED_STATUS,
            make_status(
                "EDA",
                number=1,
                timestamp=123.0,
            ),
        ),
    ],
)
def test_status_response_flags(
    flags,
    status,
):
    assert status.flags == flags


OperationGetter = Callable[
    [StatusResponse],
    Callable[[PanelState], PanelState],
]

@pytest.mark.parametrize(
    ("flags", "getter"),
    [
        (CODE_STATUS, get_status_code_operation),
        (NUMBERED_STATUS, get_numbered_status_operation),
        (EXPANDER_STATUS, get_expander_status_operation),
        (USER_STATUS, get_user_status_operation),
        (TIMESTAMPED_STATUS, get_timestamped_status_operation),
    ],
)
def test_status_type_dispatcher(
    flags: int,
    getter: OperationGetter,
) -> None:
    assert STATUS_TYPE_DISPATCHER[flags] is getter


@pytest.mark.parametrize(
    ("status", "method_name", "expected_args"),
    [
        (
            make_status("RO"),
            "set_ready_to_arm",
            (True,),
        ),
        (
            make_status("BF"),
            "set_battery_fault",
            (True,),
        ),
        (
            make_status("A", number=3),
            "set_area_state",
            (3, AlarmState.ARMED_AWAY),
        ),
        (
            make_status("ZBY", number=8),
            "set_zone_bypassed",
            (8, True),
        ),
        (
            make_status("OO", number=5),
            "set_output_on",
            (5, True),
        ),
        (
            make_status(
                "MF",
                expander_code="OX",
                expander_number=2,
            ),
            "set_output_expander_mains_fault",
            (2, True),
        ),
        (
            make_status(
                "D",
                number=4,
                user_number=17,
            ),
            "set_area_state",
            (4, AlarmState.DISARMED),
        ),
        (
            make_status(
                "EDS",
                number=6,
                timestamp=42.0,
            ),
            "set_area_state",
            (6, AlarmState.ARMING_STAY),
        ),
    ],
)
def test_get_status_operation_end_to_end(
    panel,
    status,
    method_name,
    expected_args,
):
    expected = sentinel.result
    getattr(panel, method_name).return_value = expected

    operation = get_status_operation(status)

    assert operation(panel) is expected
    getattr(panel, method_name).assert_called_once_with(*expected_args)


@pytest.mark.parametrize(
    "flags",
    [-1, 0, 999, None],
)
def test_get_status_operation_rejects_unknown_flags(flags):

    invalid_flags = StatusFlags(1 << 20)

    class InvalidStatusResponse(StatusResponse):
        @property
        def flags(self) -> StatusFlags:
            return invalid_flags

    invalid_status = InvalidStatusResponse(code="RO")
    with pytest.raises(
        ValueError,
        match=rf"Unsupported status_response type: {invalid_flags}",
    ):
        get_status_operation(invalid_status)


def test_expander_dispatcher_contains_expected_entries():
    expected_keys = {
        ("BF", "ZX"),
        ("BF", "OX"),
        ("BF", "PX"),
        ("BR", "ZX"),
        ("BR", "OX"),
        ("BR", "PX"),
        ("MF", "PX"),
        ("MF", "ZX"),
        ("MF", "OX"),
        ("MR", "PX"),
        ("MR", "ZX"),
        ("MR", "OX"),
        ("FR", "OX"),
        ("FR", "ZX"),
        ("FR", "PX"),
        ("FF", "OX"),
        ("FF", "ZX"),
        ("FF", "PX"),
        ("TR", "PX"),
        ("TR", "ZX"),
        ("TR", "OX"),
        ("TA", "PX"),
        ("TA", "ZX"),
        ("TA", "OX"),
    }

    assert set(EXPANDER_CODE_DISPATCHER) == expected_keys


@pytest.mark.parametrize(
    ("flags", "code"),
    [
        (CODE_STATUS, "PBF1"),
        (CODE_STATUS, "PBR1"),
        (CODE_STATUS, "PA"),
        (CODE_STATUS, "PC"),
        (CODE_STATUS, "FA"),
        (CODE_STATUS, "FC"),
        (CODE_STATUS, "MA"),
        (CODE_STATUS, "MC"),
        (NUMBERED_STATUS, "EA"),
        (NUMBERED_STATUS, "ES"),
    ],
)
def test_protocol_messages_not_implemented(
    flags,
    code,
):
    if flags == CODE_STATUS:
        status = make_status(code)
    else:
        status = make_status(code, number=1)

    assert status.flags == flags

    with pytest.raises(ValueError):
        get_status_operation(status)