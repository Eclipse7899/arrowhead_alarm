from typing import Any, TypeVar, Callable

import pytest

from arrowhead_alarm.protocol.commands import (
    arm_area_command_mode_2,
    arm_area_command_mode_4,
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
from arrowhead_alarm.protocol.models import ArmingMode, PanelVersion, ProtocolMode, VersionInfo
from arrowhead_alarm.protocol.types import Success, Waiting, Result, Failure, Command

T = TypeVar("T")

def assert_success(result: Result[T, Any], expected: T):
    """Assert a successful Result."""
    assert isinstance(result, Success)
    assert result.value == expected


def assert_error(result: Result[Any, Any]):
    """Assert a failed Result."""
    assert isinstance(result, Failure)

class TestVersionCommand:
    def test_payload(self):
        command = version_command()

        assert command.data == "VERSION"

    def test_esx_version(self):
        command = version_command()

        result = command.collector(
            'OK Version "ESX-1 F/W Ver. 10.2.426 (GKRA6PJW)"'
        )

        assert result.is_done

        assert_success(
            result.value,
            PanelVersion(
                model="ESX-1",
                firmware_version=VersionInfo(10, 2, 426),
                serial_number="GKRA6PJW",
            ),
        )

    def test_eci_version(self):
        command = version_command()

        result = command.collector(
            'OK Version "ECi F/W Ver. 10.2.426 (GKRA6PJW)"'
        )
        
        assert result.is_done

        assert_success(
            result.value,
            PanelVersion(
                model="ECi",
                firmware_version=VersionInfo(10, 2, 426),
                serial_number="GKRA6PJW",
            ),
        )

    def test_waits_for_non_command_response(self):
        command = version_command()

        result = command.collector("ZO4")

        assert isinstance(result, Waiting)

    def test_error_response(self):
        command = version_command()

        result = command.collector("ERR Invalid Command")

        
        assert result.is_done
        assert_error(result.value)

    @pytest.mark.parametrize(
        "response",
        [
            "OK",
            "OK Version",
            'OK Version "ESX-1"',
            'OK Version "ESX-1 F/W Ver. 10.2"',
        ],
    )
    def test_malformed_response(self, response):
        command = version_command()
        result = command.collector(response)

        assert result.is_done
        assert_error(result.value)


class TestModeCommand:
    @pytest.mark.parametrize(
        ("mode", "expected_payload"),
        [
            (ProtocolMode.MODE_1, "MODE 1"),
            (ProtocolMode.MODE_2, "MODE 2"),
            (ProtocolMode.MODE_3, "MODE 3"),
            (ProtocolMode.MODE_4, "MODE 4"),
        ],
    )
    def test_payload(self, mode, expected_payload):
        command = mode_command(mode)

        assert command.data == expected_payload

    @pytest.mark.parametrize(
        "mode",
        [
            ProtocolMode.MODE_1,
            ProtocolMode.MODE_2,
            ProtocolMode.MODE_3,
            ProtocolMode.MODE_4,
        ],
    )
    def test_success(self, mode):
        command = mode_command(mode)

        _ = command.collector(f"OK")
        result = command.collector(f"Mode {mode.value}")
        
        assert result.is_done

        assert_success(result.value, mode)

    def test_error_response(self):
        command = mode_command(ProtocolMode.MODE_1)

        result = command.collector("ERR Invalid Mode")

        assert result.is_done

        assert_error(result.value)


class TestArmButtonCommand:
    @pytest.mark.parametrize(
        ("mode", "expected_payload"),
        [
            (ArmingMode.AWAY, "ARMAWAY"),
            (ArmingMode.STAY, "ARMSTAY"),
        ],
    )
    def test_payload(self, mode, expected_payload):
        command = arm_button_command(mode)

        assert command.data == expected_payload

    @pytest.mark.parametrize(
        "response",
        [
            "OK ArmAway",
            "OK ArmAway",
        ],
    )
    def test_away_success(self, response):
        command = arm_button_command(ArmingMode.AWAY)

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, None)

    @pytest.mark.parametrize(
        "response",
        [
            "OK ArmStay",
            "OK ArmStay 1",
        ],
    )
    def test_stay_success(self, response):
        command = arm_button_command(ArmingMode.STAY)

        result = command.collector(response)

        assert result.is_done

        assert_success(result.value, None)

    def test_away_error(self):
        command = arm_button_command(ArmingMode.AWAY)

        result = command.collector("ERR Cannot Arm")

        assert result.is_done
        assert_error(result.value)

    def test_stay_error(self):
        command = arm_button_command(ArmingMode.STAY)

        result = command.collector("ERR Cannot Arm")

        assert result.is_done

        assert_error(result.value)


class TestArmUserCommand:
    @pytest.mark.parametrize(
        ("mode", "expected_payload", "response"),
        [
            (
                ArmingMode.AWAY,
                "ARMAWAY 1 123",
                "OK ArmAway 1",
            ),
            (
                ArmingMode.STAY,
                "ARMSTAY 1 123",
                "OK ArmStay 1",
            ),
        ],
    )
    def test_payload_and_success(self, mode, expected_payload, response):
        command = arm_user_command(
            user_id=1,
            pin=123,
            mode=mode,
        )

        assert command.data == expected_payload

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, int(1))

    @pytest.mark.parametrize(
        ("user_id", "pin"),
        [
            (1, 123),
            (5, 4567),
            (32, 999999),
        ],
    )
    def test_parameter_order(self, user_id, pin):
        command = arm_user_command(
            user_id=user_id,
            pin=pin,
            mode=ArmingMode.AWAY,
        )

        assert command.data == f"ARMAWAY {user_id} {pin}"

    def test_error_response(self):
        command = arm_user_command(
            user_id=1,
            pin=123,
            mode=ArmingMode.AWAY,
        )

        result = command.collector("ERR Invalid PIN")

        assert result.is_done
        assert_error(result.value)


class TestArmNoPinCommand:
    @pytest.mark.parametrize(
        ("mode", "expected_payload", "response"),
        [
            (
                ArmingMode.AWAY,
                "ARMAWAY 1",
                "OK ArmAway 1",
            ),
            (
                ArmingMode.STAY,
                "ARMSTAY 1",
                "OK ArmStay 1",
            ),
        ],
    )
    def test_payload_and_success(self, mode, expected_payload, response):
        command = arm_no_pin_command(
            user=1,
            mode=mode,
        )

        assert command.data == expected_payload

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, int(1))

    @pytest.mark.parametrize("user", [1, 2, 16, 32])
    def test_user_number(self, user):
        command = arm_no_pin_command(
            user=user,
            mode=ArmingMode.AWAY,
        )

        assert command.data == f"ARMAWAY {user}"

    def test_error_response(self):
        command = arm_no_pin_command(
            user=1,
            mode=ArmingMode.AWAY,
        )

        result = command.collector("ERR Invalid User")

        assert result.is_done
        assert_error(result.value)


class TestArmAreaCommandMode2:
    @pytest.mark.parametrize(
        ("mode", "expected_payload", "response"),
        [
            (
                ArmingMode.AWAY,
                "ARMAWAY 2",
                "OK ArmAway 2",
            ),
            (
                ArmingMode.STAY,
                "ARMSTAY 2",
                "OK ArmStay 2",
            ),
        ],
    )
    def test_payload_and_success(self, mode, expected_payload, response):
        command = arm_area_command_mode_2(
            area=2,
            mode=mode,
        )

        assert command.data == expected_payload

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, int(2))

    @pytest.mark.parametrize("area", [1, 2, 8, 16])
    def test_area_number(self, area):
        command = arm_area_command_mode_2(
            area=area,
            mode=ArmingMode.AWAY,
        )

        assert command.data == f"ARMAWAY {area}"

    def test_error_response(self):
        command = arm_area_command_mode_2(
            area=2,
            mode=ArmingMode.AWAY,
        )

        result = command.collector("ERR Area Not Ready")

        assert result.is_done
        assert_error(result.value)


class TestArmAreaCommandMode4:
    @pytest.mark.parametrize(
        ("mode", "expected_payload", "response"),
        [
            (
                ArmingMode.AWAY,
                "ARMAREA 2",
                "OK ArmArea 2",
            ),
            (
                ArmingMode.STAY,
                "STAYAREA 2",
                "OK StayArea 2",
            ),
        ],
    )
    def test_payload_and_success(self, mode, expected_payload, response):
        command = arm_area_command_mode_4(
            area=2,
            mode=mode,
        )

        assert command.data == expected_payload

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, int(2))

    @pytest.mark.parametrize("area", [1, 2, 8, 16])
    def test_area_number(self, area):
        command = arm_area_command_mode_4(
            area=area,
            mode=ArmingMode.STAY,
        )

        assert command.data == f"STAYAREA {area}"

    def test_error_response(self):
        command = arm_area_command_mode_4(
            area=2,
            mode=ArmingMode.AWAY,
        )

        result = command.collector("ERR Area Not Ready")

        assert result.is_done
        assert_error(result.value)


class TestDisarmUserCommand:
    @pytest.mark.parametrize(
        ("user", "pin"),
        [
            (1, 123),
            (2, 1234),
            (32, 999999),
        ],
    )
    def test_payload(self, user, pin):
        command = disarm_user_command(
            user=user,
            pin=pin,
        )

        assert command.data == f"DISARM {user} {pin}"

    def test_success(self):
        command = disarm_user_command(
            user=1,
            pin=123,
        )

        result = command.collector("OK Disarm 1")
        assert result.is_done
        assert_success(result.value, int(1))

    def test_error_response(self):
        command = disarm_user_command(
            user=1,
            pin=123,
        )

        result = command.collector("ERR Invalid PIN")

        assert result.is_done
        assert_error(result.value)


class TestDisarmAreaCommand:
    @pytest.mark.parametrize(
        ("area", "pin"),
        [
            (1, 123),
            (2, 1234),
            (16, 999999),
        ],
    )
    def test_payload(self, area, pin):
        command = disarm_area_command(
            area=area,
            pin=pin,
        )

        assert command.data == f"DISARM {area} {pin}"

    def test_success(self):
        command = disarm_area_command(
            area=2,
            pin=123,
        )

        result = command.collector("OK Disarm 2")
        assert result.is_done
        assert_success(result.value, int(2))

    def test_error_response(self):
        command = disarm_area_command(
            area=2,
            pin=123,
        )

        result = command.collector("ERR Invalid PIN")

        assert result.is_done
        assert_error(result.value)


class TestBypassZoneCommand:
    @pytest.mark.parametrize("zone", [1, 3, 10, 99, 128])
    def test_payload(self, zone):
        command = bypass_zone_command(zone)

        assert command.data == f"BYPASS {zone}"

    def test_success(self):
        command = bypass_zone_command(3)

        result = command.collector("OK Bypass 3")
        assert result.is_done
        assert_success(result.value, int(3))

    def test_error_response(self):
        command = bypass_zone_command(3)

        result = command.collector("ERR Invalid Zone")

        assert result.is_done
        assert_error(result.value)


class TestUnbypassZoneCommand:
    @pytest.mark.parametrize("zone", [1, 3, 10, 99, 128])
    def test_payload(self, zone):
        command = unbypass_zone_command(zone)

        assert command.data == f"UNBYPASS {zone}"

    def test_success(self):
        command = unbypass_zone_command(3)

        result = command.collector("OK UnBypass 3")
        assert result.is_done
        assert_success(result.value, int(3))

    def test_error_response(self):
        command = unbypass_zone_command(3)

        result = command.collector("ERR Invalid Zone")

        assert result.is_done
        assert_error(result.value)


class TestSetOutputCommand:
    @pytest.mark.parametrize(
        ("on", "expected_payload", "response"),
        [
            (
                True,
                "OUTPUTON 3",
                "OK OutputOn 3",
            ),
            (
                False,
                "OUTPUTOFF 3",
                "OK OutputOff 3",
            ),
        ],
    )
    def test_payload_and_success(self, on, expected_payload, response):
        command = set_output_command(
            output=3,
            on=on,
        )

        assert command.data == expected_payload

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, int(3))

    @pytest.mark.parametrize("output", [1, 2, 10, 32])
    def test_output_number(self, output):
        command = set_output_command(
            output=output,
            on=True,
        )

        assert command.data == f"OUTPUTON {output}"

    def test_error_response(self):
        command = set_output_command(
            output=3,
            on=True,
        )

        result = command.collector("ERR Invalid Output")

        assert result.is_done
        assert_error(result.value)


class TestOutputStateCommand:
    def test_payload(self):
        command = output_state_command(3)

        assert command.data == "OUTPUT 3"

    @pytest.mark.parametrize(
        ("response", "expected"),
        [
            ("OK Output 3 On", True),
            ("OK Output 3 Off", False),
        ],
    )
    def test_success(self, response, expected):
        command = output_state_command(3)

        result = command.collector(response)
        assert result.is_done
        assert_success(result.value, expected)

    @pytest.mark.parametrize("output", [1, 2, 10, 32])
    def test_output_number(self, output):
        command = output_state_command(output)

        assert command.data == f"OUTPUT {output}"

    def test_error_response(self):
        command = output_state_command(3)

        result = command.collector("ERR Invalid Output")

        assert result.is_done
        assert_error(result.value)

    def test_non_command_response_waits(self):
        command = output_state_command(3)

        result = command.collector("ZO4")

        assert isinstance(result, Waiting)


@pytest.mark.parametrize(
    ("name", "command_factory"),
    [
        ("version", version_command),
        ("mode_1", lambda: mode_command(ProtocolMode.MODE_1)),
        ("arm_button_away", lambda: arm_button_command(ArmingMode.AWAY)),
        ("arm_user_1_pin_123_away", lambda: arm_user_command(1, 123, ArmingMode.AWAY)),
        ("arm_user_1_no_pin_away", lambda: arm_no_pin_command(1, ArmingMode.AWAY)),
        ("arm_area_1_away_mode_2", lambda: arm_area_command_mode_2(1, ArmingMode.AWAY)),
        ("arm_area_1_away_mode_4", lambda: arm_area_command_mode_4(1, ArmingMode.AWAY)),
        ("disarm_user_1_pin_123", lambda: disarm_user_command(1, 123)),
        ("disarm_area_1_pin_123", lambda: disarm_area_command(1, 123)),
        ("bypass_zone_1", lambda: bypass_zone_command(1)),
        ("unbypass_zone_1", lambda: unbypass_zone_command(1)),
        ("output_1_on", lambda: set_output_command(1, True)),
        ("output_state_1", lambda: output_state_command(1)),
    ],
)
def test_commands_ignore_unrelated_status_messages(
    name: str,
    command_factory: Callable[[], Command],
):
    command = command_factory()

    result = command.collector("ZO4")

    assert isinstance(result, Waiting)


@pytest.mark.parametrize(
    ("name", "command_factory"),
    [
        ("version", version_command),
        ("mode_1", lambda: mode_command(ProtocolMode.MODE_1)),
        ("arm_button_away", lambda: arm_button_command(ArmingMode.AWAY)),
        ("arm_user_1_pin_123_away", lambda: arm_user_command(1, 123, ArmingMode.AWAY)),
        ("arm_user_1_no_pin_away", lambda: arm_no_pin_command(1, ArmingMode.AWAY)),
        ("arm_area_1_away_mode_2", lambda: arm_area_command_mode_2(1, ArmingMode.AWAY)),
        ("arm_area_1_away_mode_4", lambda: arm_area_command_mode_4(1, ArmingMode.AWAY)),
        ("disarm_user_1_pin_123", lambda: disarm_user_command(1, 123)),
        ("disarm_area_1_pin_123", lambda: disarm_area_command(1, 123)),
        ("bypass_zone_1", lambda: bypass_zone_command(1)),
        ("unbypass_zone_1", lambda: unbypass_zone_command(1)),
        ("output_1_on", lambda: set_output_command(1, True)),
        ("output_state_1", lambda: output_state_command(1)),
    ],
)
def test_commands_convert_error_response(
    name: str,
    command_factory: Callable[[], Command],
):
    command = command_factory()

    result = command.collector("ERR Some protocol error")

    assert result.is_done
    assert_error(result.value)