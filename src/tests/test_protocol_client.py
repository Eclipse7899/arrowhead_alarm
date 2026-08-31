from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from arrowhead_alarm.api.protocol_client import ProtocolClient
from arrowhead_alarm.protocol.defaults import DEFAULT_MAX_OUTPUTS, DEFAULT_MAX_ZONES
from arrowhead_alarm.protocol.models import PanelState, ProtocolMode, PanelInfo, VersionInfo
from arrowhead_alarm.protocol.types import Success, Failure
from arrowhead_alarm.util import LoginCredentials


class TestProtocolClient(ProtocolClient):
    __test__ = False

    mode = ProtocolMode.MODE_1
    delimiter = "\n\r"


@pytest.fixture
def credentials() -> LoginCredentials:
    return LoginCredentials(
        username="user",
        password="password",
    )


@pytest.fixture
def client(credentials: LoginCredentials) -> TestProtocolClient:
    with patch(
        "arrowhead_alarm.api.protocol_client.AuthenticatedSession",
    ), patch(
        "arrowhead_alarm.api.protocol_client.TcpTransport",
    ), patch(
        "arrowhead_alarm.api.protocol_client.CommandClient",
    ):
        return TestProtocolClient(
            host="127.0.0.1",
            port=12345,
            credentials=credentials,
            command_timeout=3.0,
            connection_timeout=5.0
        )


@pytest.fixture
def command_client(client: TestProtocolClient) -> MagicMock:
    client._client = MagicMock()
    client._client.request = AsyncMock()
    client._client.connect = AsyncMock()
    client._client.disconnect = AsyncMock()
    client._client.subscribe = MagicMock()
    client._client.unsubscribe = MagicMock()
    return client._client


def successful_result(value=None) -> MagicMock:
    result = MagicMock()
    result.is_ok = True
    result.value = value
    result.error = None
    return result


def failed_result(error: Exception) -> MagicMock:
    result = MagicMock()
    result.is_ok = False
    result.value = None
    result.error = error
    return result


def test_initial_state_is_default_state(
    credentials: LoginCredentials,
) -> None:
    with patch(
        "arrowhead_alarm.api.protocol_client.AuthenticatedSession",
    ), patch(
        "arrowhead_alarm.api.protocol_client.TcpTransport",
    ), patch(
        "arrowhead_alarm.api.protocol_client.CommandClient",
    ), patch(
        "arrowhead_alarm.api.protocol_client.get_default_state",
    ) as get_default_state:
        state = MagicMock(spec=PanelState)
        get_default_state.return_value = state

        client = TestProtocolClient(
            "127.0.0.1",
            12345,
            credentials,
            command_timeout=3.0,
            connection_timeout=5.0
        )

        assert client._state is state


def test_client_initializes_transport_and_session(
    credentials: LoginCredentials,
) -> None:
    transport = MagicMock()
    session = MagicMock()
    command_client = MagicMock()

    with patch(
        "arrowhead_alarm.api.protocol_client.TcpTransport",
        return_value=transport,
    ) as transport_factory, patch(
        "arrowhead_alarm.api.protocol_client.AuthenticatedSession",
        return_value=session,
    ) as session_factory, patch(
        "arrowhead_alarm.api.protocol_client.CommandClient",
        return_value=command_client,
    ) as command_client_factory:
        client = TestProtocolClient(
            "127.0.0.1",
            12345,
            credentials,
            command_timeout=3.0,
            connection_timeout=5.0
        )

    transport_factory.assert_called_once_with(
        "127.0.0.1",
        12345,
    )
    session_factory.assert_called_once_with(
        transport,
        credentials,
    )
    command_client_factory.assert_called_once_with(session)
    assert client._client is command_client
    assert client.state_publisher is not None


@pytest.mark.asyncio
async def test_start_connects_sets_mode_and_subscribes(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    command_client.request.return_value = successful_result()

    with (patch(
        "arrowhead_alarm.api.protocol_client.mode_command",
        return_value="MODE COMMAND",
    ) as mode_command,
    patch(
        "arrowhead_alarm.api.protocol_client.version_command",
        return_value="VERSION COMMAND",
    ) as version_command):
        await client.connect()

    command_client.connect.assert_awaited_once_with()
    mode_command.assert_called_once_with(ProtocolMode.MODE_1)
    version_command.assert_called_once_with()
    assert command_client.request.await_args_list == [
        call('MODE COMMAND'),
        call('VERSION COMMAND')
    ]
    command_client.subscribe.assert_called_once_with(client._handle_event)


@pytest.mark.asyncio
async def test_start_raises_when_setting_mode_fails(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("mode failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.mode_command",
        return_value="MODE COMMAND",
    ):
        with pytest.raises(RuntimeError, match="mode failed") as exc_info:
            await client.connect()

    assert exc_info.value is error
    command_client.connect.assert_awaited_once_with()
    command_client.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_stop_disconnects_and_unsubscribes(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    await client.disconnect()

    command_client.disconnect.assert_awaited_once_with()
    command_client.unsubscribe.assert_called_once_with(client._handle_event)


@pytest.mark.asyncio
async def test_set_mode_success(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    command_client.request.return_value = successful_result()

    with patch(
        "arrowhead_alarm.api.protocol_client.mode_command",
        return_value="MODE",
    ) as mode_command:
        await client._set_mode()

    mode_command.assert_called_once_with(ProtocolMode.MODE_1)
    command_client.request.assert_awaited_once_with("MODE")


@pytest.mark.asyncio
async def test_set_mode_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("cannot set mode")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.mode_command",
        return_value="MODE",
    ):
        with pytest.raises(RuntimeError, match="cannot set mode") as exc_info:
            await client._set_mode()

    assert exc_info.value is error


@pytest.mark.asyncio
async def test_query_version_success(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    version = MagicMock()
    command_client.request.return_value = successful_result(version)

    with patch(
        "arrowhead_alarm.api.protocol_client.version_command",
        return_value="VERSION",
    ) as version_command:
        result = await client.query_info()

    assert result is version
    version_command.assert_called_once_with()
    command_client.request.assert_awaited_once_with("VERSION")


@pytest.mark.asyncio
async def test_query_version_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("info failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.version_command",
        return_value="VERSION",
    ):
        with pytest.raises(RuntimeError, match="info failed") as exc_info:
            await client.query_info()

    assert exc_info.value is error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("output_number", "command"),
    [
        (1, "OUTPUT ON"),
        (2, "OUTPUT ON"),
    ],
)
async def test_output_on_success(
    client: TestProtocolClient,
    command_client: MagicMock,
    output_number: int,
    command: str,
) -> None:
    command_client.request.return_value = successful_result()

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value=command,
    ) as set_output:
        await client.output_on(output_number)

    set_output.assert_called_once_with(output_number, True)
    command_client.request.assert_awaited_once_with(command)
    assert client._state.outputs[output_number].on is True


@pytest.mark.asyncio
async def test_output_on_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("output failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value="OUTPUT ON",
    ):
        with pytest.raises(RuntimeError, match="output failed") as exc_info:
            await client.output_on(1)

    assert exc_info.value is error
    assert client._state.outputs[1].on is False


@pytest.mark.asyncio
async def test_output_on_publishes_new_state(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    command_client.request.return_value = successful_result()
    dispatch = MagicMock()

    client.state_publisher.dispatch = dispatch

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value="OUTPUT ON",
    ):
        await client.output_on(1)

    dispatch.assert_called_once_with(client._state)
    assert client._state.outputs[1].on is True


@pytest.mark.asyncio
async def test_output_off_success(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    client._state.outputs[1].on = True
    command_client.request.return_value = successful_result()

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value="OUTPUT OFF",
    ) as set_output:
        await client.output_off(1)

    set_output.assert_called_once_with(1, False)
    command_client.request.assert_awaited_once_with("OUTPUT OFF")
    assert client._state.outputs[1].on is False


@pytest.mark.asyncio
async def test_output_off_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    client._state.outputs[1].on = True
    error = RuntimeError("output off failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value="OUTPUT OFF",
    ):
        with pytest.raises(RuntimeError, match="output off failed") as exc_info:
            await client.output_off(1)

    assert exc_info.value is error
    assert client._state.outputs[1].on is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("output_number", "value"),
    [
        (1, True),
        (1, False),
        (2, True),
    ],
)
async def test_query_output_success(
    client: TestProtocolClient,
    command_client: MagicMock,
    output_number: int,
    value: bool,
) -> None:
    command_client.request.return_value = successful_result(value)

    with patch(
        "arrowhead_alarm.api.protocol_client.output_state_command",
        return_value="OUTPUT STATE",
    ) as output_state:
        result = await client.query_output(output_number)

    assert result is value
    output_state.assert_called_once_with(output_number)
    command_client.request.assert_awaited_once_with("OUTPUT STATE")
    assert client._state.outputs[output_number].on is value


@pytest.mark.asyncio
async def test_query_output_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("query failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.output_state_command",
        return_value="OUTPUT STATE",
    ):
        with pytest.raises(RuntimeError, match="query failed") as exc_info:
            await client.query_output(1)

    assert exc_info.value is error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zone_number",
    [1, 2],
)
async def test_bypass_zone_success(
    client: TestProtocolClient,
    command_client: MagicMock,
    zone_number: int,
) -> None:
    command_client.request.return_value = successful_result()

    with patch(
        "arrowhead_alarm.api.protocol_client.bypass_zone_command",
        return_value="BYPASS",
    ) as bypass_command:
        await client.bypass_zone(zone_number)

    bypass_command.assert_called_once_with(zone_number)
    command_client.request.assert_awaited_once_with("BYPASS")
    assert client._state.zones[zone_number].bypassed is True


@pytest.mark.asyncio
async def test_bypass_zone_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("bypass failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.bypass_zone_command",
        return_value="BYPASS",
    ):
        with pytest.raises(RuntimeError, match="bypass failed") as exc_info:
            await client.bypass_zone(1)

    assert exc_info.value is error
    assert client._state.zones[1].bypassed is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zone_number",
    [1, 2],
)
async def test_unbypass_zone_success(
    client: TestProtocolClient,
    command_client: MagicMock,
    zone_number: int,
) -> None:
    client._state.zones[zone_number].bypassed = True
    command_client.request.return_value = successful_result()

    with patch(
        "arrowhead_alarm.api.protocol_client.unbypass_zone_command",
        return_value="UNBYPASS",
    ) as unbypass_command:
        await client.unbypass_zone(zone_number)

    unbypass_command.assert_called_once_with(zone_number)
    command_client.request.assert_awaited_once_with("UNBYPASS")
    assert client._state.zones[zone_number].bypassed is False


@pytest.mark.asyncio
async def test_unbypass_zone_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    client._state.zones[1].bypassed = True
    error = RuntimeError("unbypass failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.unbypass_zone_command",
        return_value="UNBYPASS",
    ):
        with pytest.raises(RuntimeError, match="unbypass failed") as exc_info:
            await client.unbypass_zone(1)

    assert exc_info.value is error
    assert client._state.zones[1].bypassed is True


def test_update_state_replaces_state(
    client: TestProtocolClient,
) -> None:
    original_state = client._state
    new_state = MagicMock()

    mutate = MagicMock(return_value=new_state)
    dispatch = MagicMock()
    client.state_publisher.dispatch = dispatch

    client._update_state(mutate)

    mutate.assert_called_once_with(original_state)
    assert client._state is new_state
    dispatch.assert_called_once_with(new_state)


def test_handle_event_success(
    client: TestProtocolClient,
) -> None:
    operation = MagicMock(return_value=MagicMock())
    client._update_state = MagicMock()

    with patch(
        "arrowhead_alarm.api.protocol_client.panel_operation_transformer",
        return_value=Success(operation),
    ) as transformer:
        client._handle_event("A1")

    transformer.assert_called_once_with("A1")
    client._update_state.assert_called_once_with(operation)


def test_handle_event_failure(
    client: TestProtocolClient,
) -> None:
    error = ValueError("bad event")
    client._update_state = MagicMock()

    with patch(
        "arrowhead_alarm.api.protocol_client.panel_operation_transformer",
        return_value=Failure(error),
    ) as transformer:
        client._handle_event("INVALID")

    transformer.assert_called_once_with("INVALID")
    client._update_state.assert_not_called()


@pytest.mark.asyncio
async def test_methods_do_not_update_state_on_request_failure(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = RuntimeError("request failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value="OUTPUT",
    ):
        with pytest.raises(RuntimeError):
            await client.output_on(1)

    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
        return_value="OUTPUT",
    ):
        with pytest.raises(RuntimeError):
            await client.output_off(1)

    with patch(
        "arrowhead_alarm.api.protocol_client.bypass_zone_command",
        return_value="BYPASS",
    ):
        with pytest.raises(RuntimeError):
            await client.bypass_zone(1)

    with patch(
        "arrowhead_alarm.api.protocol_client.unbypass_zone_command",
        return_value="UNBYPASS",
    ):
        with pytest.raises(RuntimeError):
            await client.unbypass_zone(1)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output_number",
    [0, -1, DEFAULT_MAX_OUTPUTS + 1, DEFAULT_MAX_OUTPUTS + 10],
)
async def test_output_on_rejects_invalid_output_number(
    client: TestProtocolClient,
    command_client: MagicMock,
    output_number: int,
) -> None:
    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
    ) as set_output_command:
        with pytest.raises(ValueError):
            await client.output_on(output_number)

    set_output_command.assert_not_called()
    command_client.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output_number",
    [0, -1, DEFAULT_MAX_OUTPUTS + 1, DEFAULT_MAX_OUTPUTS + 10],
)
async def test_output_off_rejects_invalid_output_number(
    client: TestProtocolClient,
    command_client: MagicMock,
    output_number: int,
) -> None:
    with patch(
        "arrowhead_alarm.api.protocol_client.set_output_command",
    ) as set_output_command:
        with pytest.raises(ValueError):
            await client.output_off(output_number)

    set_output_command.assert_not_called()
    command_client.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output_number",
    [0, -1, DEFAULT_MAX_OUTPUTS + 1, DEFAULT_MAX_OUTPUTS + 10],
)
async def test_query_output_rejects_invalid_output_number(
    client: TestProtocolClient,
    command_client: MagicMock,
    output_number: int,
) -> None:
    with patch(
        "arrowhead_alarm.api.protocol_client.output_state_command",
    ) as output_state_command:
        with pytest.raises(ValueError):
            await client.query_output(output_number)

    output_state_command.assert_not_called()
    command_client.request.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zone_number",
    [0, -1, DEFAULT_MAX_ZONES + 1, DEFAULT_MAX_ZONES + 10],
)
async def test_bypass_zone_rejects_invalid_zone_number(
    client: TestProtocolClient,
    command_client: MagicMock,
    zone_number: int,
) -> None:
    with patch(
        "arrowhead_alarm.api.protocol_client.bypass_zone_command",
    ) as bypass_zone_command:
        with pytest.raises(ValueError):
            await client.bypass_zone(zone_number)

    bypass_zone_command.assert_not_called()
    command_client.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "zone_number",
    [0, -1, DEFAULT_MAX_ZONES + 1, DEFAULT_MAX_ZONES + 10],
)
async def test_unbypass_zone_rejects_invalid_zone_number(
    client: TestProtocolClient,
    command_client: MagicMock,
    zone_number: int,
) -> None:
    with patch(
        "arrowhead_alarm.api.protocol_client.unbypass_zone_command",
    ) as unbypass_zone_command:
        with pytest.raises(ValueError):
            await client.unbypass_zone(zone_number)

    unbypass_zone_command.assert_not_called()
    command_client.request.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "info",
    [
        PanelInfo(
            model="ECi",
            firmware_version=VersionInfo(10, 3, 52),
            serial_number="WR5SPLS1",
        ),
        PanelInfo(
            model="MODEL",
            firmware_version=VersionInfo(1, 2, 3),
            serial_number="ABC123",
        ),
    ],
)
async def test_query_version_returns_version(
    client: TestProtocolClient,
    command_client: MagicMock,
    info: PanelInfo,
) -> None:
    command_client.request.return_value = successful_result(info)

    with patch(
        "arrowhead_alarm.api.protocol_client.version_command",
        return_value="VERSION",
    ) as version_command:
        result = await client.query_info()

    assert result is info
    version_command.assert_called_once_with()
    command_client.request.assert_awaited_once_with("VERSION")


@pytest.mark.asyncio
async def test_query_version_raises_error_response(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    error = ValueError("info request failed")
    command_client.request.return_value = failed_result(error)

    with patch(
        "arrowhead_alarm.api.protocol_client.version_command",
        return_value="VERSION",
    ) as version_command:
        with pytest.raises(ValueError, match="info request failed") as exc_info:
            await client.query_info()

    assert exc_info.value is error
    version_command.assert_called_once_with()
    command_client.request.assert_awaited_once_with("VERSION")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method",
    [
        "output_on",
        "output_off",
        "query_output",
        "bypass_zone",
        "unbypass_zone",
    ],
)
async def test_state_method_raises_error_response(
    client: TestProtocolClient,
    command_client: MagicMock,
    method: str,
) -> None:
    error = RuntimeError("panel rejected command")
    command_client.request.return_value = failed_result(error)

    command_patches = {
        "output_on": (
            "arrowhead_alarm.api.protocol_client.set_output_command",
            (1, True),
        ),
        "output_off": (
            "arrowhead_alarm.api.protocol_client.set_output_command",
            (1, False),
        ),
        "query_output": (
            "arrowhead_alarm.api.protocol_client.output_state_command",
            (1,),
        ),
        "bypass_zone": (
            "arrowhead_alarm.api.protocol_client.bypass_zone_command",
            (1,),
        ),
        "unbypass_zone": (
            "arrowhead_alarm.api.protocol_client.unbypass_zone_command",
            (1,),
        ),
    }

    patch_path, command_args = command_patches[method]
    command = MagicMock()

    with patch(
        patch_path,
        return_value=command,
    ) as command_mock:
        with pytest.raises(RuntimeError, match="panel rejected command") as exc_info:
            if method == "output_on":
                await client.output_on(1)
            elif method == "output_off":
                await client.output_off(1)
            elif method == "query_output":
                await client.query_output(1)
            elif method == "bypass_zone":
                await client.bypass_zone(1)
            else:
                await client.unbypass_zone(1)

    assert exc_info.value is error
    command_mock.assert_called_once_with(*command_args)
    command_client.request.assert_awaited_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "timeout_attr", "timeout"),
    [
        ("connect", "_connection_timeout", 10.0),
        ("disconnect", "_connection_timeout", 20.0),
        ("connect", "_connection_timeout", 30.0),
        ("disconnect", "_connection_timeout", 40.0),
    ],
)
async def test_connection_timeout(
    client,
    method,
    timeout_attr,
    timeout,
):
    setattr(client, timeout_attr, timeout)
    client._send_command = AsyncMock()

    with (
        patch(
        "arrowhead_alarm.api.protocol_client.asyncio.wait_for",
            new=AsyncMock()
        )
    as wait_for):
        await getattr(client, method)()

    coroutine = wait_for.call_args.args[0]
    assert coroutine is not None
    assert wait_for.call_args.kwargs == {"timeout": timeout}


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", [0.1, 1.0, 5.0, 100])
async def test_send_command_timeout(client, timeout):
    client._timeout = timeout
    command = MagicMock()

    with patch(
        "arrowhead_alarm.api.protocol_client.asyncio.wait_for",
        new=AsyncMock(),
    ) as wait_for:
        await client._send_command(command)

    wait_for.assert_awaited_once()
    assert wait_for.call_args.kwargs == {"timeout": timeout}


@pytest.mark.asyncio
async def test_client_initializes_version_on_connect(
    client: TestProtocolClient,
    command_client: MagicMock,
) -> None:
    version = PanelInfo(
        model="ECi",
        firmware_version=VersionInfo(10, 3, 52),
        serial_number="WR5SPLS1",
    )
    command_client.request.return_value = successful_result()

    client.query_info = AsyncMock(return_value=version)

    with patch(
        "arrowhead_alarm.api.protocol_client.mode_command",
        return_value="MODE COMMAND",
    ), patch(
        "arrowhead_alarm.api.protocol_client.version_command",
        return_value="VERSION COMMAND",
    ):
        await client.connect()

    client.query_info.assert_awaited_once_with()
    assert client.version is version