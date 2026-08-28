"""Asyncio-based connection to the Arrowhead alarm system over IP."""

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import TypeVar

from ..util import Publisher

if sys.version_info >= (3, 11):
    pass
else:
    pass

from ..const import DEF_ENCODING, DEF_LINE_DELIMITER, DEF_READ_LENGTH

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
    """Asyncio-based TCP transport for the Arrowhead alarm system."""

    def __init__(
        self,
        host: str,
        port: int,
        encoding: str = DEF_ENCODING,
        delimiter: str = DEF_LINE_DELIMITER,
        connect_timeout: float = 10.0,
    ) -> None:
        """Initialize the TCP transport.

        Args:
            host: Target host or IP address.
            port: Target TCP port.
            encoding: Character encoding to use for data transfer.
            delimiter: Line delimiter string.
            connect_timeout: Socket connection timeout in seconds.
        """
        self.host = host
        self.port = port
        self.delimiter = delimiter
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
        """Establish a TCP connection to the alarm system."""
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
        """Close the active TCP connection and release resources."""
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
        """Write raw string data to the TCP socket.

        Args:
            data: The string data to encode and send.

        Raises:
            ConnectionError: If the transport is not connected or writing fails.
        """
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

    async def readline(self) -> str:
        """Read a line terminated by newline from the TCP stream.

        Returns:
            The decoded line with trailing whitespace stripped.

        Raises:
            ConnectionError: If not connected or the peer closes connection.
        """
        if not isinstance(self._state, TcpConnected):
            raise ConnectionError("TCP _transport not connected")

        data = await self._state.reader.readline()
        if data == b"":
            async with self._state_lock:
                self._set_state(TcpDisconnected())
            raise ConnectionError("TCP connection closed by peer")

        decoded = data.decode(self.encoding)
        _LOGGER.debug("TCP RECV ← %r", decoded)
        return decoded.rstrip()

    async def read(self, n: int = DEF_READ_LENGTH) -> str:
        """Read up to n bytes from the TCP stream.

        Args:
            n: Maximum number of bytes to read.

        Returns:
            The decoded received string.

        Raises:
            ConnectionError: If not connected or the peer closes connection.
        """
        if not isinstance(self._state, TcpConnected):
            raise ConnectionError("TCP _transport not connected")

        data = await self._state.reader.read(n)
        if data == b"":
            async with self._state_lock:
                self._set_state(TcpDisconnected())
            raise ConnectionError("TCP connection closed by peer")

        decoded = data.decode(self.encoding)
        _LOGGER.debug("TCP RECV ← %r", decoded)
        return decoded

    async def writeln(self, data: str) -> None:
        """Write data appending the delimiter if not already present.

        Args:
            data: The string to write.

        Raises:
            ConnectionError: If not connected or writing fails.
        """
        if not isinstance(self._state, TcpConnected):
            raise ConnectionError("TCP _transport not connected")
        if not data.endswith(self.delimiter):
            data += self.delimiter
        await self.write(data)
