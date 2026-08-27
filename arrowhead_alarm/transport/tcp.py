"""Asyncio-based connection to the Arrowhead alarm system over IP."""
import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import TypeVar

from arrowhead_alarm.types import Publisher

if sys.version_info >= (3, 11):
    pass
else:
    pass

from arrowhead_alarm.const import DEF_ENCODING, DEF_READ_LENGTH

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")

@dataclass
class TcpConnected:
    """Represents a connected TCP connection."""
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

@dataclass
class TcpDisconnected:
    """Represents a disconnected TCP connection."""
    pass


TcpState = TcpDisconnected | TcpConnected


class TcpTransport:
    """Asyncio-based TCP _transport for the Arrowhead alarm system."""

    def __init__(
        self,
        host: str,
        port: int,
        encoding: str = DEF_ENCODING,
        connect_timeout: float = 10.0,
    ) -> None:
        """Initialize the TCP _transport."""
        self.host = host
        self.port = port
        self.encoding = encoding
        self.connect_timeout = connect_timeout

        self._state: TcpState = TcpDisconnected()
        self.state_publisher: Publisher[TcpState] = Publisher()

        self._write_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()

    def _set_state(self, new_state: TcpState) -> None:
        """Safely update state and fire callback only on actual state transitions."""
        if type(self._state) is type(new_state):
            return

        self._state = new_state
        self.state_publisher.dispatch(self._state)

    async def connect(self) -> None:
        async with self._state_lock:
            if isinstance(self._state, TcpConnected):
                return

            _LOGGER.info("Connecting to %s:%s", self.host, self.port)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.connect_timeout,
            )
            self._set_state(TcpConnected(reader, writer))

    async def disconnect(self) -> None:
        async with self._state_lock:
            if isinstance(self._state, TcpDisconnected):
                return

            _LOGGER.info("Disconnecting TCP _transport")
            writer = self._state.writer

            self._set_state(TcpDisconnected())

            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                _LOGGER.debug("Ignored socket error during disconnect cleanup: %s", e)

    async def write(self, data: str) -> None:
        async with self._write_lock:
            if not isinstance(self._state, TcpConnected):
                raise ConnectionError("TCP _transport not connected")

            _LOGGER.debug("TCP SEND → %r", data)
            try:
                self._state.writer.write(data.encode(self.encoding))
                await self._state.writer.drain()
            except Exception as e:
                _LOGGER.debug("Error occurred while writing to TCP _transport: %s", e)
                raise ConnectionError("Failed to write to TCP _transport")

    async def read(self, n: int = DEF_READ_LENGTH) -> str:
        if not isinstance(self._state, TcpConnected):
            raise ConnectionError("TCP _transport not connected")

        data = await self._state.reader.read(n)
        if data == b'':
            async with self._state_lock:
                self._set_state(TcpDisconnected())
            raise ConnectionError("TCP connection closed by peer")

        decoded = data.decode(self.encoding)
        _LOGGER.debug("TCP RECV ← %r", decoded)
        return decoded
