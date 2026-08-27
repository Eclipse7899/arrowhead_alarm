from enum import Enum

from arrowhead_alarm import TcpTransport, LoginCredentials
from arrowhead_alarm.const import AUTH_WELCOME_MSG, AUTH_LOGIN_MSG, AUTH_PASSWORD_PROMPT
from arrowhead_alarm.types import Publisher
from arrowhead_alarm.transport.tcp import TcpState, TcpDisconnected


class SessionState(Enum):
    CONNECTED = 0
    DISCONNECTED = 1

class AuthenticatedSession:
    def __init__(self, transport: TcpTransport, credentials: LoginCredentials | None) -> None:
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
        """Connect to the Arrowhead alarm panel."""
        await self.transport.connect()
        self.transport.state_publisher.subscribe(self._on_transport_state_change)
        await self.authenticate()

    async def disconnect(self) -> None:
        """Disconnect from the Arrowhead alarm panel."""
        await self.transport.disconnect()

    async def authenticate(self) -> None:
        """Authenticate with the Arrowhead alarm panel."""
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

    async def read(self, n: int = 1024) -> str:
        return await self.transport.read(n)

    async def write(self, data: str) -> None:
        await self.transport.write(data)