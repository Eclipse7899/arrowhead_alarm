import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Callable, TypeVar

from .authenticated_session import AuthenticatedSession
from ..util import Publisher
from ..protocol.commands import Command

@dataclass
class ClientConnected:
    read_worker: asyncio.Task


@dataclass
class ClientDisconnected:
    pass


_T = TypeVar("_T")

ClientState = ClientConnected | ClientDisconnected


class CommandClient:
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
            line = await self._session.readline()
            for handler in self._handlers:
                handler(line)

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

    async def request(self, command: Command[_T]) -> _T:
        async with self._use_handler(lambda resp: None):
            future = asyncio.get_running_loop().create_future()

            def handle(response: str):
                result = command.collector(response)
                if result.is_done and not future.done():
                    future.set_result(result.value)

            self._handlers.add(handle)

            try:
                await self._session.writeln(command.data)
                return await future
            finally:
                self._handlers.remove(handle)
