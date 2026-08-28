import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arrowhead_alarm.transport.tcp import TcpTransport, TcpDisconnected, TcpConnected


@pytest.fixture
def mock_reader_writer():
    """Fixture to provide mocked StreamReader and StreamWriter."""
    reader = AsyncMock(spec=asyncio.StreamReader)

    # StreamWriter has a mix of sync and async methods
    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    return reader, writer


@pytest.fixture
def transport():
    """Fixture to provide TcpTransport with default configuration."""
    return TcpTransport(
        host="192.168.1.100",
        port=5000,
        encoding="ascii",
        connect_timeout=0.1
    )


@pytest.mark.asyncio
class TestTcpTransport:
    async def test_init(self, transport):
        """Test the initialization of the transport."""
        assert transport.host == "192.168.1.100"
        assert transport.port == 5000
        assert transport.encoding == "ascii"
        assert isinstance(transport._state, TcpDisconnected)

    @patch("asyncio.open_connection")
    async def test_connect_success(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test successful connection."""
        mock_open_connection.return_value = mock_reader_writer

        await transport.connect()

        mock_open_connection.assert_called_once_with("192.168.1.100", 5000)
        assert isinstance(transport._state, TcpConnected)
        assert transport._state.reader == mock_reader_writer[0]
        assert transport._state.writer == mock_reader_writer[1]

    @patch("asyncio.open_connection")
    async def test_connect_already_connected(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test connecting when already connected."""
        mock_open_connection.return_value = mock_reader_writer

        # Connect first time
        await transport.connect()
        assert mock_open_connection.call_count == 1

        # Connect again
        await transport.connect()

        # Verify open_connection wasn't called a second time
        assert mock_open_connection.call_count == 1

    @patch("asyncio.open_connection")
    async def test_connect_timeout(self, mock_open_connection, transport):
        """Test connection timing out."""

        async def slow_connection(*args, **kwargs):
            await asyncio.sleep(0.5)

        mock_open_connection.side_effect = slow_connection

        with pytest.raises(asyncio.TimeoutError):
            await transport.connect()

        assert isinstance(transport._state, TcpDisconnected)

    @patch("asyncio.open_connection")
    async def test_disconnect(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test disconnecting an active connection."""
        mock_open_connection.return_value = mock_reader_writer
        await transport.connect()

        await transport.disconnect()

        mock_reader_writer[1].close.assert_called_once()
        mock_reader_writer[1].wait_closed.assert_called_once()
        assert isinstance(transport._state, TcpDisconnected)

    async def test_disconnect_already_disconnected(self, transport):
        """Test disconnecting when already disconnected does not error."""
        assert isinstance(transport._state, TcpDisconnected)

        # Should not raise any exceptions
        await transport.disconnect()

    @patch("asyncio.open_connection")
    async def test_write_success(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test successfully writing request."""
        mock_open_connection.return_value = mock_reader_writer
        await transport.connect()

        test_payload = "TEST_CMD"
        await transport.write(test_payload)

        mock_reader_writer[1].write.assert_called_once_with(
            test_payload.encode(transport.encoding)
        )
        mock_reader_writer[1].drain.assert_called_once()

    async def test_write_disconnected(self, transport):
        """Test writing when not connected raises ConnectionError."""
        with pytest.raises(ConnectionError, match="TCP _transport not connected"):
            await transport.write("TEST_CMD")

    @patch("asyncio.open_connection")
    async def test_read_success(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test successfully reading request."""
        mock_open_connection.return_value = mock_reader_writer
        await transport.connect()

        # Mock the network response
        mock_reader_writer[0].read.return_value = b"RESPONSE_DATA"

        result = await transport.read(n=1024)

        mock_reader_writer[0].read.assert_called_once_with(1024)
        assert result == "RESPONSE_DATA"

    async def test_read_disconnected(self, transport):
        """Test reading when not connected raises ConnectionError."""
        with pytest.raises(ConnectionError, match="TCP _transport not connected"):
            await transport.read()

    @patch("asyncio.open_connection")
    async def test_read_connection_closed_by_peer(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test read behavior when the peer closes the socket (EOF)."""
        mock_open_connection.return_value = mock_reader_writer
        await transport.connect()

        # Mock EOF
        mock_reader_writer[0].read.return_value = b""

        with pytest.raises(ConnectionError, match="TCP connection closed by peer"):
            await transport.read()

        # Ensure internal state is updated to disconnected
        assert isinstance(transport._state, TcpDisconnected)

    @patch("asyncio.open_connection")
    async def test_concurrent_connects(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test that multiple concurrent calls to connect() only open one connection."""

        # Simulate network delay to ensure the lock is highly contested
        async def slow_connect(*args, **kwargs):
            await asyncio.sleep(0.05)
            return mock_reader_writer

        mock_open_connection.side_effect = slow_connect

        # Fire 5 connect requests at the exact same time
        tasks = [transport.connect() for _ in range(5)]
        await asyncio.gather(*tasks)

        # The lock should ensure open_connection is only executed exactly once
        assert mock_open_connection.call_count == 1
        assert isinstance(transport._state, TcpConnected)

    @patch("asyncio.open_connection")
    async def test_concurrent_writes(
            self, mock_open_connection, transport, mock_reader_writer
    ):
        """Test that multiple concurrent writes are safely queued and executed."""
        mock_open_connection.return_value = mock_reader_writer
        await transport.connect()

        # Simulate network latency during the drain() call to force lock contention
        async def slow_drain():
            await asyncio.sleep(0.02)

        mock_reader_writer[1].drain.side_effect = slow_drain

        # Fire 3 writes concurrently
        messages = ["msg_A", "msg_B", "msg_C"]
        tasks = [transport.write(msg) for msg in messages]
        await asyncio.gather(*tasks)

        # Ensure write and drain were both called exactly 3 times
        assert mock_reader_writer[1].write.call_count == 3
        assert mock_reader_writer[1].drain.call_count == 3

        # Verify all payloads were written (order isn't guaranteed by gather,
        # but all must be present)
        written_args = [
            call.args[0].decode(transport.encoding)
            for call in mock_reader_writer[1].write.mock_calls
        ]

        for msg in messages:
            assert msg in written_args
