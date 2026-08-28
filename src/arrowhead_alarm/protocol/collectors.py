"""Module for resp collectors that process incoming resp and produce results."""

import asyncio
from typing import Callable, Generic, TypeVar

from .types import (
    CollectionResult,
    Collector,
    Done,
    Waiting,
)

_T = TypeVar("_T")
_U = TypeVar("_U")


class LineCountCollector(Generic[_U]):
    """A collector that collects a number of lines and returns them as a list."""

    def __init__(
        self,
        expected: int,
    ) -> None:
        """Initialize the LineCountCollector."""
        self.expected = expected
        self._lines: list[str] = []

    def collect(self, data: str) -> CollectionResult[list[str]]:
        """Collect incoming data and return the collected lines."""
        self._lines.append(data)
        if len(self._lines) < self.expected:
            return Waiting()
        else:
            return Done(self._lines)


class SlidingCollectorCompletion(Generic[_T, _U]):
    """A collector that debounces completion events within a sliding time window."""

    def __init__(
        self,
        evaluator: Collector[_T, _U],
        callback: Callable[[_U], None],
        window: float,
    ) -> None:
        """Initialize the SlidingCollectorCompletion.

        Args:
            evaluator: Collector function or callable that processes incoming items.
            callback: Callback function called with the completed value after window expires.
            window: Debounce window duration in seconds.
        """
        self._evaluator = evaluator
        self._callback = callback
        self._last_done: _U | None = None
        self._window_sec = window
        self._countdown_task: asyncio.Task | None = None

    async def _timer(self) -> None:
        try:
            await asyncio.sleep(self._window_sec)
            if self._last_done is not None:
                value = self._last_done
                self._last_done = None
                self._callback(value)

        except asyncio.CancelledError:
            raise

    def _reset_timer(self) -> None:
        if self._countdown_task is not None:
            self._countdown_task.cancel()
        self._countdown_task = asyncio.create_task(self._timer())

    def collect(self, data: _T) -> None:
        """Collect incoming data and reset the completion timer if done.

        Args:
            data: Incoming data item to process.
        """
        result = self._evaluator(data)

        match result:
            case Done(value):
                self._last_done = value
                self._reset_timer()
            case Waiting():
                pass
