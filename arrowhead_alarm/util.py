"""Utility functions for Arrowhead alarm integration."""

import asyncio
import logging
from asyncio import Task
from typing import Any, TypeVar

from arrowhead_alarm.protocol import VersionInfo

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
