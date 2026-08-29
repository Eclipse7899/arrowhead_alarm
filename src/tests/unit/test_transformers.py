from unittest.mock import MagicMock

import pytest

from arrowhead_alarm.protocol.models import (
    AlarmState,
    ErrorResponse,
    OkResponse,
    PanelVersion,
    ProtocolMode,
    Response,
    VersionInfo,
)
from arrowhead_alarm.protocol.transformers import (
    boolean_response_transformer,
    cmd_result_transformer,
    create_version_transformer,
    get_cmd_keyword_transformer,
    get_line_join_transformer,
    int_response_transformer,
    mode_response_transformer,
    panel_operation_transformer, get_int_prefix_transformer,
)
from arrowhead_alarm.protocol.types import Failure, Result, Success
from arrowhead_alarm.protocol.exceptions import ProtocolErrorCode


@pytest.mark.parametrize(
    ("response", "keyword"),
    [
        (OkResponse(keyword="TEST", data="value"), "TEST"),
        (OkResponse(keyword="VERSION", data="value"), "version"),
        (OkResponse(keyword="Version", data="value"), "VERSION"),
        (OkResponse(keyword="STATUS", data="value"), "status"),
    ],
)
def test_get_cmd_keyword_transformer_accepts_matching_keyword(
    response: OkResponse,
    keyword: str,
) -> None:
    transformer = get_cmd_keyword_transformer(keyword)

    result = transformer(response)

    assert result == Success(response)


@pytest.mark.parametrize(
    ("response", "keyword"),
    [
        (OkResponse(keyword="TEST", data="value"), "OTHER"),
        (OkResponse(keyword="VERSION", data="value"), "STATUS"),
        (OkResponse(keyword="STATUS", data="value"), "VERSION"),
    ],
)
def test_get_cmd_keyword_transformer_rejects_mismatched_keyword(
    response: OkResponse,
    keyword: str,
) -> None:
    transformer = get_cmd_keyword_transformer(keyword)

    result = transformer(response)

    assert result == Failure(ProtocolErrorCode.INVALID_RESPONSE)


@pytest.mark.parametrize(
    "error_code",
    [
        ProtocolErrorCode.INVALID_RESPONSE,
        ProtocolErrorCode.COMMAND_NOT_UNDERSTOOD,
        ProtocolErrorCode.COMMAND_NOT_ALLOWED,
        ProtocolErrorCode.RX_BUFFER_OVERFLOW,
        ProtocolErrorCode.TX_BUFFER_OVERFLOW,
        ProtocolErrorCode.XMODEM_SESSION_FAILED,
    ],
)
def test_get_cmd_keyword_transformer_converts_error_response(
    error_code: ProtocolErrorCode,
) -> None:
    response = ErrorResponse(error_code=error_code.value)

    result = get_cmd_keyword_transformer("TEST")(response)

    assert result == Failure(error_code)


def test_get_cmd_keyword_transformer_returns_original_response() -> None:
    response = OkResponse(
        keyword="TEST",
        data="value",
    )

    result = get_cmd_keyword_transformer("TEST")(response)

    assert isinstance(result, Success)
    assert result.value is response


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            OkResponse(keyword="TEST", data="value"),
            Success("value"),
        ),
        (
            OkResponse(keyword="TEST", data=""),
            Success(""),
        ),
        (
            OkResponse(keyword="TEST", data="some data here"),
            Success("some data here"),
        ),
    ],
)
def test_cmd_result_transformer_success(
    response: Response,
    expected: Result[str, ProtocolErrorCode],
) -> None:
    assert cmd_result_transformer(response) == expected


@pytest.mark.parametrize(
    "error_code",
    [
        ProtocolErrorCode.INVALID_RESPONSE,
        ProtocolErrorCode.COMMAND_NOT_UNDERSTOOD,
        ProtocolErrorCode.COMMAND_NOT_ALLOWED,
        ProtocolErrorCode.RX_BUFFER_OVERFLOW,
        ProtocolErrorCode.TX_BUFFER_OVERFLOW,
        ProtocolErrorCode.XMODEM_SESSION_FAILED,
    ],
)
def test_cmd_result_transformer_error(
    error_code: ProtocolErrorCode,
) -> None:
    response = ErrorResponse(error_code=error_code.value)

    result = cmd_result_transformer(response)

    assert result == Failure(error_code)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            '"ECi F/W Ver. 10.3.52 (WR5SPLS1)"',
            PanelVersion(
                model="ECi",
                firmware_version=VersionInfo(10, 3, 52),
                serial_number="WR5SPLS1",
            ),
        ),
        (
            "ECi F/W Ver. 10.3.52 (WR5SPLS1)",
            PanelVersion(
                model="ECi",
                firmware_version=VersionInfo(10, 3, 52),
                serial_number="WR5SPLS1",
            ),
        ),
        (
            '  "ECi F/W Ver. 1.2.3 (ABC123)"  ',
            PanelVersion(
                model="ECi",
                firmware_version=VersionInfo(1, 2, 3),
                serial_number="ABC123",
            ),
        ),
    ],
)
def test_create_version_transformer_success(
    data: str,
    expected: PanelVersion,
) -> None:
    result = create_version_transformer(data)

    assert isinstance(result, Success)
    assert result.value == expected

@pytest.mark.parametrize(
    "data",
    [
        "",
        "invalid",
        '"invalid"',
        '"ECi F/W Ver. invalid (SERIAL)"',
        '"ECi F/W Ver. 1.2 (SERIAL)"',
        '"ECi F/W Ver. 1.2.3 SERIAL"',
    ],
)
def test_create_version_transformer_returns_invalid_response(
    data: str,
) -> None:
    result = create_version_transformer(data)

    assert isinstance(result, Failure)
    assert result.error == ProtocolErrorCode.INVALID_RESPONSE


@pytest.mark.parametrize(
    ("lines", "delimiter", "expected"),
    [
        ([], "\n", ""),
        (["one"], "\n", "one"),
        (["one", "two"], "\n", "one\ntwo"),
        (["one", "two", "three"], " ", "one two three"),
        (["a", "b", "c"], "", "abc"),
    ],
)
def test_get_line_join_transformer(
    lines: list[str],
    delimiter: str,
    expected: str,
) -> None:
    transformer = get_line_join_transformer(delimiter)

    assert transformer(lines) == expected


@pytest.mark.parametrize(
    ("mode_int", "expected"),
    [
        (ProtocolMode.MODE_1.value, ProtocolMode.MODE_1),
        (ProtocolMode.MODE_2.value, ProtocolMode.MODE_2),
        (ProtocolMode.MODE_3.value, ProtocolMode.MODE_3),
        (ProtocolMode.MODE_4.value, ProtocolMode.MODE_4),
    ],
)
def test_mode_response_transformer_success(
    mode_int: int,
    expected: ProtocolMode,
) -> None:
    assert mode_response_transformer(mode_int) == Success(expected)


@pytest.mark.parametrize(
    "mode_int",
    [
        -1,
        0,
        5,
        99,
    ],
)
def test_mode_response_transformer_invalid_mode(
    mode_int: int,
) -> None:
    assert mode_response_transformer(mode_int) == Failure(
        ProtocolErrorCode.INVALID_RESPONSE
    )


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("0", 0),
        ("1", 1),
        ("123", 123),
        ("-1", -1),
        ("+10", 10),
        (" 42 ", 42),
    ],
)
def test_int_response_transformer_success(
    data: str,
    expected: int,
) -> None:
    assert int_response_transformer(data) == Success(expected)


@pytest.mark.parametrize(
    "data",
    [
        "",
        "abc",
        "1.5",
        "1a",
        "one",
        "1 2",
    ],
)
def test_int_response_transformer_invalid_data(
    data: str,
) -> None:
    assert int_response_transformer(data) == Failure(
        ProtocolErrorCode.INVALID_RESPONSE
    )


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("ON", True),
        ("OFF", False),
        ("on", True),
        ("off", False),
        (" On ", True),
        ("\tOFF\t", False),
        ("oN", True),
        ("OfF", False),
    ],
)
def test_boolean_response_transformer_success(
    data: str,
    expected: bool,
) -> None:
    assert boolean_response_transformer(data) == Success(expected)


@pytest.mark.parametrize(
    "data",
    [
        "",
        "TRUE",
        "FALSE",
        "1",
        "0",
        "YES",
        "NO",
        "ONLINE",
        "OFFLINE",
        "ONOFF",
    ],
)
def test_boolean_response_transformer_invalid_data(
    data: str,
) -> None:
    assert boolean_response_transformer(data) == Failure(
        ProtocolErrorCode.INVALID_RESPONSE
    )


@pytest.mark.parametrize(
    ("data", "expected_state"),
    [
        (
            "RO",
            lambda state: state.set_ready_to_arm(True),
        ),
        (
            "NR",
            lambda state: state.set_ready_to_arm(False),
        ),
        (
            "A1",
            lambda state: state.set_area_state(
                1,
                AlarmState.ARMED_AWAY,
            ),
        ),
        (
            "D1",
            lambda state: state.set_area_state(
                1,
                AlarmState.DISARMED,
            ),
        ),
        (
            "S1",
            lambda state: state.set_area_state(
                1,
                AlarmState.ARMED_STAY,
            ),
        ),
        (
            "ZC1",
            lambda state: state.set_zone_closed(1, True),
        ),
        (
            "ZO1",
            lambda state: state.set_zone_closed(1, False),
        ),
        (
            "OO1",
            lambda state: state.set_output_on(1, True),
        ),
        (
            "OR1",
            lambda state: state.set_output_on(1, False),
        ),
    ],
)
def test_panel_operation_transformer_success(
    data: str,
    expected_state,
) -> None:
    result = panel_operation_transformer(data)

    assert isinstance(result, Success)

    state = MagicMock()
    operation = result.value

    operation(state)

    expected_state(state)


@pytest.mark.parametrize(
    "data",
    [
        "",
        "INVALID",
        "not valid",
        "A",
        "ZC",
        "A1-INVALID",
    ],
)
def test_panel_operation_transformer_invalid_response(
    data: str,
) -> None:
    result = panel_operation_transformer(data)

    assert isinstance(result, Failure)
    assert result.error == ProtocolErrorCode.INVALID_RESPONSE


@pytest.mark.parametrize(
    ("expected_int", "expected_str", "data"),
    [
        (1, "value", "1 value"),
        (10, "hello", "10 hello"),
        (123, "some response", "123 some response"),
        (0, "value", "0 value"),
        (-1, "value", "-1 value"),
        (42, "value with spaces", "42 value with spaces"),
        (7, "", "7 "),
    ],
)
def test_get_int_prefix_transformer_success(
    expected_int: int,
    expected_str: str,
    data: str
) -> None:
    transformer = get_int_prefix_transformer(expected_int)

    result = transformer(data)

    assert isinstance(result, Success)
    assert result.value == expected_str

@pytest.mark.parametrize(
    ("expected_int", "data"),
    [
        (1, "2 value"),
        (10, "9 value"),
        (1, "value"),
        (1, ""),
        (1, "1"),
        (1, "1value"),
        (1, "1value more"),
        (1, "abc value"),
        (1, "1\tvalue"),
    ],
)
def test_get_int_prefix_transformer_failure(
    expected_int: int,
    data: str,
) -> None:
    transformer = get_int_prefix_transformer(expected_int)

    result = transformer(data)

    assert isinstance(result, Failure)
    assert result.error == ProtocolErrorCode.INVALID_RESPONSE