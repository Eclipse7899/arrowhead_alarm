from unittest.mock import AsyncMock, Mock, call

import pytest

from arrowhead_alarm.const import (
    AUTH_LOGIN_MSG,
    AUTH_PASSWORD_PROMPT,
    AUTH_WELCOME_MSG,
)
from arrowhead_alarm.transport.authenticated_session import AuthenticatedSession, SessionState
from arrowhead_alarm.transport.tcp import TcpDisconnected


@pytest.fixture
def transport():
    transport = Mock()
    transport.connect = AsyncMock()
    transport.disconnect = AsyncMock()
    transport.read = AsyncMock()
    transport.write = AsyncMock()
    transport.state_publisher = Mock()
    transport.state_publisher.subscribe = Mock()
    return transport


@pytest.fixture
def credentials():
    credentials = Mock()
    credentials.username = "test-user"
    credentials.password = "test-password"
    return credentials


@pytest.fixture
def session(transport, credentials):
    return AuthenticatedSession(transport, credentials)


class TestAuthenticatedSession:
    def test_initial_state_is_disconnected(self, session):
        assert session.state == SessionState.DISCONNECTED

    def test_set_state_changes_state(self, session):
        session._set_state(SessionState.CONNECTED)

        assert session.state == SessionState.CONNECTED

    def test_set_state_dispatches_new_state(self, session):
        session._set_state(SessionState.CONNECTED)

        session.state_publisher.dispatch = Mock()

        session._set_state(SessionState.DISCONNECTED)

        session.state_publisher.dispatch.assert_called_once_with(
            SessionState.DISCONNECTED
        )

    def test_set_state_does_not_dispatch_when_state_is_unchanged(self, session):
        session.state_publisher.dispatch = Mock()

        session._set_state(SessionState.DISCONNECTED)

        session.state_publisher.dispatch.assert_not_called()

    def test_transport_disconnect_sets_session_disconnected(
        self,
        session,
    ):
        session.state = SessionState.CONNECTED
        session.state_publisher.dispatch = Mock()

        session._on_transport_state_change(TcpDisconnected())

        assert session.state == SessionState.DISCONNECTED
        session.state_publisher.dispatch.assert_called_once_with(
            SessionState.DISCONNECTED
        )

    def test_transport_disconnect_does_not_dispatch_if_already_disconnected(
        self,
        session,
    ):
        session.state_publisher.dispatch = Mock()

        session._on_transport_state_change(TcpDisconnected())

        assert session.state == SessionState.DISCONNECTED
        session.state_publisher.dispatch.assert_not_called()

    def test_connect_connects_transport_then_authenticates(
        self,
        session,
        transport,
    ):
        session.authenticate = AsyncMock()

        import asyncio

        asyncio.run(session.connect())

        transport.connect.assert_awaited_once()
        session.authenticate.assert_awaited_once()

        assert transport.connect.await_count == 1
        assert session.authenticate.await_count == 1

    @pytest.mark.asyncio
    async def test_connect_awaits_transport_before_authentication(
        self,
        session,
        transport,
    ):
        calls = []

        async def connect():
            calls.append("connect")

        async def authenticate():
            calls.append("authenticate")

        transport.connect.side_effect = connect
        session.authenticate = authenticate

        await session.connect()

        assert calls == ["connect", "authenticate"]

    @pytest.mark.asyncio
    async def test_disconnect_calls_transport_disconnect(
        self,
        session,
        transport,
    ):
        await session.disconnect()

        transport.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_authenticate_sends_username_then_password(
        self,
        session,
        transport,
        credentials,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        assert transport.write.await_args_list == [
            call("test-user\n"),
            call("test-password\n"),
        ]

    @pytest.mark.asyncio
    async def test_authenticate_reads_three_prompts(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        assert transport.read.await_count == 3

    @pytest.mark.asyncio
    async def test_successful_authentication_sets_connected(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]
        session.state_publisher.dispatch = Mock()

        await session.authenticate()

        assert session.state == SessionState.CONNECTED
        session.state_publisher.dispatch.assert_called_once_with(
            SessionState.CONNECTED
        )

    @pytest.mark.asyncio
    async def test_successful_authentication_does_not_write_before_login_prompt(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        assert transport.write.await_args_list[0] == call(
            "test-user\n"
        )

    @pytest.mark.asyncio
    async def test_login_prompt_must_be_present(
        self,
        session,
        transport,
    ):
        transport.read.return_value = "unexpected prompt"

        with pytest.raises(Exception, match="Authentication failed"):
            await session.authenticate()

        transport.write.assert_not_awaited()
        assert transport.read.await_count == 1

    @pytest.mark.asyncio
    async def test_password_prompt_must_be_present(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            "unexpected prompt",
        ]

        with pytest.raises(
            Exception,
            match="Password prompt not received",
        ):
            await session.authenticate()

        assert transport.write.await_args_list == [
            call("test-user\n"),
        ]
        assert transport.read.await_count == 2

    @pytest.mark.asyncio
    async def test_welcome_message_must_be_present(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            "authentication failed",
        ]

        with pytest.raises(
            Exception,
            match="Waiting credentials",
        ):
            await session.authenticate()

        assert transport.write.await_args_list == [
            call("test-user\n"),
            call("test-password\n"),
        ]
        assert transport.read.await_count == 3

    @pytest.mark.asyncio
    async def test_failed_authentication_does_not_set_connected(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            "authentication failed",
        ]

        with pytest.raises(Exception):
            await session.authenticate()

        assert session.state == SessionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_missing_login_prompt_does_not_set_connected(
        self,
        session,
        transport,
    ):
        transport.read.return_value = "something else"

        with pytest.raises(Exception):
            await session.authenticate()

        assert session.state == SessionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_username_is_written_with_newline(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        transport.write.assert_any_await("test-user\n")

    @pytest.mark.asyncio
    async def test_password_is_written_with_newline(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        transport.write.assert_any_await("test-password\n")

    @pytest.mark.asyncio
    async def test_authentication_sequence_is_exactly_correct(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        assert transport.mock_calls == [
            call.read(),
            call.write("test-user\n"),
            call.read(),
            call.write("test-password\n"),
            call.read(),
        ]

    @pytest.mark.asyncio
    async def test_login_message_can_be_embedded_in_prompt(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            f"banner\r\n{AUTH_LOGIN_MSG}\r\n",
            f"{AUTH_PASSWORD_PROMPT}:",
            f"Some text {AUTH_WELCOME_MSG} some text",
        ]

        await session.authenticate()

        assert session.state == SessionState.CONNECTED

    @pytest.mark.asyncio
    async def test_password_prompt_can_be_embedded_in_response(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            f"prefix {AUTH_PASSWORD_PROMPT} suffix",
            AUTH_WELCOME_MSG,
        ]

        await session.authenticate()

        assert session.state == SessionState.CONNECTED

    @pytest.mark.asyncio
    async def test_welcome_message_can_be_embedded_in_response(
        self,
        session,
        transport,
    ):
        transport.read.side_effect = [
            AUTH_LOGIN_MSG,
            AUTH_PASSWORD_PROMPT,
            f"prefix {AUTH_WELCOME_MSG} suffix",
        ]

        await session.authenticate()

        assert session.state == SessionState.CONNECTED

    @pytest.mark.asyncio
    async def test_transport_connect_failure_does_not_authenticate(
        self,
        session,
        transport,
    ):
        session.authenticate = AsyncMock()
        transport.connect.side_effect = RuntimeError("connection failed")

        with pytest.raises(RuntimeError, match="connection failed"):
            await session.connect()

        session.authenticate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_transport_disconnect_failure_is_propagated(
        self,
        session,
        transport,
    ):
        transport.disconnect.side_effect = RuntimeError(
            "disconnect failed"
        )

        with pytest.raises(RuntimeError, match="disconnect failed"):
            await session.disconnect()