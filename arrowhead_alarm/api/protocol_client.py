from abc import ABC, abstractmethod

from arrowhead_alarm import PanelVersion
from arrowhead_alarm.protocol import ProtocolMode


class ProtocolClient(ABC):
    """Base client for a specific ECI protocol mode."""

    mode: ProtocolMode

    @abstractmethod
    async def query_version(self) -> PanelVersion:
        ...

    @abstractmethod
    async def query_output(self, output_number: int) -> bool:
        ...

    @abstractmethod
    async def output_on(self, output_number: int) -> None:
        ...

    @abstractmethod
    async def output_off(self, output_number: int) -> None:
        ...

    @abstractmethod
    async def bypass_zone(self, zone_number: int) -> None:
        ...

    @abstractmethod
    async def unbypass_zone(self, zone_number: int) -> None:
        ...

    @abstractmethod
    async def cancel(self) -> None:
        ...

    @abstractmethod
    async def reboot(self) -> None:
        ...