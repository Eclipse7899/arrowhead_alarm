"""Utility functions for Arrowhead alarm integration."""

import asyncio
import logging
from asyncio import Task
from dataclasses import dataclass
from typing import Any, TypeVar, Generic, Callable

from .protocol.models import VersionInfo

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


async def cancel_task(task: Task[Any] | None) -> None:
    """Cancel the given asyncio task if it is not already done.

    Args:
        task: The asyncio task to cancel.

    """
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.warning("Error while cancelling task: %s", type(e).__name__)


def is_mode_4_supported(version: VersionInfo) -> bool:
    """Check if Protocol Mode 4 is supported for the given firmware version.

    Args:
        version: Firmware version.

    Returns: True if Protocol Mode 4 is supported, False otherwise.

    """
    return version >= VersionInfo(10, 3, 50)


@dataclass
class LoginCredentials:
    """Credentials for the alarm panel connection."""
    username: str
    password: str

    def __post_init__(self):
        if not self.username:
            raise ValueError("Username cannot be empty.")
        if not self.password:
            raise ValueError("Password cannot be empty.")


class ToggleEvent:
    """An asyncio-compatible event that can be set or cleared."""

    def __init__(self) -> None:
        """Initialize the ToggleEvent."""
        self._set_event = asyncio.Event()
        self._clear_event = asyncio.Event()
        self._clear_event.set()

    def is_set(self) -> bool:
        """Check if the event is set.

        Returns: True if the event is set, False otherwise.

        """
        return self._set_event.is_set()

    def is_clear(self) -> bool:
        """Check if the event is clear.

        Returns: True if the event is clear, False otherwise.

        """
        return self._clear_event.is_set()

    def set(self) -> None:
        """Set the event."""
        self._set_event.set()
        self._clear_event.clear()

    def clear(self) -> None:
        """Clear the event."""
        self._set_event.clear()
        self._clear_event.set()

    async def wait_until_set(self) -> None:
        """Wait until the event is set."""
        await self._set_event.wait()

    async def wait_until_clear(self) -> None:
        """Wait until the event is clear."""
        await self._clear_event.wait()


class Publisher(Generic[_T]):
    """A _publisher that notifies subscribers of changes."""

    def __init__(self) -> None:
        """Initialize the Publisher."""
        self._subscribers: set[Callable[[_T], None]] = set()

    def subscribe(self, callback: Callable[[_T], None]) -> None:
        """Subscribe to changes."""
        self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable[[_T], None]) -> None:
        """Unsubscribe from changes."""
        self._subscribers.discard(callback)

    def dispatch(self, data: _T) -> None:
        """Notify subscribers of a change."""
        for subscriber in self._subscribers:
            subscriber(data)
