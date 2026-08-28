"""Types for Arrowhead alarm integration."""
import asyncio
from dataclasses import dataclass
from typing import (
    Callable,
    Generic,
    TypeVar,
)

from arrowhead_alarm.protocol import CollectionResult

_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")
_E = TypeVar("_E")
_F = TypeVar("_F")


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
