from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arrowhead_alarm.api.mode_3_client import Mode3Client
from arrowhead_alarm.protocol.models import ArmingMode, ProtocolMode
from arrowhead_alarm.util import LoginCredentials


@pytest.fixture
def credentials() -> LoginCredentials:
    return LoginCredentials(
        username="user",
        password="password",
    )


@pytest.fixture
def client(credentials: LoginCredentials) -> Mode3Client:
    return Mode3Client(
        host="127.0.0.1",
        port=12345,
        credentials=credentials,
    )


@pytest.fixture
def request_mock(client: Mode3Client) -> AsyncMock:
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
    assert Mode3Client.mode == ProtocolMode.MODE_3


def test_delimiter() -> None:
    assert Mode3Client.delimiter == "\n\r"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arm_mode",
    [
        ArmingMode.AWAY,
        ArmingMode.STAY,
    ],
)
async def test_arm_button_success(
    client: Mode3Client,
    request_mock: AsyncMock,
    arm_mode: ArmingMode,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.arm_button_command",
        return_value=command,
    ) as command_mock:
        result = await client.arm_button(arm_mode)

    assert result is None
    command_mock.assert_called_once_with(arm_mode)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_button_failure(
    client: Mode3Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("arming failed")
    request_mock.return_value = failed_result(error)
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.arm_button_command",
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="arming failed") as exc_info:
            await client.arm_button(ArmingMode.AWAY)

    assert exc_info.value is error
    command_mock.assert_called_once_with(ArmingMode.AWAY)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arm_mode", "user", "pin"),
    [
        (ArmingMode.AWAY, 1, 1111),
        (ArmingMode.AWAY, 99, 9999),
        (ArmingMode.STAY, 2, 1234),
    ],
)
async def test_arm_user_pin_success(
    client: Mode3Client,
    request_mock: AsyncMock,
    arm_mode: ArmingMode,
    user: int,
    pin: int,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.arm_user_command",
        return_value=command,
    ) as command_mock:
        result = await client.arm_user_pin(
            arm_mode,
            user,
            pin,
        )

    assert result is None
    command_mock.assert_called_once_with(
        user,
        pin,
        arm_mode,
    )
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_user_pin_failure(
    client: Mode3Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("invalid pin")
    request_mock.return_value = failed_result(error)
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.arm_user_command",
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="invalid pin") as exc_info:
            await client.arm_user_pin(
                ArmingMode.STAY,
                7,
                1234,
            )

    assert exc_info.value is error
    command_mock.assert_called_once_with(
        7,
        1234,
        ArmingMode.STAY,
    )
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user", "mode"),
    [
        (1, ArmingMode.AWAY),
        (2, ArmingMode.STAY),
        (99, ArmingMode.AWAY),
    ],
)
async def test_arm_as_user_success(
    client: Mode3Client,
    request_mock: AsyncMock,
    user: int,
    mode: ArmingMode,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.arm_no_pin_command",
        return_value=command,
    ) as command_mock:
        result = await client.arm_as_user(user, mode)

    assert result is None
    command_mock.assert_called_once_with(user, mode)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_as_user_failure(
    client: Mode3Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("arming failed")
    request_mock.return_value = failed_result(error)
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.arm_no_pin_command",
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="arming failed") as exc_info:
            await client.arm_as_user(
                3,
                ArmingMode.AWAY,
            )

    assert exc_info.value is error
    command_mock.assert_called_once_with(
        3,
        ArmingMode.AWAY,
    )
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user", "pin"),
    [
        (1, 1111),
        (2, 1234),
        (99, 9999),
    ],
)
async def test_disarm_success(
    client: Mode3Client,
    request_mock: AsyncMock,
    user: int,
    pin: int,
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.disarm_user_command",
        return_value=command,
    ) as command_mock:
        result = await client.disarm(user, pin)

    assert result is None
    command_mock.assert_called_once_with(user, pin)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_disarm_failure(
    client: Mode3Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("disarming failed")
    request_mock.return_value = failed_result(error)
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_3_client.disarm_user_command",
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="disarming failed") as exc_info:
            await client.disarm(5, 4321)

    assert exc_info.value is error
    command_mock.assert_called_once_with(5, 4321)
    request_mock.assert_awaited_once_with(command)
