import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from arrowhead_alarm.transport.authenticated_session import AuthenticatedSession
from arrowhead_alarm.transport.command_client import CommandClient, ClientDisconnected, ClientConnected


@pytest.fixture
def session():
    session = Mock(spec=AuthenticatedSession)
    session.connect = AsyncMock()
    session.disconnect = AsyncMock()
    session.read = AsyncMock()
    session.write = AsyncMock()
    return session


@pytest.fixture
def client(session):
    return CommandClient(session)


class TestRequestClientState:
    def test_initial_state_is_disconnected(self, client):
        assert isinstance(client.state, ClientDisconnected)

    def test_initial_handlers_are_empty(self, client):
        assert client._handlers == set()

    def test_set_state_changes_state(self, client):
        worker = Mock()
        new_state = ClientConnected(worker)

        client._set_state(new_state)

        assert client.state is new_state

    def test_set_state_dispatches_new_state(self, client):
        client.state_publisher.dispatch = Mock()

        worker = Mock()
        new_state = ClientConnected(worker)

        client._set_state(new_state)

        client.state_publisher.dispatch.assert_called_once_with(new_state)

    def test_set_state_does_not_dispatch_same_state(
        self,
        client,
    ):
        client.state_publisher.dispatch = Mock()

        state = ClientDisconnected()

        client._set_state(state)

        client.state_publisher.dispatch.assert_not_called()

    def test_disconnect_state_instances_compare_equal(self, client):
        client.state_publisher.dispatch = Mock()

        client._set_state(ClientDisconnected())

        client.state_publisher.dispatch.assert_not_called()


class TestRequestClientConnect:
    @pytest.mark.asyncio
    async def test_connect_connects_session(self, client, session):
        await client.connect()

        session.connect.assert_awaited_once()

        # Don't leave background task running.
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_starts_read_worker(self, client, session):
        session.read.side_effect = asyncio.CancelledError

        await client.connect()

        assert isinstance(client.state, ClientConnected)
        assert isinstance(client.state.read_worker, asyncio.Task)

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_sets_connected_state(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError

        await client.connect()

        assert isinstance(client.state, ClientConnected)

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_publishes_connected_state(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError
        client.state_publisher.dispatch = Mock()

        await client.connect()

        client.state_publisher.dispatch.assert_called_once()
        state = client.state_publisher.dispatch.call_args.args[0]

        assert isinstance(state, ClientConnected)

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_does_not_start_worker_if_session_connect_fails(
        self,
        client,
        session,
    ):
        session.connect.side_effect = RuntimeError("connection failed")

        with pytest.raises(RuntimeError, match="connection failed"):
            await client.connect()

        assert isinstance(client.state, ClientDisconnected)
        session.connect.assert_awaited_once()


class TestReadWorker:
    @pytest.mark.asyncio
    async def test_read_worker_reads_from_session(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError

        task = asyncio.create_task(client._read_worker())

        await asyncio.sleep(0)

        session.read.assert_awaited_once()

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_read_worker_calls_handler_with_response(
        self,
        client,
        session,
    ):
        handler = Mock()
        client._handlers.add(handler)

        session.read.side_effect = [
            "response",
            asyncio.CancelledError(),
        ]

        with pytest.raises(asyncio.CancelledError):
            await client._read_worker()

        handler.assert_called_once_with("response")

    @pytest.mark.asyncio
    async def test_read_worker_continues_reading(
        self,
        client,
        session,
    ):
        handler = Mock()
        client._handlers.add(handler)

        session.read.side_effect = [
            "response-1",
            "response-2",
            "response-3",
            asyncio.CancelledError(),
        ]

        with pytest.raises(asyncio.CancelledError):
            await client._read_worker()

        assert handler.call_args_list == [
            (( "response-1",),),
            (( "response-2",),),
            (( "response-3",),),
        ]

    @pytest.mark.asyncio
    async def test_read_worker_calls_all_handlers(
        self,
        client,
        session,
    ):
        handler_1 = Mock()
        handler_2 = Mock()

        client._handlers.update({
            handler_1,
            handler_2,
        })

        session.read.side_effect = [
            "response",
            asyncio.CancelledError(),
        ]

        with pytest.raises(asyncio.CancelledError):
            await client._read_worker()

        handler_1.assert_called_once_with("response")
        handler_2.assert_called_once_with("response")

    @pytest.mark.asyncio
    async def test_read_worker_does_not_call_handler_when_no_response(
        self,
        client,
        session,
    ):
        handler = Mock()
        client._handlers.add(handler)

        session.read.side_effect = asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await client._read_worker()

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_worker_can_be_cancelled(
        self,
        client,
        session,
    ):
        started = asyncio.Event()

        async def read():
            started.set()
            await asyncio.Future()

        session.read.side_effect = read

        task = asyncio.create_task(client._read_worker())

        await started.wait()

        assert not task.done()

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert task.cancelled()


class TestUseHandler:
    @pytest.mark.asyncio
    async def test_handler_is_registered_inside_context(
        self,
        client,
    ):
        handler = Mock()

        async with client._use_handler(handler):
            assert handler in client._handlers

    @pytest.mark.asyncio
    async def test_handler_is_removed_after_context(
        self,
        client,
    ):
        handler = Mock()

        async with client._use_handler(handler):
            pass

        assert handler not in client._handlers

    @pytest.mark.asyncio
    async def test_handler_is_removed_when_context_raises(
        self,
        client,
    ):
        handler = Mock()

        with pytest.raises(RuntimeError):
            async with client._use_handler(handler):
                assert handler in client._handlers
                raise RuntimeError("boom")

        assert handler not in client._handlers

    @pytest.mark.asyncio
    async def test_multiple_handlers_can_be_registered(
        self,
        client,
    ):
        handler_1 = Mock()
        handler_2 = Mock()

        async with client._use_handler(handler_1):
            async with client._use_handler(handler_2):
                assert client._handlers == {
                    handler_1,
                    handler_2,
                }

        assert client._handlers == set()

    @pytest.mark.asyncio
    async def test_same_handler_is_only_stored_once(
        self,
        client,
    ):
        handler = Mock()

        async with client._use_handler(handler):
            async with client._use_handler(handler):
                assert len(client._handlers) == 1

        assert handler not in client._handlers


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_does_nothing_when_already_disconnected(
        self,
        client,
        session,
    ):
        await client.disconnect()

        session.disconnect.assert_not_awaited()

        assert isinstance(client.state, ClientDisconnected)

    @pytest.mark.asyncio
    async def test_disconnect_calls_session_disconnect(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError

        await client.connect()
        await client.disconnect()

        session.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_cancels_read_worker(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError

        await client.connect()

        worker = client.state._read_worker

        await client.disconnect()

        assert worker.cancelled() or worker.done()

    @pytest.mark.asyncio
    async def test_disconnect_sets_disconnected_state(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError

        await client.connect()
        await client.disconnect()

        assert isinstance(client.state, ClientDisconnected)

    @pytest.mark.asyncio
    async def test_disconnect_publishes_disconnected_state(
        self,
        client,
        session,
    ):
        session.read.side_effect = asyncio.CancelledError
        client.state_publisher.dispatch = Mock()

        await client.connect()
        client.state_publisher.dispatch.reset_mock()

        await client.disconnect()

        client.state_publisher.dispatch.assert_called_once_with(
            ClientDisconnected()
        )


class TestSend:
    @pytest.mark.asyncio
    async def test_send_writes_request_data(
        self,
        client,
        session,
    ):
        future = asyncio.get_running_loop().create_future()
        future.set_result("response")

        handler = Mock()

        response = Mock()
        response.handler = handler
        response.future = future

        request = Mock()
        request.request_data = "hello\n"
        request.response = response

        result = await client.request(request)

        assert result == "response"
        session.write.assert_awaited_once_with("hello\n")

    @pytest.mark.asyncio
    async def test_send_returns_response_future_result(
        self,
        client,
        session,
    ):
        future = asyncio.get_running_loop().create_future()
        future.set_result("my response")

        handler = Mock()

        response = Mock()
        response.handler = handler
        response.future = future

        request = Mock()
        request.request_data = "request"
        request.response = response

        result = await client.request(request)

        assert result == "my response"

    @pytest.mark.asyncio
    async def test_send_registers_response_handler(
        self,
        client,
        session,
    ):
        handler = Mock()

        future = asyncio.get_running_loop().create_future()

        async def complete_future():
            await asyncio.sleep(0)
            future.set_result("response")

        asyncio.create_task(complete_future())

        response = Mock()
        response.handler = handler
        response.future = future

        request = Mock()
        request.request_data = None
        request.response = response

        # Verify callback exists while send is waiting.
        task = asyncio.create_task(client.request(request))

        await asyncio.sleep(0)

        assert handler in client._handlers

        await task

    @pytest.mark.asyncio
    async def test_send_removes_handler_after_response(
        self,
        client,
        session,
    ):
        handler = Mock()

        future = asyncio.get_running_loop().create_future()
        future.set_result("response")

        response = Mock()
        response.handler = handler
        response.future = future

        request = Mock()
        request.request_data = None
        request.response = response

        await client.request(request)

        assert handler not in client._handlers

    @pytest.mark.asyncio
    async def test_send_removes_handler_when_future_fails(
        self,
        client,
        session,
    ):
        handler = Mock()

        future = asyncio.get_running_loop().create_future()
        future.set_exception(RuntimeError("request failed"))

        response = Mock()
        response.handler = handler
        response.future = future

        request = Mock()
        request.request_data = None
        request.response = response

        with pytest.raises(RuntimeError, match="request failed"):
            await client.request(request)

        assert handler not in client._handlers

    @pytest.mark.asyncio
    async def test_send_without_request_data_does_not_write(
        self,
        client,
        session,
    ):
        future = asyncio.get_running_loop().create_future()
        future.set_result("response")

        response = Mock()
        response.handler = Mock()
        response.future = future

        request = Mock()
        request.request_data = None
        request.response = response

        result = await client.request(request)

        assert result == "response"
        session.write.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_writes_before_waiting_for_response(
        self,
        client,
        session,
    ):
        events = []

        async def write(data):
            events.append(("write", data))

        future = asyncio.get_running_loop().create_future()

        async def wait_for_response():
            events.append(("wait",))
            return await future

        session.write.side_effect = write

        response = Mock()
        response.handler = Mock()
        response.future = Mock()
        response.future.__await__ = wait_for_response

        # Simpler equivalent using an actual Future:
        response.future = future

        request = Mock()
        request.request_data = "hello"
        request.response = response

        task = asyncio.create_task(client.request(request))

        await asyncio.sleep(0)

        assert events == [("write", "hello")]

        future.set_result("response")
        await task

    @pytest.mark.asyncio
    async def test_send_removes_handler_if_write_fails(
        self,
        client,
        session,
    ):
        handler = Mock()

        session.write.side_effect = RuntimeError("write failed")

        response = Mock()
        response.handler = handler
        response.future = asyncio.Future()

        request = Mock()
        request.request_data = "hello"
        request.response = response

        with pytest.raises(RuntimeError, match="write failed"):
            await client.request(request)

        assert handler not in client._handlers