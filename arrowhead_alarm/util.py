"""Utility functions for Arrowhead alarm integration."""

import asyncio
import logging
from asyncio import Task
from typing import Any, Mapping, TypeVar

from arrowhead_alarm.types import (
    AlarmCapabilities,
    ArmingCapabilities,
    DisarmingCapabilities,
)
from arrowhead_alarm.protocol.models import ArmingMode, ProtocolMode, VersionInfo

_LOGGER = logging.getLogger(__name__)

T = TypeVar("_T")


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


def ensure_delimiter(message: str, delimiter: str) -> str:
    """Add the delimiter to the command if it is missing.

    Args:
        message: The command string.
        delimiter: The delimiter to add if missing.
    Returns: The command with the delimiter added if it was missing.

    """
    if not message.endswith(delimiter):
        return message + delimiter
    return message


def get_arming_keyword(mode: ArmingMode) -> str:
    """Return the arming cmd keyword for the given arming arming_mode.

    Args:
        mode (ArmingMode): The arming arming_mode.

    Returns:
        str: The corresponding arming cmd keyword.

    Raises:
        ValueError: If the arming arming_mode is unsupported.

    """
    match mode:
        case ArmingMode.AWAY:
            return "ARMAWAY"
        case ArmingMode.STAY:
            return "ARMSTAY"
        case _:
            raise ValueError(f"Unsupported arming arming_mode: {mode}")


def search_prefix(query: str, data: Mapping[str, T]) -> T | None:
    """Search for the first matching prefix of the query in the resp mapping.

    Args:
        query: String to search for prefixes within.
        data: The dictionary or mapping to search in.

    Returns:
        The value associated with the first found prefix, or None if no match is found.

    """
    prefix = ""
    for char in query:
        prefix += char
        if prefix in data:
            return data[prefix]
    return None


def get_mode_capabilites(mode: ProtocolMode) -> AlarmCapabilities:
    """Get the alarm capabilities based on the protocol arming_mode."""
    capabilities = AlarmCapabilities()
    match mode:
        case ProtocolMode.MODE_1:
            capabilities.all_zones_ready_status = True
            capabilities.arming = (
                ArmingCapabilities.USER_ID_AND_PIN | ArmingCapabilities.ONE_PUSH
            )
            capabilities.disarming = DisarmingCapabilities.USER_ID_AND_PIN
        case ProtocolMode.MODE_2:
            capabilities.all_zones_ready_status = False
            capabilities.arming = ArmingCapabilities.INDIVIDUAL_AREA
            capabilities.disarming = DisarmingCapabilities.INDIVIDUAL_AREA_WITH_USER_PIN
        case ProtocolMode.MODE_4:
            capabilities.all_zones_ready_status = False
            capabilities.arming = (
                ArmingCapabilities.INDIVIDUAL_AREA | ArmingCapabilities.USER_ID_AND_PIN
            )
            capabilities.disarming = DisarmingCapabilities.USER_ID_AND_PIN
        case _:
            raise NotImplementedError
    return capabilities


