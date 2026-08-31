import asyncio
from typing import Type
from unittest.mock import MagicMock

import pytest

from arrowhead_alarm.protocol.const import COMMAND_OK_PREFIX, COMMAND_ERROR_PREFIX
from arrowhead_alarm.protocol.exceptions import CommandNotUnderstoodError, InvalidParameterError, \
    CommandNotAllowedError, RxBufferOverflowError, TxBufferOverflowError, XModemSessionFailedError, \
    CommandError, ProtocolErrorCode
from arrowhead_alarm.protocol.models import Response, StatusResponse, OkResponse, ErrorResponse, \
    VersionInfo, PanelInfo
from arrowhead_alarm.protocol.types import Success, Failure, Result
from arrowhead_alarm.protocol.util import parse_panel_version_string, split_delimited, \
    is_command_error, is_command_ok, convert_to_response, \
    parse_status_response, convert_to_command_ok, convert_to_command_error, get_protocol_exception
from arrowhead_alarm.util import LoginCredentials, Publisher, ToggleEvent

@pytest.mark.parametrize(
    "data",
    [
        COMMAND_OK_PREFIX,
        f"{COMMAND_OK_PREFIX} anything",
        f"{COMMAND_OK_PREFIX} TEST value",
        f"{COMMAND_OK_PREFIX} TEST",
    ],
)
def test_is_command_ok_returns_true_for_ok_responses(data: str) -> None:
    assert is_command_ok(data) is True


@pytest.mark.parametrize(
    "data",
    [
        "",
        "O",
        f"{COMMAND_ERROR_PREFIX} 1",
        f"X {COMMAND_OK_PREFIX} TEST",
    ],
)
def test_is_command_ok_returns_false_for_non_ok_responses(data: str) -> None:
    assert is_command_ok(data) is False


@pytest.mark.parametrize(
    "data",
    [
        COMMAND_ERROR_PREFIX,
        f"{COMMAND_ERROR_PREFIX}1",
        f"{COMMAND_ERROR_PREFIX}123",
    ],
)
def test_is_command_error_returns_true_for_error_responses(data: str) -> None:
    assert is_command_error(data) is True


@pytest.mark.parametrize(
    "data",
    [
        "",
        "E",
        COMMAND_OK_PREFIX,
        f"X {COMMAND_ERROR_PREFIX}1",
    ],
)
def test_is_command_error_returns_false_for_non_error_responses(data: str) -> None:
    assert is_command_error(data) is False


@pytest.mark.parametrize(
    ("error_code", "exception_type"),
    [
        (1, CommandNotUnderstoodError),
        (2, InvalidParameterError),
        (3, CommandNotAllowedError),
        (4, RxBufferOverflowError),
        (5, TxBufferOverflowError),
        (6, XModemSessionFailedError),
    ],
)
def test_get_protocol_exception_returns_expected_exception(
    error_code: ProtocolErrorCode,
    exception_type: Type[CommandError],
) -> None:
    request = "REQUEST"
    response = f"{COMMAND_ERROR_PREFIX}{error_code}"

    exception = get_protocol_exception(
        error_code,
        request,
        response,
    )

    assert isinstance(exception, exception_type)


@pytest.mark.parametrize(
    "error_code",
    [-1, 0, 7, 8, 99],
)
def test_get_protocol_exception_returns_command_error_for_unknown_code(
    error_code: int,
) -> None:
    request = "REQUEST"
    response = f"{COMMAND_ERROR_PREFIX}{error_code}"

    exception = get_protocol_exception(
        ProtocolErrorCode(error_code),
        request,
        response,
    )

    assert type(exception) is CommandError
    assert str(error_code) in str(exception)


@pytest.mark.parametrize(
    "data",
    [
        f"{COMMAND_ERROR_PREFIX}1",
        f"{COMMAND_ERROR_PREFIX}01",
        f"{COMMAND_ERROR_PREFIX}123456",
    ],
)
def test_convert_to_command_error_returns_error_response(data: str) -> None:
    result = convert_to_command_error(data)

    assert isinstance(result, Success)
    assert result.value == ErrorResponse(
        error_code=int(data.lstrip(COMMAND_ERROR_PREFIX))
    )


@pytest.mark.parametrize(
    "data",
    [
        "",
        "NOT_ERROR",
        COMMAND_OK_PREFIX,
        f"{COMMAND_OK_PREFIX} TEST",
    ],
)
def test_convert_to_command_error_rejects_non_error_response(
    data: str,
) -> None:
    result = convert_to_command_error(data)

    assert isinstance(result, Failure)
    assert result.error.args == (f"Waiting cmd error response: {data}",)


@pytest.mark.parametrize(
    "data",
    [
        f"{COMMAND_ERROR_PREFIX}X",
        f"{COMMAND_ERROR_PREFIX}ABC",
        f"{COMMAND_ERROR_PREFIX}1X",
    ],
)
def test_convert_to_command_error_rejects_non_numeric_error_code(
    data: str,
) -> None:
    result = convert_to_command_error(data)

    assert isinstance(result, Failure)
    assert result.error.args == (
        f"Waiting cmd error code: {data.lstrip(COMMAND_ERROR_PREFIX)}",
    )


@pytest.mark.parametrize(
    ("data", "keyword", "response_data"),
    [
        (f"{COMMAND_OK_PREFIX} TEST value", "TEST", "value"),
        (f"{COMMAND_OK_PREFIX} TEST", "TEST", ""),
        (f"{COMMAND_OK_PREFIX} TEST one two three", "TEST", "one two three"),
    ],
)
def test_convert_to_command_ok_returns_ok_response(
    data: str,
    keyword: str,
    response_data: str,
) -> None:
    result = convert_to_command_ok(data)

    assert isinstance(result, Success)
    assert result.value == OkResponse(
        keyword=keyword,
        data=response_data,
    )


@pytest.mark.parametrize(
    "data",
    [
        "",
        "INVALID",
        COMMAND_ERROR_PREFIX,
        f"{COMMAND_ERROR_PREFIX}1",
    ],
)
def test_convert_to_command_ok_rejects_non_ok_response(data: str) -> None:
    result = convert_to_command_ok(data)

    assert isinstance(result, Failure)
    assert result.error.args == (f"Waiting cmd OK response: {data}",)


def test_convert_to_command_ok_rejects_incomplete_response() -> None:
    data = ""

    result = convert_to_command_ok(data)

    assert isinstance(result, Failure)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            "",
            Failure(ValueError("Empty response resp")),
        ),
        (
            f"{COMMAND_OK_PREFIX} TEST value",
            Success(
                OkResponse(
                    keyword="TEST",
                    data="value",
                )
            ),
        ),
        (
            f"{COMMAND_ERROR_PREFIX}1",
            Success(
                ErrorResponse(
                    error_code=1,
                )
            ),
        ),
    ],
)
def test_convert_to_response(data: str, expected: Result[Response, ValueError]) -> None:
    result = convert_to_response(data)

    if isinstance(expected, Success):
        assert isinstance(result, Success)
        assert result.value == expected.value
    else:
        assert isinstance(result, Failure)
        assert isinstance(result.error, ValueError)


@pytest.mark.parametrize(
    "data",
    [
        "",
        "RANDOM",
        "STATUS RESPONSE",
        "123",
    ],
)
def test_convert_to_response_rejects_unknown_response(data: str) -> None:
    result = convert_to_response(data)

    assert isinstance(result, Failure)
    assert result.error.args == (f"Waiting cmd response: {data}",)


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        (
                "AA-123 F/W Ver. 1.2.3 (ABC123)",
                PanelInfo(
                model="AA-123",
                firmware_version=VersionInfo(1, 2, 3),
                serial_number="ABC123",
            ),
        ),
        (
                "MODEL F/W Ver. 0.0.0 (SERIAL)",
                PanelInfo(
                model="MODEL",
                firmware_version=VersionInfo(0, 0, 0),
                serial_number="SERIAL",
            ),
        ),
        (
                "ABC-DEF F/W Ver. 10.20.30 (123456789)",
                PanelInfo(
                model="ABC-DEF",
                firmware_version=VersionInfo(10, 20, 30),
                serial_number="123456789",
            ),
        ),
        (
                "MODEL F/W Ver. 1.2.3 (SERIAL-NUMBER)",
                PanelInfo(
                model="MODEL",
                firmware_version=VersionInfo(1, 2, 3),
                serial_number="SERIAL-NUMBER",
            ),
        ),
    ],
)
def test_parse_panel_version_string_returns_panel_version(
    info: str,
    expected: PanelInfo,
) -> None:
    result = parse_panel_version_string(info)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    "version_string",
    [
        "",
        "MODEL",
        "MODEL F/W",
        "MODEL F/W Ver.",
        "MODEL F/W Ver. 1.2.3",
        "MODEL F/W Ver. 1.2 (SERIAL)",
        "MODEL F/W Ver. 1.2.3 SERIAL",
        "MODEL X/W Ver. 1.2.3 (SERIAL)",
        "MODEL F/W Ver. a.b.c (SERIAL)",
        "model with spaces F/W Ver. 1.2.3 (SERIAL)",
        "MODEL F/W Ver. 1.2.3 ()",
    ],
)
def test_parse_panel_version_string_rejects_invalid_versions(
    version_string: str,
) -> None:
    result = parse_panel_version_string(version_string)

    assert isinstance(result, Failure)
    assert result.error.args == (
        f"Waiting version string format: {version_string}",
    )


def test_parse_panel_version_string_strips_surrounding_whitespace() -> None:
    version = "  MODEL F/W Ver. 1.2.3 (SERIAL)  "

    result = parse_panel_version_string(version)

    assert isinstance(result, Success)
    assert result.value == PanelInfo(
        model="MODEL",
        firmware_version=VersionInfo(1, 2, 3),
        serial_number="SERIAL",
    )

def test_version_parsing():
    version_output = """ECi F/W Ver. 10.3.52 (WR5SPLS1)"""

    version_result = parse_panel_version_string(version_output)
    assert isinstance(version_result, Success)
    assert version_result.value.model == "ECi"
    assert version_result.value.firmware_version.major == 10
    assert version_result.value.firmware_version.minor == 3
    assert version_result.value.firmware_version.patch == 52


def test_version_parsing_with_unexpected_format():
    version_output = """Unexpected Format String"""

    result = parse_panel_version_string(version_output)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)


def test_version_comparison():
    v1 = parse_panel_version_string("ECi F/W Ver. 10.3.52 (WR5SPLS1)")
    v2 = parse_panel_version_string("ECi F/W Ver. 10.4.0 (WR5SPLS1)")
    v3 = parse_panel_version_string("ECi F/W Ver. 11.0.0 (WR5SPLS1)")

    assert isinstance(v1, Success)
    assert isinstance(v2, Success)
    assert isinstance(v3, Success)

    assert v1.value.firmware_version < v2.value.firmware_version
    assert v2.value.firmware_version < v3.value.firmware_version
    assert v3.value.firmware_version > v1.value.firmware_version
    assert v1.value.firmware_version <= v1.value.firmware_version
    assert v2.value.firmware_version >= v1.value.firmware_version


def test_version_equality():
    v1 = parse_panel_version_string("ECi F/W Ver. 10.3.52 (WR5SPLS1)")
    v2 = parse_panel_version_string("ECi F/W Ver. 10.3.52 (W4RXPY2A)")
    assert isinstance(v1, Success)
    assert isinstance(v2, Success)
    assert v1.value.firmware_version == v2.value.firmware_version


def test_version_inequality():
    v1 = parse_panel_version_string("ECi F/W Ver. 10.3.52 (WR5SPLS1)")
    v2 = parse_panel_version_string("ECi F/W Ver. 10.3.53 (WR5SPLS1)")
    assert isinstance(v1, Success)
    assert isinstance(v2, Success)
    assert v1.value.firmware_version != v2.value.firmware_version

def assert_success(
    result: Result[Response, ValueError],
) -> Response:
    assert isinstance(result, Success)
    return result.value

@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "RO",
            StatusResponse(code="RO"),
        ),
        (
            "NR",
            StatusResponse(code="NR"),
        ),
        (
            "BF",
            StatusResponse(code="BF"),
        ),
        (
            "BR",
            StatusResponse(code="BR"),
        ),
        (
            "CAL",
            StatusResponse(code="CAL"),
        ),
        (
            "CLF",
            StatusResponse(code="CLF"),
        ),
        (
            "DF",
            StatusResponse(code="DF"),
        ),
        (
            "DR",
            StatusResponse(code="DR"),
        ),
        (
            "LF",
            StatusResponse(code="LF"),
        ),
        (
            "LR",
            StatusResponse(code="LR"),
        ),
        (
            "MF",
            StatusResponse(code="MF"),
        ),
        (
            "MR",
            StatusResponse(code="MR"),
        ),
        (
            "TA",
            StatusResponse(code="TA"),
        ),
        (
            "TR",
            StatusResponse(code="TR"),
        ),
        (
            "FF",
            StatusResponse(code="FF"),
        ),
        (
            "FR",
            StatusResponse(code="FR"),
        ),
        (
            "RIF",
            StatusResponse(code="RIF"),
        ),
        (
            "RIR",
            StatusResponse(code="RIR"),
        ),
        (
            "PA",
            StatusResponse(code="PA"),
        ),
        (
            "PC",
            StatusResponse(code="PC"),
        ),
        (
            "FA",
            StatusResponse(code="FA"),
        ),
        (
            "FC",
            StatusResponse(code="FC"),
        ),
        (
            "MA",
            StatusResponse(code="MA"),
        ),
        (
            "MC",
            StatusResponse(code="MC"),
        ),
    ],
)
def test_parse_status_response_system_statuses(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("A1", StatusResponse(code="A", number=1)),
        ("A999", StatusResponse(code="A", number=999)),
        ("AA1", StatusResponse(code="AA", number=1)),
        ("AR1", StatusResponse(code="AR", number=1)),
        ("D1", StatusResponse(code="D", number=1)),
        ("S1", StatusResponse(code="S", number=1)),
        ("NR1", StatusResponse(code="NR", number=1)),
        ("RO1", StatusResponse(code="RO", number=1)),
        ("EA1", StatusResponse(code="EA", number=1)),
        ("ES1", StatusResponse(code="ES", number=1)),
    ],
)
def test_parse_status_response_area_statuses(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("ZEDS1-1.5", StatusResponse(code="ZEDS", number=1, timestamp=1.5)),
        ("ZEDS99-123.456", StatusResponse(code="ZEDS", number=99, timestamp=123.456)),
        ("EDA1-10.0", StatusResponse(code="EDA", number=1, timestamp=10.0)),
        ("EDS2-25.75", StatusResponse(code="EDS", number=2, timestamp=25.75)),
    ],
)
def test_parse_status_response_timestamped_statuses(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("A1-U2", StatusResponse(code="A", number=1, user_number=2)),
        ("D3-U4", StatusResponse(code="D", number=3, user_number=4)),
        ("S5-U6", StatusResponse(code="S", number=5, user_number=6)),
        ("A999-U123", StatusResponse(code="A", number=999, user_number=123)),
    ],
)
def test_parse_status_response_user_statuses(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("BF ZX1", StatusResponse(code="BF", expander_code="ZX", expander_number=1)),
        ("BF OX2", StatusResponse(code="BF", expander_code="OX", expander_number=2)),
        ("BF PX3", StatusResponse(code="BF", expander_code="PX", expander_number=3)),
        ("BR ZX4", StatusResponse(code="BR", expander_code="ZX", expander_number=4)),
        ("BR OX5", StatusResponse(code="BR", expander_code="OX", expander_number=5)),
        ("BR PX6", StatusResponse(code="BR", expander_code="PX", expander_number=6)),
        ("MF ZX7", StatusResponse(code="MF", expander_code="ZX", expander_number=7)),
        ("MF OX8", StatusResponse(code="MF", expander_code="OX", expander_number=8)),
        ("MF PX9", StatusResponse(code="MF", expander_code="PX", expander_number=9)),
        ("MR ZX10", StatusResponse(code="MR", expander_code="ZX", expander_number=10)),
        ("MR OX11", StatusResponse(code="MR", expander_code="OX", expander_number=11)),
        ("MR PX12", StatusResponse(code="MR", expander_code="PX", expander_number=12)),
        ("FF ZX13", StatusResponse(code="FF", expander_code="ZX", expander_number=13)),
        ("FF OX14", StatusResponse(code="FF", expander_code="OX", expander_number=14)),
        ("FF PX15", StatusResponse(code="FF", expander_code="PX", expander_number=15)),
        ("FR ZX16", StatusResponse(code="FR", expander_code="ZX", expander_number=16)),
        ("FR OX17", StatusResponse(code="FR", expander_code="OX", expander_number=17)),
        ("FR PX18", StatusResponse(code="FR", expander_code="PX", expander_number=18)),
        ("TA ZX19", StatusResponse(code="TA", expander_code="ZX", expander_number=19)),
        ("TA OX20", StatusResponse(code="TA", expander_code="OX", expander_number=20)),
        ("TA PX21", StatusResponse(code="TA", expander_code="PX", expander_number=21)),
        ("TR ZX22", StatusResponse(code="TR", expander_code="ZX", expander_number=22)),
        ("TR OX23", StatusResponse(code="TR", expander_code="OX", expander_number=23)),
        ("TR PX24", StatusResponse(code="TR", expander_code="PX", expander_number=24)),
    ],
)
def test_parse_status_response_expander_statuses(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("PBF1", StatusResponse(code="PBF", number=1)),
        ("PBR1", StatusResponse(code="PBR", number=1)),
        ("ZA1", StatusResponse(code="ZA", number=1)),
        ("ZBL1", StatusResponse(code="ZBL", number=1)),
        ("ZBR1", StatusResponse(code="ZBR", number=1)),
        ("ZBY1", StatusResponse(code="ZBY", number=1)),
        ("ZBYR1", StatusResponse(code="ZBYR", number=1)),
        ("ZC1", StatusResponse(code="ZC", number=1)),
        ("ZIA1", StatusResponse(code="ZIA", number=1)),
        ("ZIR1", StatusResponse(code="ZIR", number=1)),
        ("ZO1", StatusResponse(code="ZO", number=1)),
        ("ZR1", StatusResponse(code="ZR", number=1)),
        ("ZT1", StatusResponse(code="ZT", number=1)),
        ("ZTR1", StatusResponse(code="ZTR", number=1)),
        ("ZSA1", StatusResponse(code="ZSA", number=1)),
        ("ZSR1", StatusResponse(code="ZSR", number=1)),
        ("OO1", StatusResponse(code="OO", number=1)),
        ("OR1", StatusResponse(code="OR", number=1)),
    ],
)
def test_parse_status_response_numbered_statuses(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


@pytest.mark.parametrize(
    "message",
    [
        "",
        " ",
        "invalid",
        "ro",
        "RO-",
        "A-1",
        "A1-U",
        "A1-Ux",
        "A1-",
        "A1-1",
        "A1-1.2.3",
        "EDA1-",
        "EDA1-1",
        "EDA1-1.",
        "ZEDS1-",
        "BF ZX",
        "BF ZX",
        "BF XXX1",
        "BF ZX-1",
        "BF ZX1 extra",
        "A1-U2 extra",
    ],
)
def test_parse_status_response_rejects_invalid_messages(
    message: str,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Failure)
    assert result.error.args == (
        f"Waiting status_response command format: {message}",
    )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "A123",
            StatusResponse(code="A", number=123),
        ),
        (
            "A1-U999",
            StatusResponse(
                code="A",
                number=1,
                user_number=999,
            ),
        ),
        (
            "EDA12-999.999",
            StatusResponse(
                code="EDA",
                number=12,
                timestamp=999.999,
            ),
        ),
        (
            "BF ZX123",
            StatusResponse(
                code="BF",
                expander_code="ZX",
                expander_number=123,
            ),
        ),
    ],
)
def test_parse_status_response_preserves_numeric_values(
    message: str,
    expected: StatusResponse,
) -> None:
    result = parse_status_response(message)

    assert isinstance(result, Success)
    assert result.value == expected


def test_parse_status_response_flags_match_populated_fields() -> None:
    statuses = [
        StatusResponse(code="RO"),
        StatusResponse(code="A", number=1),
        StatusResponse(code="A", number=1, user_number=2),
        StatusResponse(code="EDA", number=1, timestamp=1.5),
        StatusResponse(
            code="BF",
            expander_code="ZX",
            expander_number=1,
        ),
    ]

    for status in statuses:
        assert status.flags is not None


@pytest.mark.parametrize(
    ("message", "delimiter", "expected"),
    [
        ("A,B,C,", ",", ["A", "B", "C"]),
        ("A|B|C|", "|", ["A", "B", "C"]),
        ("one;two;three;", ";", ["one", "two", "three"]),
        ("single,", ",", ["single"]),
        (",", ",", [""]),
        (",,", ",", ["", ""]),
        ("", ",", []),
    ],
)
def test_split_delimited(
    message: str,
    delimiter: str,
    expected: list[str],
) -> None:
    assert split_delimited(message, delimiter) == expected


def test_split_delimited_does_not_return_final_empty_element() -> None:
    assert split_delimited("A,B,C,", ",") == ["A", "B", "C"]


def test_split_delimited_requires_delimiter_to_be_present_for_trimming() -> None:
    assert split_delimited("ABC", ",") == []


def test_status_response_field_types() -> None:
    status = StatusResponse(
        code="BF",
        number=1,
        expander_code="ZX",
        expander_number=2,
        user_number=3,
        timestamp=4.5,
    )

    assert isinstance(status.code, str)
    assert isinstance(status.number, int)
    assert isinstance(status.expander_code, str)
    assert isinstance(status.expander_number, int)
    assert isinstance(status.user_number, int)
    assert isinstance(status.timestamp, float)


def test_convert_to_response_returns_response_subtype_for_ok() -> None:
    result = convert_to_response(
        f"{COMMAND_OK_PREFIX} TEST value"
    )

    response = assert_success(result)
    assert isinstance(response, OkResponse)


def test_convert_to_response_returns_response_subtype_for_error() -> None:
    result = convert_to_response(
        f"{COMMAND_ERROR_PREFIX}1"
    )

    response = assert_success(result)
    assert isinstance(response, ErrorResponse)


def test_parse_panel_version_string_returns_expected_version_info() -> None:
    result = parse_panel_version_string(
        "MODEL F/W Ver. 1.2.3 (SERIAL)"
    )

    assert isinstance(result, Success)
    assert result.value.firmware_version == VersionInfo(1, 2, 3)
    assert result.value.model == "MODEL"
    assert result.value.serial_number == "SERIAL"


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("user", "password"),
        ("admin", "1234"),
        ("a", "b"),
        ("user@example.com", "very-secure-password"),
    ],
)
def test_login_credentials_accepts_valid_credentials(
    username: str,
    password: str,
) -> None:
    credentials = LoginCredentials(
        username=username,
        password=password,
    )

    assert credentials.username == username
    assert credentials.password == password


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("", "password"),
        ("user", ""),
        ("", ""),
    ],
)
def test_login_credentials_rejects_empty_credentials(
    username: str,
    password: str,
) -> None:
    with pytest.raises(ValueError):
        LoginCredentials(
            username=username,
            password=password,
        )


def test_login_credentials_error_for_empty_username() -> None:
    with pytest.raises(
        ValueError,
        match="Username cannot be empty\\.",
    ):
        LoginCredentials(
            username="",
            password="password",
        )


def test_login_credentials_error_for_empty_password() -> None:
    with pytest.raises(
        ValueError,
        match="Password cannot be empty\\.",
    ):
        LoginCredentials(
            username="user",
            password="",
        )


def test_login_credentials_preserves_whitespace() -> None:
    credentials = LoginCredentials(
        username=" user ",
        password=" password ",
    )

    assert credentials.username == " user "
    assert credentials.password == " password "


@pytest.fixture
def toggle_event() -> ToggleEvent:
    return ToggleEvent()


def test_toggle_event_initial_state(
    toggle_event: ToggleEvent,
) -> None:
    assert toggle_event.is_set() is False
    assert toggle_event.is_clear() is True


def test_toggle_event_set(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.set()

    assert toggle_event.is_set() is True
    assert toggle_event.is_clear() is False


def test_toggle_event_clear(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.set()
    toggle_event.clear()

    assert toggle_event.is_set() is False
    assert toggle_event.is_clear() is True


def test_toggle_event_set_is_idempotent(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.set()
    toggle_event.set()

    assert toggle_event.is_set() is True
    assert toggle_event.is_clear() is False


def test_toggle_event_clear_is_idempotent(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.clear()
    toggle_event.clear()

    assert toggle_event.is_set() is False
    assert toggle_event.is_clear() is True


@pytest.mark.asyncio
async def test_toggle_event_wait_until_set_returns_immediately_when_set(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.set()

    await asyncio.wait_for(
        toggle_event.wait_until_set(),
        timeout=0.1,
    )

    assert toggle_event.is_set() is True


@pytest.mark.asyncio
async def test_toggle_event_wait_until_clear_returns_immediately_when_clear(
    toggle_event: ToggleEvent,
) -> None:
    await asyncio.wait_for(
        toggle_event.wait_until_clear(),
        timeout=0.1,
    )

    assert toggle_event.is_clear() is True


@pytest.mark.asyncio
async def test_toggle_event_wait_until_set_blocks_until_set(
    toggle_event: ToggleEvent,
) -> None:
    task = asyncio.create_task(
        toggle_event.wait_until_set(),
    )

    await asyncio.sleep(0)

    assert task.done() is False

    toggle_event.set()

    await asyncio.wait_for(task, timeout=0.1)

    assert task.done() is True


@pytest.mark.asyncio
async def test_toggle_event_wait_until_clear_blocks_until_clear(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.set()

    task = asyncio.create_task(
        toggle_event.wait_until_clear(),
    )

    await asyncio.sleep(0)

    assert task.done() is False

    toggle_event.clear()

    await asyncio.wait_for(task, timeout=0.1)

    assert task.done() is True


@pytest.mark.asyncio
async def test_toggle_event_wait_until_set_remains_blocked_when_clear(
    toggle_event: ToggleEvent,
) -> None:
    task = asyncio.create_task(
        toggle_event.wait_until_set(),
    )

    await asyncio.sleep(0)

    assert task.done() is False

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_toggle_event_wait_until_clear_remains_blocked_when_set(
    toggle_event: ToggleEvent,
) -> None:
    toggle_event.set()

    task = asyncio.create_task(
        toggle_event.wait_until_clear(),
    )

    await asyncio.sleep(0)

    assert task.done() is False

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_toggle_event_switches_between_states(
    toggle_event: ToggleEvent,
) -> None:
    assert toggle_event.is_clear() is True

    toggle_event.set()

    await asyncio.wait_for(
        toggle_event.wait_until_set(),
        timeout=0.1,
    )

    assert toggle_event.is_set() is True
    assert toggle_event.is_clear() is False

    toggle_event.clear()

    await asyncio.wait_for(
        toggle_event.wait_until_clear(),
        timeout=0.1,
    )

    assert toggle_event.is_set() is False
    assert toggle_event.is_clear() is True

@pytest.fixture
def publisher() -> Publisher[int]:
    return Publisher()


def test_subscribe_adds_subscriber(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.subscribe(callback)

    assert callback in publisher._subscribers


def test_subscribe_same_callback_only_once(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.subscribe(callback)
    publisher.subscribe(callback)

    assert len(publisher._subscribers) == 1


def test_unsubscribe_removes_subscriber(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.subscribe(callback)
    publisher.unsubscribe(callback)

    assert callback not in publisher._subscribers


def test_unsubscribe_missing_subscriber_is_safe(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.unsubscribe(callback)

    assert publisher._subscribers == dict()


def test_dispatch_calls_subscriber(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.subscribe(callback)
    publisher.dispatch(42)

    callback.assert_called_once_with(42)


def test_dispatch_calls_all_subscribers(
    publisher: Publisher[int],
) -> None:
    first = MagicMock()
    second = MagicMock()
    third = MagicMock()

    publisher.subscribe(first)
    publisher.subscribe(second)
    publisher.subscribe(third)

    publisher.dispatch(42)

    first.assert_called_once_with(42)
    second.assert_called_once_with(42)
    third.assert_called_once_with(42)


def test_dispatch_does_nothing_without_subscribers(
    publisher: Publisher[int],
) -> None:
    publisher.dispatch(42)


def test_unsubscribe_prevents_future_dispatch(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.subscribe(callback)
    publisher.unsubscribe(callback)
    publisher.dispatch(42)

    callback.assert_not_called()


def test_unsubscribe_during_dispatch_prevents_later_callback(
    publisher: Publisher[int],
) -> None:
    first = MagicMock()
    second = MagicMock()

    def first_callback(value: int) -> None:
        first(value)
        publisher.unsubscribe(second)

    publisher.subscribe(first_callback)
    publisher.subscribe(second)

    publisher.dispatch(42)

    first.assert_called_once_with(42)
    second.assert_not_called()


def test_unsubscribe_during_dispatch_does_not_affect_current_callback(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    def callback_wrapper(value: int) -> None:
        publisher.unsubscribe(callback)
        callback(value)

    publisher.subscribe(callback_wrapper)

    publisher.dispatch(42)

    callback.assert_called_once_with(42)


def test_unsubscribe_during_dispatch_only_affects_subsequent_dispatches(
    publisher: Publisher[int],
) -> None:
    first = MagicMock()
    second = MagicMock()

    def first_callback(value: int) -> None:
        first(value)
        publisher.unsubscribe(second)

    publisher.subscribe(first_callback)
    publisher.subscribe(second)

    publisher.dispatch(1)
    publisher.dispatch(2)

    first.assert_has_calls(
        [
            ((1,),),
            ((2,),),
        ] # ty: ignore[invalid-argument-type]
    )
    second.assert_not_called()


def test_subscribe_during_dispatch_does_not_receive_current_event(
    publisher: Publisher[int],
) -> None:
    first = MagicMock()
    second = MagicMock()

    def first_callback(value: int) -> None:
        first(value)
        publisher.subscribe(second)

    publisher.subscribe(first_callback)

    publisher.dispatch(42)

    first.assert_called_once_with(42)
    second.assert_not_called()


def test_subscribe_during_dispatch_receives_next_event(
    publisher: Publisher[int],
) -> None:
    first = MagicMock()
    second = MagicMock()

    def first_callback(value: int) -> None:
        first(value)
        publisher.subscribe(second)

    publisher.subscribe(first_callback)

    publisher.dispatch(1)
    publisher.dispatch(2)

    first.assert_has_calls(
        [
            ((1,),),
            ((2,),),
        ]  # ty: ignore[invalid-argument-type]
    )
    second.assert_called_once_with(2)


def test_subscribe_and_unsubscribe_during_dispatch(
    publisher: Publisher[int],
) -> None:
    first = MagicMock()
    second = MagicMock()
    third = MagicMock()

    def first_callback(value: int) -> None:
        first(value)
        publisher.unsubscribe(second)
        publisher.subscribe(third)

    publisher.subscribe(first_callback)
    publisher.subscribe(second)

    publisher.dispatch(1)
    publisher.dispatch(2)

    first.assert_has_calls(
        [
            ((1,),),
            ((2,),),
        ] # ty: ignore[invalid-argument-type]
    )
    second.assert_not_called()
    third.assert_called_once_with(2)


def test_callback_can_unsubscribe_itself(
    publisher: Publisher[int],
) -> None:
    calls: list[int] = []

    def callback(value: int) -> None:
        calls.append(value)
        publisher.unsubscribe(callback)

    publisher.subscribe(callback)

    publisher.dispatch(1)
    publisher.dispatch(2)

    assert calls == [1]


def test_callback_can_subscribe_another_callback(
    publisher: Publisher[int],
) -> None:
    calls: list[tuple[str, int]] = []

    def first(value: int) -> None:
        calls.append(("first", value))
        publisher.subscribe(second)

    def second(value: int) -> None:
        calls.append(("second", value))

    publisher.subscribe(first)

    publisher.dispatch(1)
    publisher.dispatch(2)

    assert calls == [
        ("first", 1),
        ("first", 2),
        ("second", 2),
    ]


def test_dispatch_passes_exact_value(
    publisher: Publisher[object],
) -> None:
    callback = MagicMock()
    value = object()

    publisher.subscribe(callback)
    publisher.dispatch(value)

    callback.assert_called_once_with(value)


def test_dispatch_supports_multiple_values(
    publisher: Publisher[int],
) -> None:
    callback = MagicMock()

    publisher.subscribe(callback)

    publisher.dispatch(1)
    publisher.dispatch(2)
    publisher.dispatch(3)

    assert callback.call_args_list == [
        ((1,),),
        ((2,),),
        ((3,),),
    ]


def test_subscriber_exception_propagates(
    publisher: Publisher[int],
) -> None:
    error = RuntimeError("subscriber failed")
    callback = MagicMock(side_effect=error)

    publisher.subscribe(callback)

    with pytest.raises(RuntimeError, match="subscriber failed"):
        publisher.dispatch(42)
