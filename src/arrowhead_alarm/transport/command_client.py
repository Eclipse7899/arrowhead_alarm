"""Command client for managing commands over authenticated sessions."""

import asyncio
from contextlib import (
    asynccontextmanager,
)
from dataclasses import dataclass
from typing import AsyncGenerator, Callable, TypeVar

from ..protocol.commands import Command
from ..util import Publisher
from .authenticated_session import AuthenticatedSession


@dataclass
class ClientConnected:
    """Represents the connected state of a command client."""

    read_worker: asyncio.Task


@dataclass
class ClientDisconnected:
    """Represents the disconnected state of a command client."""

    pass


_T = TypeVar("_T")

ClientState = ClientConnected | ClientDisconnected


class CommandClient:
    """Client for executing commands and managing message handlers over a session."""

    def __init__(self, session: AuthenticatedSession) -> None:
        """Initialize the command client.

        Args:
            session: The authenticated session instance to communicate through.
        """
        self._session = session
        self.state = ClientDisconnected()
        self.state_publisher: Publisher[ClientState] = Publisher()
        self._handlers: set[Callable[[str], None]] = set()

    def _set_state(self, new_state: ClientState) -> None:
        if self.state == new_state:
            return
        self.state = new_state
        self.state_publisher.dispatch(self.state)

    async def connect(self) -> None:
        """Connect the underlying session and start the background read worker."""
        await self._session.connect()
        read_worker = asyncio.create_task(self._read_worker())
        self._set_state(ClientConnected(read_worker))

    async def disconnect(self) -> None:
        """Disconnect the session and cancel the background read worker."""
        if isinstance(self.state, ClientConnected):
            await self._session.disconnect()
            self.state.read_worker.cancel()
            self._set_state(ClientDisconnected())

    async def _read_worker(self) -> None:
        while True:
            line = await self._session.readline()
            for handler in self._handlers:
                handler(line)

    @asynccontextmanager
    async def _use_handler(
        self, handler: Callable[[str], None]
    ) -> AsyncGenerator[None, bool | None]:
        self._handlers.add(handler)
        try:
            yield
        finally:
            self._handlers.remove(handler)

    def subscribe(self, handler: Callable[[str], None]) -> None:
        """Subscribe a handler callback to received incoming message lines.

        Args:
            handler: Callable that processes incoming line strings.
        """
        self._handlers.add(handler)

    def unsubscribe(self, handler: Callable[[str], None]) -> None:
        """Unsubscribe a handler callback from incoming message lines.

        Args:
            handler: The callback function to remove.
        """
        self._handlers.remove(handler)

    async def request(self, command: Command[_T]) -> _T:
        """Send a command to the panel and await its completed result.

        Args:
            command: The command object specifying payload and response collector.

        Returns:
            The collected command result.
        """
        async with self._use_handler(lambda resp: None):
            future = asyncio.get_running_loop().create_future()

            def handle(response: str) -> None:
                result = command.collector(response)
                if result.is_done and not future.done():
                    future.set_result(result.value)

            self._handlers.add(handle)

            try:
                await self._session.writeln(command.data)
                return await future
            finally:
                self._handlers.remove(handle)
