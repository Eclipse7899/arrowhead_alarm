"""Authenticated session management over TCP transport."""

from enum import Enum

from ..const import AUTH_LOGIN_MSG, AUTH_PASSWORD_PROMPT, AUTH_WELCOME_MSG
from ..util import LoginCredentials, Publisher
from .tcp import TcpDisconnected, TcpState, TcpTransport


class SessionState(Enum):
    """Enumeration of authenticated session states."""

    CONNECTED = 0
    DISCONNECTED = 1


class AuthenticatedSession:
    """Manages an authenticated TCP session with an Arrowhead alarm panel."""

    def __init__(self, transport: TcpTransport, credentials: LoginCredentials | None) -> None:
        """Initialize the authenticated session.

        Args:
            transport: The underlying TCP transport instance.
            credentials: Login credentials for panel authentication, or None.
        """
        self.state = SessionState.DISCONNECTED
        self.state_publisher: Publisher[SessionState] = Publisher()
        self.transport = transport
        self.credentials = credentials

    def _set_state(self, new_state: SessionState) -> None:
        if self.state == new_state:
            return
        self.state = new_state
        self.state_publisher.dispatch(self.state)

    def _on_transport_state_change(self, state: TcpState) -> None:
        if isinstance(state, TcpDisconnected):
            self._set_state(SessionState.DISCONNECTED)

    async def connect(self) -> None:
        """Connect to the Arrowhead alarm panel and perform authentication."""
        await self.transport.connect()
        self.transport.state_publisher.subscribe(self._on_transport_state_change)
        await self.authenticate()

    async def disconnect(self) -> None:
        """Disconnect from the Arrowhead alarm panel."""
        await self.transport.disconnect()

    async def authenticate(self) -> None:
        """Authenticate with the Arrowhead alarm panel.

        Raises:
            ValueError: If credentials are required but not provided.
            Exception: If authentication fails or unexpected prompts are encountered.
        """
        prompt = await self.transport.read()
        if AUTH_LOGIN_MSG in prompt:
            if self.credentials is None:
                raise ValueError("Credentials are required for authentication.")
            await self.transport.write(self.credentials.username + "\n")
            prompt = await self.transport.read()
            if AUTH_PASSWORD_PROMPT in prompt:
                await self.transport.write(self.credentials.password + "\n")
                prompt = await self.transport.read()
                if AUTH_WELCOME_MSG in prompt:
                    self._set_state(SessionState.CONNECTED)
                else:
                    raise Exception("Authentication failed: Waiting credentials.")
            else:
                raise Exception("Authentication failed: Password prompt not received.")
        elif AUTH_WELCOME_MSG in prompt:
            self._set_state(SessionState.CONNECTED)
        else:
            raise Exception("Authentication failed: Done prompt not received.")

    async def readline(self) -> str:
        """Read a line of text from the session transport.

        Returns:
            The line read from the transport.
        """
        return await self.transport.readline()

    async def writeln(self, data: str) -> None:
        """Write a line of text to the session transport.

        Args:
            data: The string data to write.
        """
        await self.transport.writeln(data)
