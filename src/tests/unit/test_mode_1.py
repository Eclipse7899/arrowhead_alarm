import asyncio
from asyncio import StreamReader, StreamWriter
from typing import Callable, Awaitable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arrowhead_alarm.api.mode_1_client import Mode1Client
from arrowhead_alarm.protocol.models import ArmingMode, ProtocolMode
from arrowhead_alarm.util import LoginCredentials


@pytest.fixture
def credentials() -> LoginCredentials:
    return LoginCredentials(
        username="user",
        password="password",
    )


@pytest.fixture
def client(credentials: LoginCredentials) -> Mode1Client:
    return Mode1Client(
        host="127.0.0.1",
        port=12345,
        credentials=credentials,
    )


@pytest.fixture
def request_mock(client: Mode1Client) -> AsyncMock:
    client._client = MagicMock()
    client._client.request = AsyncMock()
    return client._client.request


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
    assert Mode1Client.mode == ProtocolMode.MODE_1


def test_delimiter() -> None:
    assert Mode1Client.delimiter == "\n\r"


@pytest.mark.asyncio
async def test_arm_button_success(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    result = successful_result()
    request_mock.return_value = result

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_button_command",
        return_value=command,
    ) as command_mock:
        await client.arm_button(ArmingMode.AWAY)

    command_mock.assert_called_once_with(ArmingMode.AWAY)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_button_failure(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("arm failed")
    request_mock.return_value = failed_result(error)

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_button_command",
        return_value=command,
    ):
        with pytest.raises(RuntimeError, match="arm failed"):
            await client.arm_button(ArmingMode.AWAY)

    request_mock.assert_awaited_once_with(command)


@pytest.mark.parametrize(
    "arm_mode",
    [
        ArmingMode.AWAY,
        ArmingMode.STAY,
    ],
)
@pytest.mark.asyncio
async def test_arm_button_passes_arm_mode(
    client: Mode1Client,
    request_mock: AsyncMock,
    arm_mode: ArmingMode,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_button_command",
        return_value=command,
    ) as command_mock:
        await client.arm_button(arm_mode)

    command_mock.assert_called_once_with(arm_mode)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_user_pin_success(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_user_command",
        return_value=command,
    ) as command_mock:
        await client.arm_user_pin(
            ArmingMode.AWAY,
            user=7,
            pin=1234,
        )

    command_mock.assert_called_once_with(
        7,
        1234,
        ArmingMode.AWAY,
    )
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_user_pin_failure(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("invalid pin")
    request_mock.return_value = failed_result(error)

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_user_command",
        return_value=command,
    ):
        with pytest.raises(RuntimeError, match="invalid pin"):
            await client.arm_user_pin(
                ArmingMode.AWAY,
                user=7,
                pin=1234,
            )

    request_mock.assert_awaited_once_with(command)


@pytest.mark.parametrize(
    ("arm_mode", "user", "pin"),
    [
        (ArmingMode.AWAY, 1, 1111),
        (ArmingMode.AWAY, 99, 9999),
        (ArmingMode.STAY, 2, 1234),
    ],
)
@pytest.mark.asyncio
async def test_arm_user_pin_passes_arguments(
    client: Mode1Client,
    request_mock: AsyncMock,
    arm_mode: ArmingMode,
    user: int,
    pin: int,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_user_command",
        return_value=command,
    ) as command_mock:
        await client.arm_user_pin(
            arm_mode,
            user=user,
            pin=pin,
        )

    command_mock.assert_called_once_with(
        user,
        pin,
        arm_mode,
    )
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_as_user_success(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_no_pin_command",
        return_value=command,
    ) as command_mock:
        await client.arm_as_user(
            user=3,
            mode=ArmingMode.STAY,
        )

    command_mock.assert_called_once_with(
        3,
        ArmingMode.STAY,
    )
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_arm_as_user_failure(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("arming failed")
    request_mock.return_value = failed_result(error)

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_no_pin_command",
        return_value=command,
    ):
        with pytest.raises(RuntimeError, match="arming failed"):
            await client.arm_as_user(
                user=3,
                mode=ArmingMode.STAY,
            )

    request_mock.assert_awaited_once_with(command)


@pytest.mark.parametrize(
    ("user", "mode"),
    [
        (1, ArmingMode.AWAY),
        (2, ArmingMode.STAY),
        (99, ArmingMode.AWAY),
    ],
)
@pytest.mark.asyncio
async def test_arm_as_user_passes_arguments(
    client: Mode1Client,
    request_mock: AsyncMock,
    user: int,
    mode: ArmingMode,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_no_pin_command",
        return_value=command,
    ) as command_mock:
        await client.arm_as_user(
            user=user,
            mode=mode,
        )

    command_mock.assert_called_once_with(user, mode)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_disarm_success(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.disarm_user_command",
        return_value=command,
    ) as command_mock:
        await client.disarm(
            user=5,
            pin=4321,
        )

    command_mock.assert_called_once_with(5, 4321)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_disarm_failure(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    error = RuntimeError("disarm failed")
    request_mock.return_value = failed_result(error)

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.disarm_user_command",
        return_value=command,
    ):
        with pytest.raises(RuntimeError, match="disarm failed"):
            await client.disarm(
                user=5,
                pin=4321,
            )

    request_mock.assert_awaited_once_with(command)


@pytest.mark.parametrize(
    ("user", "pin"),
    [
        (1, 1111),
        (2, 2222),
        (99, 9999),
    ],
)
@pytest.mark.asyncio
async def test_disarm_passes_arguments(
    client: Mode1Client,
    request_mock: AsyncMock,
    user: int,
    pin: int,
) -> None:
    request_mock.return_value = successful_result()

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.disarm_user_command",
        return_value=command,
    ) as command_mock:
        await client.disarm(
            user=user,
            pin=pin,
        )

    command_mock.assert_called_once_with(user, pin)
    request_mock.assert_awaited_once_with(command)


@pytest.mark.asyncio
async def test_methods_raise_exact_error_instance(
    client: Mode1Client,
    request_mock: AsyncMock,
) -> None:
    error = ValueError("specific error")
    request_mock.return_value = failed_result(error)

    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.mode_1_client.arm_button_command",
        return_value=command,
    ):
        with pytest.raises(ValueError) as exc_info:
            await client.arm_button(ArmingMode.AWAY)

    assert exc_info.value is error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command_patch", "invoke", "command_args"),
    [
        (
            "arm_button_command",
            lambda client: client.arm_button(ArmingMode.AWAY),
            (ArmingMode.AWAY,),
        ),
        (
            "arm_user_command",
            lambda client: client.arm_user_pin(
                ArmingMode.STAY,
                1,
                1234,
            ),
            (1, 1234, ArmingMode.STAY),
        ),
        (
            "arm_no_pin_command",
            lambda client: client.arm_as_user(
                1,
                ArmingMode.AWAY,
            ),
            (1, ArmingMode.AWAY),
        ),
        (
            "disarm_user_command",
            lambda client: client.disarm(1, 1234),
            (1, 1234),
        ),
    ],
)
async def test_each_method_makes_exactly_one_request(
    client: Mode1Client,
    request_mock: AsyncMock,
    command_patch: str,
    invoke: Callable[[Mode1Client], Awaitable[None]],
    command_args: tuple[object, ...],
) -> None:
    request_mock.return_value = successful_result()
    command = MagicMock()

    with patch(
        f"arrowhead_alarm.api.mode_1_client.{command_patch}",
        return_value=command,
    ) as command_mock:
        await invoke(client)

    command_mock.assert_called_once_with(*command_args)
    request_mock.assert_awaited_once_with(command)


async def mock_panel(
    reader: StreamReader,
    writer: StreamWriter,
) -> None:
    writer.write(b"\r\nWelcome\r\n")
    await writer.drain()

    try:
        while True:
            raw_line = await reader.readline()

            if not raw_line:
                break

            line = raw_line.strip().upper()

            if line == b"VERSION":
                writer.write(
                    b'OK Version "ECi F/W Ver. 10.3.52 (WR5SPLS1)"\r\n'
                )
                await writer.drain()

            elif line.startswith(b"MODE"):
                parts = line.split()

                if len(parts) >= 2:
                    writer.write(
                        b"OK\r\nMode "
                        + parts[1]
                        + b"\r\n"
                    )
                    await writer.drain()

            elif line == b"ARM":
                writer.write(b"OK\r\n")
                await writer.drain()

            elif line.startswith(b"DISARM"):
                writer.write(b"OK\r\n")
                await writer.drain()

    finally:
        writer.close()
        await writer.wait_closed()


@pytest.fixture
async def panel_server():
    server = await asyncio.start_server(
        mock_panel,
        host="127.0.0.1",
        port=0,
    )

    yield server

    server.close()
    await server.wait_closed()