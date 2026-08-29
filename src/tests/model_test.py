from dataclasses import replace

import pytest

from arrowhead_alarm.protocol.models import (
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
    StatusFlags,
    StatusResponse,
    UserPin,
    VersionInfo,
    Zone, STATUS_CODE, NUMBERED_STATUS, EXPANDER_STATUS, USER_STATUS, TIMESTAMPED_STATUS,
)


@pytest.fixture
def version() -> VersionInfo:
    return VersionInfo(1, 2, 3)


@pytest.fixture
def panel_state() -> PanelState:
    area = Area(
        area_number=1,
        state=AlarmState.DISARMED,
        ready_to_arm=True,
    )

    zone = Zone(
        zone_number=1,
        supervise_alarm=False,
        trouble_alarm=False,
        bypassed=False,
        alarm=False,
        radio_battery_low=False,
        zone_closed=True,
        sensor_watch_alarm=False,
    )

    expander = Expander(
        expander_id=1,
        tamper_alarm_triggered=False,
        mains_fault=False,
        battery_fault=False,
        fuse_fault=False,
    )

    output = Output(
        output_number=1,
        on=False,
    )

    return PanelState(
        ready_to_arm=True,
        battery_fault=False,
        mains_fault=False,
        tamper_alarm_triggered=False,
        line_fault=False,
        dialer_fault=False,
        dialer_line_fault=False,
        fuse_fault=False,
        monitoring_station_active=False,
        dialer_active=False,
        code_tamper=False,
        receiver_fault=None,
        pendant_battery_fault=None,
        rf_battery_low=None,
        sensor_watch_alarm=None,
        zones={1: zone},
        outputs={1: output},
        areas={1: area},
        zone_expanders={1: expander},
        output_expanders={1: expander},
        prox_expanders={1: expander},
    )


def test_status_flags_values() -> None:
    assert StatusFlags.CODE == 1
    assert StatusFlags.NUMBER == 2
    assert StatusFlags.EXPANDER_CODE == 4
    assert StatusFlags.EXPANDER_NUMBER == 8
    assert StatusFlags.USER_NUMBER == 16
    assert StatusFlags.TIMESTAMP == 32


def test_status_flag_combinations() -> None:
    assert StatusFlags.CODE | StatusFlags.NUMBER == 3
    assert StatusFlags.CODE | StatusFlags.EXPANDER_CODE == 5
    assert (
        StatusFlags.CODE
        | StatusFlags.EXPANDER_CODE
        | StatusFlags.EXPANDER_NUMBER
        == 13
    )
    assert (
        StatusFlags.CODE
        | StatusFlags.NUMBER
        | StatusFlags.USER_NUMBER
        == 19
    )
    assert (
        StatusFlags.CODE
        | StatusFlags.NUMBER
        | StatusFlags.TIMESTAMP
        == 35
    )


def test_status_type_constants() -> None:
    assert STATUS_CODE == StatusFlags.CODE
    assert NUMBERED_STATUS == (
        StatusFlags.CODE | StatusFlags.NUMBER
    )
    assert EXPANDER_STATUS == (
        StatusFlags.CODE
        | StatusFlags.EXPANDER_CODE
        | StatusFlags.EXPANDER_NUMBER
    )
    assert USER_STATUS == (
        StatusFlags.CODE
        | StatusFlags.NUMBER
        | StatusFlags.USER_NUMBER
    )
    assert TIMESTAMPED_STATUS == (
        StatusFlags.CODE
        | StatusFlags.NUMBER
        | StatusFlags.TIMESTAMP
    )


def test_protocol_mode_values() -> None:
    assert ProtocolMode.MODE_1.value == 1
    assert ProtocolMode.MODE_2.value == 2
    assert ProtocolMode.MODE_3.value == 3
    assert ProtocolMode.MODE_4.value == 4


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (
            VersionInfo(1, 2, 3),
            (1, 2, 3),
        ),
        (
            VersionInfo(0, 0, 0),
            (0, 0, 0),
        ),
        (
            VersionInfo(10, 20, 30),
            (10, 20, 30),
        ),
    ],
)
def test_version_info_as_tuple(
    version: VersionInfo,
    expected: tuple[int, int, int],
) -> None:
    assert version._as_tuple() == expected


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (VersionInfo(1, 0, 0), VersionInfo(2, 0, 0)),
        (VersionInfo(1, 1, 0), VersionInfo(1, 2, 0)),
        (VersionInfo(1, 2, 3), VersionInfo(1, 2, 4)),
    ],
)
def test_version_info_less_than(
    left: VersionInfo,
    right: VersionInfo,
) -> None:
    assert left < right
    assert not right < left


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (VersionInfo(2, 0, 0), VersionInfo(1, 0, 0)),
        (VersionInfo(1, 2, 0), VersionInfo(1, 1, 0)),
        (VersionInfo(1, 2, 4), VersionInfo(1, 2, 3)),
    ],
)
def test_version_info_greater_than(
    left: VersionInfo,
    right: VersionInfo,
) -> None:
    assert left > right
    assert not right > left


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (VersionInfo(1, 2, 3), VersionInfo(1, 2, 3)),
        (VersionInfo(1, 2, 3), VersionInfo(1, 2, 4)),
        (VersionInfo(1, 2, 3), VersionInfo(1, 3, 3)),
        (VersionInfo(1, 2, 3), VersionInfo(2, 2, 3)),
    ],
)
def test_version_info_less_than_or_equal(
    left: VersionInfo,
    right: VersionInfo,
) -> None:
    assert left <= right


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (VersionInfo(1, 2, 3), VersionInfo(1, 2, 3)),
        (VersionInfo(1, 2, 4), VersionInfo(1, 2, 3)),
        (VersionInfo(1, 3, 3), VersionInfo(1, 2, 3)),
        (VersionInfo(2, 2, 3), VersionInfo(1, 2, 3)),
    ],
)
def test_version_info_greater_than_or_equal(
    left: VersionInfo,
    right: VersionInfo,
) -> None:
    assert left >= right


def test_version_info_equal_versions(version: VersionInfo) -> None:
    assert version == VersionInfo(1, 2, 3)
    assert not version < VersionInfo(1, 2, 3)
    assert not version > VersionInfo(1, 2, 3)
    assert version <= VersionInfo(1, 2, 3)
    assert version >= VersionInfo(1, 2, 3)


@pytest.mark.parametrize(
    ("version", "other"),
    [
        (VersionInfo(1, 2, 3), VersionInfo(2, 0, 0)),
        (VersionInfo(2, 0, 0), VersionInfo(1, 2, 3)),
        (VersionInfo(1, 2, 3), VersionInfo(1, 2, 4)),
    ],
)
def test_version_info_ordering(version: VersionInfo, other: VersionInfo) -> None:
    assert (version < other) != (version > other)


def test_user_pin() -> None:
    user_pin = UserPin(user_id=12, pin=3456)

    assert user_pin.user_id == 12
    assert user_pin.pin == 3456


def test_command_payload_without_args() -> None:
    command = CommandPayload(keyword="VERSION")

    assert command.build() == "VERSION"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            CommandPayload(keyword="MODE", args=[1]),
            "MODE 1",
        ),
        (
            CommandPayload(keyword="ARM", args=[1, 2]),
            "ARM 1 2",
        ),
        (
            CommandPayload(keyword="TEST", args=["ABC"]),
            "TEST ABC",
        ),
        (
            CommandPayload(keyword="TEST", args=[1, "ABC", 2]),
            "TEST 1 ABC 2",
        ),
    ],
)
def test_command_payload_build(
    payload: CommandPayload,
    expected: str,
) -> None:
    assert payload.build() == expected


@pytest.mark.parametrize(
    "args",
    [
        None,
        [],
    ],
)
def test_command_payload_empty_args(
    args: list[int | str] | None,
) -> None:
    payload = CommandPayload(
        keyword="TEST",
        args=args,
    )

    assert payload.build() == "TEST"


def test_command_payload_is_frozen() -> None:
    payload = CommandPayload(
        keyword="TEST",
        args=[1],
    )

    with pytest.raises(AttributeError):
        payload.keyword = "OTHER"  # ty: ignore[invalid-assignment]


def test_error_response() -> None:
    response = ErrorResponse(error_code=4)

    assert response.error_code == 4


def test_ok_response() -> None:
    response = OkResponse(
        keyword="VERSION",
        data="value",
    )

    assert response.keyword == "VERSION"
    assert response.data == "value"


@pytest.mark.parametrize(
    ("initial", "expected"),
    [
        (
            Area(
                area_number=1,
                state=AlarmState.DISARMED,
                ready_to_arm=True,
            ),
            AlarmState.ARMED_AWAY,
        ),
        (
            Area(
                area_number=5,
                state=AlarmState.ARMED_STAY,
                ready_to_arm=False,
            ),
            AlarmState.DISARMED,
        ),
    ],
)
def test_area_set_state(
    initial: Area,
    expected: AlarmState,
) -> None:
    result = initial.set_state(expected)

    assert result is not initial
    assert result.state is expected
    assert result.area_number == initial.area_number
    assert result.ready_to_arm == initial.ready_to_arm
    assert initial.state != expected


@pytest.mark.parametrize("value", [True, False])
def test_area_set_ready_to_arm(value: bool) -> None:
    initial = Area(
        area_number=1,
        state=AlarmState.DISARMED,
        ready_to_arm=not value,
    )

    result = initial.set_ready_to_arm(value)

    assert result is not initial
    assert result.ready_to_arm is value
    assert result.area_number == initial.area_number
    assert result.state is initial.state


@pytest.fixture
def zone() -> Zone:
    return Zone(
        zone_number=1,
        supervise_alarm=False,
        trouble_alarm=False,
        bypassed=False,
        alarm=False,
        radio_battery_low=False,
        zone_closed=True,
        sensor_watch_alarm=False,
    )


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_supervise_alarm(zone: Zone, value: bool) -> None:
    result = zone.set_supervise_alarm(value)

    assert result is not zone
    assert result.supervise_alarm is value
    assert zone.supervise_alarm is False


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_trouble_alarm(zone: Zone, value: bool) -> None:
    result = zone.set_trouble_alarm(value)

    assert result is not zone
    assert result.trouble_alarm is value
    assert zone.trouble_alarm is False


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_bypassed(zone: Zone, value: bool) -> None:
    result = zone.set_bypassed(value)

    assert result is not zone
    assert result.bypassed is value


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_alarm(zone: Zone, value: bool) -> None:
    result = zone.set_alarm(value)

    assert result is not zone
    assert result.alarm is value


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_radio_battery_low(zone: Zone, value: bool) -> None:
    result = zone.set_radio_battery_low(value)

    assert result is not zone
    assert result.radio_battery_low is value


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_closed(zone: Zone, value: bool) -> None:
    result = zone.set_closed(value)

    assert result is not zone
    assert result.zone_closed is value


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_zone_set_sensor_watch_alarm(zone: Zone, value: bool) -> None:
    result = zone.set_sensor_watch_alarm(value)

    assert result is not zone
    assert result.sensor_watch_alarm is value


@pytest.fixture
def expander() -> Expander:
    return Expander(
        expander_id=1,
        tamper_alarm_triggered=False,
        mains_fault=False,
        battery_fault=False,
        fuse_fault=False,
    )


@pytest.mark.parametrize("value", [True, False])
def test_expander_set_tamper_alarm_triggered(
    expander: Expander,
    value: bool,
) -> None:
    result = expander.set_tamper_alarm_triggered(value)

    assert result is not expander
    assert result.tamper_alarm_triggered is value


@pytest.mark.parametrize("value", [True, False])
def test_expander_set_mains_fault(
    expander: Expander,
    value: bool,
) -> None:
    result = expander.set_mains_fault(value)

    assert result is not expander
    assert result.mains_fault is value


@pytest.mark.parametrize("value", [True, False])
def test_expander_set_battery_fault(
    expander: Expander,
    value: bool,
) -> None:
    result = expander.set_battery_fault(value)

    assert result is not expander
    assert result.battery_fault is value


@pytest.mark.parametrize("value", [True, False])
def test_expander_set_fuse_fault(
    expander: Expander,
    value: bool,
) -> None:
    result = expander.set_fuse_fault(value)

    assert result is not expander
    assert result.fuse_fault is value


@pytest.fixture
def output() -> Output:
    return Output(
        output_number=1,
        on=False,
    )


@pytest.mark.parametrize("value", [True, False])
def test_output_set_on(
    output: Output,
    value: bool,
) -> None:
    result = output.set_on(value)

    assert result is not output
    assert result.on is value
    assert result.output_number == output.output_number


@pytest.mark.parametrize(
    ("method_name", "value"),
    [
        ("set_ready_to_arm", False),
        ("set_battery_fault", True),
        ("set_mains_fault", True),
        ("set_tamper_alarm_triggered", True),
        ("set_line_fault", True),
        ("set_dialer_fault", True),
        ("set_dialer_line_fault", True),
        ("set_fuse_fault", True),
        ("set_monitoring_station_active", True),
        ("set_dialer_active", True),
        ("set_code_tamper", True),
        ("set_receiver_fault", True),
        ("set_pendant_battery_fault", True),
        ("set_rf_battery_low", True),
        ("set_sensor_watch_alarm", True),
    ],
)
def test_panel_state_scalar_setters(
    panel_state: PanelState,
    method_name: str,
    value: bool,
) -> None:
    method = getattr(panel_state, method_name)

    result = method(value)

    assert result is not panel_state
    assert getattr(result, method_name.removeprefix("set_")) == value


def test_panel_state_receiver_fault_accepts_none(
    panel_state: PanelState,
) -> None:
    result = panel_state.set_receiver_fault(None)

    assert result.receiver_fault is None
    assert result is not panel_state


def test_panel_state_pendant_battery_fault_accepts_none(
    panel_state: PanelState,
) -> None:
    result = panel_state.set_pendant_battery_fault(None)

    assert result.pendant_battery_fault is None
    assert result is not panel_state


def test_panel_state_rf_battery_low_accepts_none(
    panel_state: PanelState,
) -> None:
    result = panel_state.set_rf_battery_low(None)

    assert result.rf_battery_low is None
    assert result is not panel_state


def test_panel_state_sensor_watch_alarm_accepts_none(
    panel_state: PanelState,
) -> None:
    result = panel_state.set_sensor_watch_alarm(None)

    assert result.sensor_watch_alarm is None
    assert result is not panel_state


@pytest.mark.parametrize(
    ("area_number", "state"),
    [
        (1, AlarmState.ARMED_AWAY),
        (1, AlarmState.ARMED_STAY),
        (1, AlarmState.DISARMED),
        (1, AlarmState.ALARM_TRIGGERED),
        (1, AlarmState.ARMING_AWAY),
        (1, AlarmState.ARMING_STAY),
    ],
)
def test_panel_state_set_area_state(
    panel_state: PanelState,
    area_number: int,
    state: AlarmState,
) -> None:
    result = panel_state.set_area_state(area_number, state)

    assert result is not panel_state
    assert result.areas[area_number].state is state
    assert panel_state.areas[area_number].state is AlarmState.DISARMED


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_panel_state_set_area_ready(
    panel_state: PanelState,
    value: bool,
) -> None:
    result = panel_state.set_area_ready(1, value)

    assert result is not panel_state
    assert result.areas[1].ready_to_arm is value
    assert panel_state.areas[1].ready_to_arm is True


@pytest.mark.parametrize(
    (
        "method_name",
        "field_name",
        "value",
    ),
    [
        ("set_zone_alarm", "alarm", True),
        ("set_zone_radio_battery_low", "radio_battery_low", True),
        ("set_zone_bypassed", "bypassed", True),
        ("set_zone_closed", "zone_closed", False),
        ("set_zone_sensor_watch_alarm", "sensor_watch_alarm", True),
        ("set_zone_trouble_alarm", "trouble_alarm", True),
        ("set_zone_supervise_alarm", "supervise_alarm", True),
    ],
)
def test_panel_state_zone_setters(
    panel_state: PanelState,
    method_name: str,
    field_name: str,
    value: bool,
) -> None:
    result = getattr(panel_state, method_name)(1, value)

    assert result is not panel_state
    assert getattr(result.zones[1], field_name) is value


@pytest.mark.parametrize(
    "value",
    [True, False],
)
def test_panel_state_set_output_on(
    panel_state: PanelState,
    value: bool,
) -> None:
    result = panel_state.set_output_on(1, value)

    assert result is not panel_state
    assert result.outputs[1].on is value
    assert panel_state.outputs[1].on is False


@pytest.mark.parametrize(
    (
        "method_name",
        "field_name",
    ),
    [
        ("set_zone_expander_battery_fault", "battery_fault"),
        ("set_zone_expander_mains_fault", "mains_fault"),
        ("set_zone_expander_fuse_fault", "fuse_fault"),
        (
            "set_zone_expander_tamper_alarm_triggered",
            "tamper_alarm_triggered",
        ),
    ],
)
@pytest.mark.parametrize("value", [True, False])
def test_panel_state_zone_expander_setters(
    panel_state: PanelState,
    method_name: str,
    field_name: str,
    value: bool,
) -> None:
    result = getattr(panel_state, method_name)(1, value)

    assert result is not panel_state
    assert getattr(result.zone_expanders[1], field_name) is value
    assert getattr(panel_state.zone_expanders[1], field_name) is False


@pytest.mark.parametrize(
    (
        "method_name",
        "field_name",
    ),
    [
        ("set_output_expander_battery_fault", "battery_fault"),
        ("set_output_expander_mains_fault", "mains_fault"),
        ("set_output_expander_fuse_fault", "fuse_fault"),
        (
            "set_output_expander_tamper_alarm_triggered",
            "tamper_alarm_triggered",
        ),
    ],
)
@pytest.mark.parametrize("value", [True, False])
def test_panel_state_output_expander_setters(
    panel_state: PanelState,
    method_name: str,
    field_name: str,
    value: bool,
) -> None:
    result = getattr(panel_state, method_name)(1, value)

    assert result is not panel_state
    assert getattr(result.output_expanders[1], field_name) is value


@pytest.mark.parametrize(
    (
        "method_name",
        "field_name",
    ),
    [
        ("set_prox_expander_battery_fault", "battery_fault"),
        ("set_prox_expander_mains_fault", "mains_fault"),
        ("set_prox_expander_fuse_fault", "fuse_fault"),
        (
            "set_prox_expander_tamper_alarm_triggered",
            "tamper_alarm_triggered",
        ),
    ],
)
@pytest.mark.parametrize("value", [True, False])
def test_panel_state_prox_expander_setters(
    panel_state: PanelState,
    method_name: str,
    field_name: str,
    value: bool,
) -> None:
    result = getattr(panel_state, method_name)(1, value)

    assert result is not panel_state
    assert getattr(result.prox_expanders[1], field_name) is value


@pytest.mark.parametrize(
    (
        "method_name",
        "collection_name",
    ),
    [
        ("set_area_state", "areas"),
        ("set_area_ready", "areas"),
        ("set_zone_alarm", "zones"),
        ("set_zone_radio_battery_low", "zones"),
        ("set_zone_bypassed", "zones"),
        ("set_zone_closed", "zones"),
        ("set_zone_sensor_watch_alarm", "zones"),
        ("set_zone_trouble_alarm", "zones"),
        ("set_zone_supervise_alarm", "zones"),
        ("set_output_on", "outputs"),
        ("set_zone_expander_battery_fault", "zone_expanders"),
        ("set_zone_expander_mains_fault", "zone_expanders"),
        ("set_zone_expander_fuse_fault", "zone_expanders"),
        (
            "set_zone_expander_tamper_alarm_triggered",
            "zone_expanders",
        ),
        ("set_output_expander_battery_fault", "output_expanders"),
        ("set_output_expander_mains_fault", "output_expanders"),
        ("set_output_expander_fuse_fault", "output_expanders"),
        (
            "set_output_expander_tamper_alarm_triggered",
            "output_expanders",
        ),
        ("set_prox_expander_battery_fault", "prox_expanders"),
        ("set_prox_expander_mains_fault", "prox_expanders"),
        ("set_prox_expander_fuse_fault", "prox_expanders"),
        (
            "set_prox_expander_tamper_alarm_triggered",
            "prox_expanders",
        ),
    ],
)
def test_panel_state_setters_ignore_unknown_identifiers(
    panel_state: PanelState,
    method_name: str,
    collection_name: str,
) -> None:
    original_collection = getattr(panel_state, collection_name)

    if method_name == "set_area_state":
        result = getattr(panel_state, method_name)(
            999,
            AlarmState.ARMED_AWAY,
        )
    elif method_name == "set_area_ready":
        result = getattr(panel_state, method_name)(999, True)
    elif method_name == "set_output_on":
        result = getattr(panel_state, method_name)(999, True)
    else:
        result = getattr(panel_state, method_name)(999, True)

    assert result is panel_state
    assert getattr(result, collection_name) is original_collection


def test_panel_state_set_area_state_preserves_other_areas() -> None:
    state = Area(
        area_number=2,
        state=AlarmState.DISARMED,
        ready_to_arm=True,
    )

    panel = PanelState(
        ready_to_arm=True,
        battery_fault=False,
        mains_fault=False,
        tamper_alarm_triggered=False,
        line_fault=False,
        dialer_fault=False,
        dialer_line_fault=False,
        fuse_fault=False,
        monitoring_station_active=False,
        dialer_active=False,
        code_tamper=False,
        receiver_fault=None,
        pendant_battery_fault=None,
        rf_battery_low=None,
        sensor_watch_alarm=None,
        zones={},
        outputs={},
        areas={
            1: Area(
                area_number=1,
                state=AlarmState.DISARMED,
                ready_to_arm=True,
            ),
            2: state,
        },
        zone_expanders={},
        output_expanders={},
        prox_expanders={},
    )

    result = panel.set_area_state(
        1,
        AlarmState.ARMED_AWAY,
    )

    assert result.areas[1].state is AlarmState.ARMED_AWAY
    assert result.areas[2] is state


def test_panel_state_set_zone_alarm_preserves_other_zones() -> None:
    zone2 = Zone(
        zone_number=2,
        supervise_alarm=False,
        trouble_alarm=False,
        bypassed=False,
        alarm=False,
        radio_battery_low=False,
        zone_closed=True,
        sensor_watch_alarm=False,
    )

    panel = replace(
        PanelState(
            ready_to_arm=True,
            battery_fault=False,
            mains_fault=False,
            tamper_alarm_triggered=False,
            line_fault=False,
            dialer_fault=False,
            dialer_line_fault=False,
            fuse_fault=False,
            monitoring_station_active=False,
            dialer_active=False,
            code_tamper=False,
            receiver_fault=None,
            pendant_battery_fault=None,
            rf_battery_low=None,
            sensor_watch_alarm=None,
            zones={
                1: Zone(
                    zone_number=1,
                    supervise_alarm=False,
                    trouble_alarm=False,
                    bypassed=False,
                    alarm=False,
                    radio_battery_low=False,
                    zone_closed=True,
                    sensor_watch_alarm=False,
                ),
                2: zone2,
            },
            outputs={},
            areas={},
            zone_expanders={},
            output_expanders={},
            prox_expanders={},
        )
    )

    result = panel.set_zone_alarm(1, True)

    assert result.zones[1].alarm is True
    assert result.zones[2] is zone2


@pytest.mark.parametrize(
    (
        "status",
        "expected_flags",
    ),
    [
        (
            StatusResponse(code="RO"),
            StatusFlags.CODE,
        ),
        (
            StatusResponse(code="A", number=1),
            StatusFlags.CODE | StatusFlags.NUMBER,
        ),
        (
            StatusResponse(
                code="A",
                number=1,
                user_number=2,
            ),
            StatusFlags.CODE
            | StatusFlags.NUMBER
            | StatusFlags.USER_NUMBER,
        ),
        (
            StatusResponse(
                code="EDA",
                number=1,
                timestamp=1.5,
            ),
            StatusFlags.CODE
            | StatusFlags.NUMBER
            | StatusFlags.TIMESTAMP,
        ),
        (
            StatusResponse(
                code="BF",
                expander_code="ZX",
                expander_number=1,
            ),
            StatusFlags.CODE
            | StatusFlags.EXPANDER_CODE
            | StatusFlags.EXPANDER_NUMBER,
        ),
    ],
)
def test_status_response_flags(
    status: StatusResponse,
    expected_flags: StatusFlags,
) -> None:
    assert status.flags == expected_flags


def test_status_response_only_code_when_optional_fields_are_none() -> None:
    status = StatusResponse(
        code="TEST",
        number=None,
        expander_code=None,
        expander_number=None,
        user_number=None,
        timestamp=None,
    )

    assert status.flags == StatusFlags.CODE


@pytest.mark.parametrize(
    (
        "number",
        "expander_code",
        "expander_number",
        "user_number",
        "timestamp",
        "expected",
    ),
    [
        (
            1,
            None,
            None,
            None,
            None,
            StatusFlags.CODE | StatusFlags.NUMBER,
        ),
        (
            None,
            "ZX",
            None,
            None,
            None,
            StatusFlags.CODE | StatusFlags.EXPANDER_CODE,
        ),
        (
            None,
            None,
            1,
            None,
            None,
            StatusFlags.CODE | StatusFlags.EXPANDER_NUMBER,
        ),
        (
            None,
            None,
            None,
            1,
            None,
            StatusFlags.CODE | StatusFlags.USER_NUMBER,
        ),
        (
            None,
            None,
            None,
            None,
            1.0,
            StatusFlags.CODE | StatusFlags.TIMESTAMP,
        ),
    ],
)
def test_status_response_flags_for_individual_optional_fields(
    number: int | None,
    expander_code: str | None,
    expander_number: int | None,
    user_number: int | None,
    timestamp: float | None,
    expected: StatusFlags,
) -> None:
    status = StatusResponse(
        code="TEST",
        number=number,
        expander_code=expander_code,
        expander_number=expander_number,
        user_number=user_number,
        timestamp=timestamp,
    )

    assert status.flags == expected


def test_status_response_flags_include_all_fields() -> None:
    status = StatusResponse(
        code="TEST",
        number=1,
        expander_code="ZX",
        expander_number=2,
        user_number=3,
        timestamp=4.5,
    )

    expected = (
        StatusFlags.CODE
        | StatusFlags.NUMBER
        | StatusFlags.EXPANDER_CODE
        | StatusFlags.EXPANDER_NUMBER
        | StatusFlags.USER_NUMBER
        | StatusFlags.TIMESTAMP
    )

    assert status.flags == expected


def test_panel_version() -> None:
    version = PanelVersion(
        model="ECi",
        firmware_version=VersionInfo(10, 3, 52),
        serial_number="WR5SPLS1",
    )

    assert version.model == "ECi"
    assert version.firmware_version == VersionInfo(10, 3, 52)
    assert version.serial_number == "WR5SPLS1"


@pytest.mark.parametrize(
    "state",
    list(AlarmState),
)
def test_alarm_state_values(state: AlarmState) -> None:
    assert isinstance(state.value, str)


@pytest.mark.parametrize(
    ("state", "value"),
    [
        (AlarmState.DISARMED, "disarmed"),
        (AlarmState.ARMED_AWAY, "armed_away"),
        (AlarmState.ARMED_STAY, "armed_stay"),
        (AlarmState.ARMING_AWAY, "arming_away"),
        (AlarmState.ARMING_STAY, "arming_stay"),
        (AlarmState.ALARM_TRIGGERED, "alarm_triggered"),
    ],
)
def test_alarm_state_values_are_correct(
    state: AlarmState,
    value: str,
) -> None:
    assert state.value == value


@pytest.mark.parametrize(
    ("mode", "value"),
    [
        (ArmingMode.AWAY, "away"),
        (ArmingMode.STAY, "stay"),
    ],
)
def test_arming_mode_values(
    mode: ArmingMode,
    value: str,
) -> None:
    assert mode.value == value