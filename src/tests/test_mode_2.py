from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arrowhead_alarm.api.mode_2_client import Mode2Client
from arrowhead_alarm.protocol.models import ArmingMode, ProtocolMode
from arrowhead_alarm.util import LoginCredentials


@pytest.fixture
def credentials() -> LoginCredentials:
    return LoginCredentials(
        username="user",
        password="password",
    )


@pytest.fixture
def client(credentials: LoginCredentials) -> Mode2Client:
    return Mode2Client(
        host="127.0.0.1",
        port=12345,
        credentials=credentials,
    )


@pytest.fixture
def request_mock(client: Mode2Client) -> AsyncMock:
    client._send_command = AsyncMock()
    return client._send_command


def successful_result() -> MagicMock:
    result = MagicMock()
    result.is_ok = True
    result.error = None
    return result


def failed_result(error: Exception) -> MagicMock:
    result = MagicMock()
    result.is_ok = False
    result.error = error
    return result


def test_mode() -> None:
    assert Mode2Client.mode == ProtocolMode.MODE_2


def test_delimiter() -> None:
    assert Mode2Client.delimiter == "\n\r"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("area", "mode"),
    [
        (1, ArmingMode.AWAY),
        (1, ArmingMode.STAY),
        (2, ArmingMode.AWAY),
        (99, ArmingMode.STAY),
    ],
)
async def test_arm_area_success(
    client: Mode2Client,
    request_mock: AsyncMock,
    area: int,
    mode: ArmingMode,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.arm_area_command_mode_2",
        return_value=command,
    ) as command_mock:
        await client.arm_area(area, mode)

    command_mock.assert_called_once_with(area, mode)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_area_failure(
    client: Mode2Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("arming failed")
    request_mock.return_value = failed_result(error)
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.arm_area_command_mode_2",
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="arming failed") as exc_info:
            await client.arm_area(3, ArmingMode.AWAY)

    command_mock.assert_called_once_with(3, ArmingMode.AWAY)
    request_mock.assert_awaited_once_with(command)
    assert exc_info.value is error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("area", "pin"),
    [
        (1, 1111),
        (1, 1234),
        (2, 9999),
        (99, 4321),
    ],
)
async def test_disarm_success(
    client: Mode2Client,
    request_mock: AsyncMock,
    area: int,
    pin: int,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.disarm_area_command",
        return_value=command,
    ) as command_mock:
        await client.disarm(area, pin)

    command_mock.assert_called_once_with(area, pin)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_disarm_failure(
    client: Mode2Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("disarming failed")
    request_mock.return_value = failed_result(error)
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.disarm_area_command",
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="disarming failed") as exc_info:
            await client.disarm(4, 1234)

    command_mock.assert_called_once_with(4, 1234)
    request_mock.assert_awaited_once_with(command)
    assert exc_info.value is error


@pytest.mark.asyncio
async def test_arm_area_does_not_raise_on_success(
    client: Mode2Client,
    request_mock: AsyncMock,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.arm_area_command_mode_2",
        return_value=command,
    ):
        result = await client.arm_area(1, ArmingMode.AWAY)

    assert result is None


@pytest.mark.asyncio
async def test_disarm_does_not_raise_on_success(
    client: Mode2Client,
    request_mock: AsyncMock,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.disarm_area_command",
        return_value=command,
    ):
        result = await client.disarm(1, 1234)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("area", "mode"),
    [
        (1, ArmingMode.AWAY),
        (5, ArmingMode.STAY),
        (99, ArmingMode.AWAY),
    ],
)
async def test_arm_area_uses_exact_command(
    client: Mode2Client,
    request_mock: AsyncMock,
    area: int,
    mode: ArmingMode,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.arm_area_command_mode_2",
        return_value=command,
    ) as command_mock:
        await client.arm_area(area, mode)

    assert command_mock.call_count == 1
    assert request_mock.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("area", "pin"),
    [
        (1, 1111),
        (5, 5678),
        (99, 9999),
    ],
)
async def test_disarm_uses_exact_command(
    client: Mode2Client,
    request_mock: AsyncMock,
    area: int,
    pin: int,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_2_client.disarm_area_command",
        return_value=command,
    ) as command_mock:
        await client.disarm(area, pin)

    assert command_mock.call_count == 1
    assert request_mock.await_count == 1
