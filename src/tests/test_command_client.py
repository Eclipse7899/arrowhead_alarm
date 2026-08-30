import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arrowhead_alarm.transport.authenticated_session import AuthenticatedSession
from arrowhead_alarm.transport.command_client import (
    ClientConnected,
    ClientDisconnected,
    CommandClient,
)


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock(spec=AuthenticatedSession)
    session.connect = AsyncMock()
    session.disconnect = AsyncMock()
    session.readline = AsyncMock()
    session.writeln = AsyncMock()
    return session


@pytest.fixture
def client(session: MagicMock) -> CommandClient:
    return CommandClient(session)


@dataclass
class CollectorResult:
    is_done: bool
    value: object = None


def make_command(
    data: str = "TEST COMMAND",
    is_done: bool = True,
    value: object = "result",
) -> MagicMock:
    command = MagicMock()
    command.data = data
    command.collector.return_value = CollectorResult(
        is_done=is_done,
        value=value,
    )
    return command


def test_initializes_with_session(session: MagicMock) -> None:
    client = CommandClient(session)

    assert client._session is session
    assert isinstance(client.state, ClientDisconnected)
    assert client._handlers == set()
    assert client.state_publisher is not None


def test_set_state_changes_state(client: CommandClient) -> None:
    publisher = MagicMock()
    client.state_publisher = publisher

    new_state = ClientConnected(MagicMock())

    client._set_state(new_state)

    assert client.state is new_state
    publisher.dispatch.assert_called_once_with(new_state)


def test_set_state_does_not_publish_same_state(
    client: CommandClient,
) -> None:
    publisher = MagicMock()
    client.state_publisher = publisher

    state = client.state

    client._set_state(state)

    assert client.state is state
    publisher.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_connect(
    client: CommandClient,
    session: MagicMock,
) -> None:
    read_worker = MagicMock()

    with patch(
        "arrowhead_alarm.transport.command_client.asyncio.create_task",
        return_value=read_worker,
    ) as create_task:
        await client.connect()

    session.connect.assert_awaited_once_with()
    create_task.assert_called_once()

    assert isinstance(client.state, ClientConnected)
    assert client.state.read_worker is read_worker


@pytest.mark.asyncio
async def test_disconnect_when_disconnected(
    client: CommandClient,
    session: MagicMock,
) -> None:
    await client.disconnect()

    session.disconnect.assert_not_awaited()
    assert isinstance(client.state, ClientDisconnected)


@pytest.mark.asyncio
async def test_disconnect(
    client: CommandClient,
    session: MagicMock,
) -> None:
    read_worker = MagicMock()
    client.state = ClientConnected(read_worker)

    await client.disconnect()

    session.disconnect.assert_awaited_once_with()
    read_worker.cancel.assert_called_once_with()
    assert isinstance(client.state, ClientDisconnected)


def test_subscribe(client: CommandClient) -> None:
    handler = MagicMock()

    client.subscribe(handler)

    assert handler in client._handlers


def test_subscribe_same_handler_twice(
    client: CommandClient,
) -> None:
    handler = MagicMock()

    client.subscribe(handler)
    client.subscribe(handler)

    assert client._handlers == {handler}


def test_unsubscribe(client: CommandClient) -> None:
    handler = MagicMock()

    client.subscribe(handler)
    client.unsubscribe(handler)

    assert handler not in client._handlers


def test_unsubscribe_missing_handler(
    client: CommandClient,
) -> None:
    handler = MagicMock()

    with pytest.raises(KeyError):
        client.unsubscribe(handler)


@pytest.mark.asyncio
async def test_read_worker_calls_handlers(
    client: CommandClient,
    session: MagicMock,
) -> None:
    handler = MagicMock()
    client.subscribe(handler)

    session.readline.side_effect = [
        "response",
        asyncio.CancelledError(),
    ]

    with pytest.raises(asyncio.CancelledError):
        await client._read_worker()

    handler.assert_called_once_with("response")


@pytest.mark.asyncio
async def test_read_worker_calls_all_handlers(
    client: CommandClient,
    session: MagicMock,
) -> None:
    handler_one = MagicMock()
    handler_two = MagicMock()

    client.subscribe(handler_one)
    client.subscribe(handler_two)

    session.readline.side_effect = [
        "response",
        asyncio.CancelledError(),
    ]

    with pytest.raises(asyncio.CancelledError):
        await client._read_worker()

    handler_one.assert_called_once_with("response")
    handler_two.assert_called_once_with("response")


@pytest.mark.asyncio
async def test_request_returns_result(
    client: CommandClient,
    session: MagicMock,
) -> None:
    command = make_command(
        data="TEST COMMAND",
        value="result",
    )

    async def writeln(data: str) -> None:
        for handler in list(client._handlers):
            handler("response")

    session.writeln.side_effect = writeln

    result = await client.request(command)

    assert result == "result"
    session.writeln.assert_awaited_once_with("TEST COMMAND")
    command.collector.assert_called_once_with("response")


@pytest.mark.asyncio
async def test_request_waits_until_collector_is_done(
    client: CommandClient,
    session: MagicMock,
) -> None:
    command = MagicMock()
    command.data = "TEST COMMAND"
    command.collector.side_effect = [
        CollectorResult(False),
        CollectorResult(True, "result"),
    ]

    async def writeln(data: str) -> None:
        for handler in list(client._handlers):
            handler("response 1")
            handler("response 2")

    session.writeln.side_effect = writeln

    result = await client.request(command)

    assert result == "result"
    assert command.collector.call_count == 2


@pytest.mark.asyncio
async def test_request_removes_handler_after_success(
    client: CommandClient,
    session: MagicMock,
) -> None:
    command = make_command()

    async def writeln(data: str) -> None:
        for handler in list(client._handlers):
            handler("response")

    session.writeln.side_effect = writeln

    await client.request(command)

    assert client._handlers == set()


@pytest.mark.asyncio
async def test_request_removes_handler_when_writeln_fails(
    client: CommandClient,
    session: MagicMock,
) -> None:
    command = make_command()

    session.writeln.side_effect = RuntimeError("write failed")

    with pytest.raises(RuntimeError, match="write failed"):
        await client.request(command)

    assert client._handlers == set()


@pytest.mark.asyncio
async def test_request_preserves_existing_subscriber(
    client: CommandClient,
    session: MagicMock,
) -> None:
    subscriber = MagicMock()
    client.subscribe(subscriber)

    command = make_command()

    async def writeln(data: str) -> None:
        for handler in list(client._handlers):
            handler("response")

    session.writeln.side_effect = writeln

    await client.request(command)

    assert client._handlers == {subscriber}