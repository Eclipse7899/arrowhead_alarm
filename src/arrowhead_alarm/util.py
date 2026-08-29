"""Utility functions for Arrowhead alarm integration."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


@dataclass
class LoginCredentials:
    """Credentials for the alarm panel connection."""

    username: str
    password: str

    def __post_init__(self) -> None:
        """Validate credentials after initialization.

        Raises:
            ValueError: If username or password is empty.
        """
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


@dataclass
class _Subscription(Generic[_T]):
    """A subscription to a publisher."""
    callback: Callable[[_T], None]
    active: bool = field(default=True)

class Publisher(Generic[_T]):
    """A _publisher that notifies subscribers of changes."""

    def __init__(self) -> None:
        """Initialize the Publisher."""
        self._subscribers: dict[
            Callable[[_T], None],
            _Subscription[_T],
        ] = {}

    def subscribe(self, callback: Callable[[_T], None]) -> None:
        """Subscribe to changes."""
        if callback not in self._subscribers:
            self._subscribers[callback] = _Subscription(callback)

    def unsubscribe(self, callback: Callable[[_T], None]) -> None:
        """Unsubscribe from changes."""
        if callback in self._subscribers:
            self._subscribers[callback].active = False
            del self._subscribers[callback]

    def dispatch(self, data: _T) -> None:
        """Notify subscribers of a change."""
        snapshot = self._subscribers.copy()
        for subscription in snapshot.values():
            if subscription.active:
                subscription.callback(data)
