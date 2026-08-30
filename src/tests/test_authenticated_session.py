"""Tests for AuthenticatedSession."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arrowhead_alarm.transport.authenticated_session import (
    AuthenticatedSession,
    SessionState,
)
from arrowhead_alarm.transport.tcp import TcpDisconnected, TcpState
from arrowhead_alarm.util import LoginCredentials
from arrowhead_alarm.const import (
    AUTH_LOGIN_MSG,
    AUTH_PASSWORD_PROMPT,
    AUTH_WELCOME_MSG,
)


@pytest.fixture
def transport() -> MagicMock:
    transport = MagicMock()
    transport.connect = AsyncMock()
    transport.disconnect = AsyncMock()
    transport.read = AsyncMock()
    transport.write = AsyncMock()
    transport.readline = AsyncMock()
    transport.writeln = AsyncMock()
    transport.state_publisher = MagicMock()
    return transport


@pytest.fixture
def credentials() -> LoginCredentials:
    return LoginCredentials(
        username="user",
        password="password",
    )


@pytest.fixture
def session(
    transport: MagicMock,
    credentials: LoginCredentials,
) -> AuthenticatedSession:
    return AuthenticatedSession(transport, credentials)


def test_initializes(
    transport: MagicMock,
    credentials: LoginCredentials,
) -> None:
    session = AuthenticatedSession(transport, credentials)

    assert session.transport is transport
    assert session.credentials is credentials
    assert session.state is SessionState.DISCONNECTED
    assert session.state_publisher is not None


def test_initializes_without_credentials(
    transport: MagicMock,
) -> None:
    session = AuthenticatedSession(transport, None)

    assert session.credentials is None
    assert session.state is SessionState.DISCONNECTED


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def test_set_state_changes_state(
    session: AuthenticatedSession,
) -> None:
    publisher = MagicMock()
    session.state_publisher = publisher

    session._set_state(SessionState.CONNECTED)

    assert session.state is SessionState.CONNECTED
    publisher.dispatch.assert_called_once_with(SessionState.CONNECTED)


def test_set_state_does_not_publish_when_state_is_unchanged(
    session: AuthenticatedSession,
) -> None:
    publisher = MagicMock()
    session.state_publisher = publisher

    session._set_state(SessionState.DISCONNECTED)

    assert session.state is SessionState.DISCONNECTED
    publisher.dispatch.assert_not_called()


def test_on_transport_state_change_disconnects_session(
    session: AuthenticatedSession,
) -> None:
    session.state = SessionState.CONNECTED

    with patch.object(session, "_set_state") as set_state:
        session._on_transport_state_change(TcpDisconnected())

    set_state.assert_called_once_with(SessionState.DISCONNECTED)


def test_on_transport_state_change_ignores_non_disconnected_state(
    session: AuthenticatedSession,
) -> None:
    state = MagicMock(spec=TcpState)

    with patch.object(session, "_set_state") as set_state:
        session._on_transport_state_change(state)

    set_state.assert_not_called()


# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_connects_transport_subscribes_and_authenticates(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    with patch.object(
        session,
        "authenticate",
        new_callable=AsyncMock,
    ) as authenticate:
        await session.connect()

    transport.connect.assert_awaited_once_with()
    transport.state_publisher.subscribe.assert_called_once_with(
        session._on_transport_state_change,
    )
    authenticate.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_connect_propagates_transport_connection_error(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.connect.side_effect = RuntimeError("connection failed")

    with pytest.raises(RuntimeError, match="connection failed"):
        await session.connect()

    transport.state_publisher.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    await session.disconnect()

    transport.disconnect.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_disconnect_propagates_transport_error(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.disconnect.side_effect = RuntimeError("disconnect failed")

    with pytest.raises(RuntimeError, match="disconnect failed"):
        await session.disconnect()


@pytest.mark.asyncio
async def test_authenticate_succeeds_when_welcome_is_received(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.read.return_value = AUTH_WELCOME_MSG

    with patch.object(session, "_set_state") as set_state:
        await session.authenticate()

    transport.read.assert_awaited_once_with()
    transport.write.assert_not_awaited()
    set_state.assert_called_once_with(SessionState.CONNECTED)


@pytest.mark.asyncio
async def test_authenticate_with_credentials(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.read.side_effect = [
        AUTH_LOGIN_MSG,
        AUTH_PASSWORD_PROMPT,
        AUTH_WELCOME_MSG,
    ]

    with patch.object(session, "_set_state") as set_state:
        await session.authenticate()

    assert transport.read.await_count == 3
    set_state.assert_called_once_with(SessionState.CONNECTED)


@pytest.mark.asyncio
async def test_authenticate_requires_credentials(
    transport: MagicMock,
) -> None:
    session = AuthenticatedSession(transport, None)

    transport.read.return_value = AUTH_LOGIN_MSG

    with pytest.raises(
        ValueError,
        match="Credentials are required for authentication.",
    ):
        await session.authenticate()

    transport.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_fails_when_password_prompt_is_not_received(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.read.side_effect = [
        AUTH_LOGIN_MSG,
        "unexpected prompt",
    ]

    with pytest.raises(
        Exception,
        match="Authentication failed: Password prompt not received.",
    ):
        await session.authenticate()

    transport.write.assert_awaited_once_with("user\n")


@pytest.mark.asyncio
async def test_authenticate_fails_when_welcome_is_not_received(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.read.side_effect = [
        AUTH_LOGIN_MSG,
        AUTH_PASSWORD_PROMPT,
        "authentication failed",
    ]

    with pytest.raises(
        Exception,
        match="Authentication failed: Waiting credentials.",
    ):
        await session.authenticate()

    assert transport.read.await_count == 3

@pytest.mark.asyncio
async def test_authenticate_fails_when_initial_prompt_is_unexpected(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.read.return_value = "unexpected prompt"

    with pytest.raises(
        Exception,
        match="Authentication failed: Done prompt not received.",
    ):
        await session.authenticate()

    transport.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_readline_delegates_to_transport(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.readline.return_value = "some response"

    result = await session.readline()

    assert result == "some response"
    transport.readline.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_readline_propagates_transport_error(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.readline.side_effect = RuntimeError("read failed")

    with pytest.raises(RuntimeError, match="read failed"):
        await session.readline()


@pytest.mark.asyncio
async def test_writeln_delegates_to_transport(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    await session.writeln("TEST COMMAND")

    transport.writeln.assert_awaited_once_with("TEST COMMAND")


@pytest.mark.asyncio
async def test_writeln_propagates_transport_error(
    session: AuthenticatedSession,
    transport: MagicMock,
) -> None:
    transport.writeln.side_effect = RuntimeError("write failed")

    with pytest.raises(RuntimeError, match="write failed"):
        await session.writeln("TEST COMMAND")
