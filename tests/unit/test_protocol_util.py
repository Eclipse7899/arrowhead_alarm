"""Tests for the protocol utility functions."""

# ruff: noqa
from arrowhead_alarm.types import Failure, Success
from arrowhead_alarm.protocol.models import ErrorResponse, OkResponse
from arrowhead_alarm.protocol.util import (
    convert_to_command_error,
    convert_to_command_ok,
    convert_to_response,
    is_command_error,
    is_command_ok,
)


def test_is_command_ok():
    assert is_command_ok("OK VER 10.3.52") is True
    assert is_command_ok("ERR 1") is False
    assert is_command_ok("SOMETHING ELSE") is False
    assert is_command_ok("") is False


def test_is_command_error():
    assert is_command_error("ERR 1") is True
    assert is_command_error("OK VER 10.3.52") is False
    assert is_command_error("SOMETHING ELSE") is False
    assert is_command_error("") is False


def test_convert_to_command_ok_success():
    data = "OK VER 10.3.52"
    result = convert_to_command_ok(data)
    assert isinstance(result, Success)
    assert result.value == OkResponse(keyword="VER", data="10.3.52")


def test_convert_to_command_ok_failure_invalid_prefix():
    data = "ERR 1"
    result = convert_to_command_ok(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)
    assert "Waiting cmd OK response" in str(result.error)


def test_convert_to_command_ok_failure_invalid_format():
    # Only "OK" or "OK KEYWORD" (needs at least two spaces for split(" ", 2))
    data = "OK"
    result = convert_to_command_ok(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)

    data = "OK KEYWORD"
    result = convert_to_command_ok(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)


def test_convert_to_command_error_success():
    data = "ERR123"
    result = convert_to_command_error(data)
    assert isinstance(result, Success)
    assert result.value == ErrorResponse(error_code=123)


def test_convert_to_command_error_failure_invalid_prefix():
    data = "OK VER 1.0"
    result = convert_to_command_error(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)


def test_convert_to_command_error_failure_non_digit():
    data = "ERR ABC"
    result = convert_to_command_error(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)


def test_convert_to_command_from_ok():
    data = "OK VER 10.3.52"
    result = convert_to_response(data)
    assert isinstance(result, Success)
    assert isinstance(result.value, OkResponse)
    assert result.value.keyword == "VER"
    assert result.value.data == "10.3.52"


def test_convert_to_command_from_error():
    data = "ERR1"
    result = convert_to_response(data)
    assert isinstance(result, Success)
    assert isinstance(result.value, ErrorResponse)
    assert result.value.error_code == 1


def test_convert_to_command_from_error_invalid():
    data = "ERR 123"
    result = convert_to_response(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)


def test_convert_to_command_invalid():
    data = "INVALID RESPONSE"
    result = convert_to_response(data)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValueError)
