from contextlib import asynccontextmanager
from typing import Callable, TypeVar
from arrowhead_alarm.protocol import Request
import asyncio
from dataclasses import dataclass

from arrowhead_alarm.types import Publisher
from arrowhead_alarm.transport.authenticated_session import AuthenticatedSession

@dataclass
class ClientConnected:
    read_worker: asyncio.Task

@dataclass
class ClientDisconnected:
    pass

_T = TypeVar("_T")

ClientState = ClientConnected | ClientDisconnected

class RequestClient:
    def __init__(self, session: AuthenticatedSession):
        self._session = session
        self.state = ClientDisconnected()
        self.state_publisher: Publisher[ClientState] = Publisher()
        self._handlers: set[Callable[[str], None]] = set()

    def _set_state(self, new_state: ClientState):
        if self.state == new_state:
            return
        self.state = new_state
        self.state_publisher.dispatch(self.state)

    async def connect(self):
        await self._session.connect()
        read_worker = asyncio.create_task(self._read_worker())
        self._set_state(ClientConnected(read_worker))

    async def disconnect(self):
        if isinstance(self.state, ClientConnected):
            await self._session.disconnect()
            self.state.read_worker.cancel()
            self._set_state(ClientDisconnected())

    async def _read_worker(self):
        while True:
            resp = await self._session.read()
            for handler in self._handlers:
                handler(resp)

    @asynccontextmanager
    async def _use_handler(self, handler: Callable[[str], None]):
        self._handlers.add(handler)
        try:
            yield handler
        finally:
            self._handlers.remove(handler)

    def subscribe(self, handler: Callable[[str], None]):
        self._handlers.add(handler)

    def unsubscribe(self, handler: Callable[[str], None]):
        self._handlers.remove(handler)

    async def request(self, request: Request[_T]) -> _T:
        async with self._use_handler(request.response.callback):
            if request.request_data is not None:
                await self._session.write(request.request_data)
            return await request.response.future

