"""Types for Arrowhead alarm integration."""
import asyncio
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntFlag
from typing import (
    Callable,
    Generic,
    TypeAlias,
    TypeVar,
    Literal,
)

if sys.version_info >= (3, 11):
    from typing import override
else:
    from typing_extensions import override

_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")
_E = TypeVar("_E")
_F = TypeVar("_F")

Transformer: TypeAlias = Callable[[_T], _U]
ResultTransformer: TypeAlias = Callable[[_T], "Result[_U, _E]"]


@dataclass
class UserPin:
    """User ID and PIN for arming/disarming."""

    user_id: int
    pin: int


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


class ArmingCapabilities(IntFlag):
    """Capabilities for arming the alarm panel."""

    NONE = 0
    INDIVIDUAL_AREA = 1 << 0
    USER_ID_AND_PIN = 1 << 1
    ONE_PUSH = 1 << 2

class DisarmingCapabilities(IntFlag):
    """Capabilities for disarming the alarm panel."""

    NONE = 0
    INDIVIDUAL_AREA_WITH_USER_PIN = 1 << 0
    USER_ID_AND_PIN = 1 << 1


@dataclass
class AlarmCapabilities:
    """Capabilities of the alarm panel."""

    all_zones_ready_status: bool = False
    arming: ArmingCapabilities = ArmingCapabilities.NONE
    disarming: DisarmingCapabilities = DisarmingCapabilities.NONE


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


class ResultBase(ABC, Generic[_T, _E]):
    """Abstract base class for Result types."""
    is_ok: bool
    @abstractmethod
    def bind(self, func: ResultTransformer[_T, _U, _E]) -> "Result[_U, _E]":
        """Bind the result to a function that returns a Result.

        Args:
            func: A function that takes a value and returns a Result.

        Returns: The Result returned by the function.

        """
        ...

    @abstractmethod
    def map_error(self, func: Transformer[_E, _F]) -> "Result[_T, _F]":
        """Bind the error to a function that returns a Result.

        Args:
            func: A function that takes an error and returns a Result.

        Returns: The Result returned by the function.

        """
        ...

    @abstractmethod
    def map(self, func: Transformer[_T, _U]) -> "Result[_U, _E]":
        """Map the result to a new Result.

        Args:
            func: A function that takes a value and returns a new value.

        Returns: A new Result instance with the mapped value.

        """
        ...


@dataclass(frozen=True, slots=True)
class Success(ResultBase[_T, _E], Generic[_T, _E]):
    """Represents a successful result with a value."""

    value: _T
    is_ok: Literal[True] = True

    @override
    def bind(self, func: ResultTransformer[_T, _U, _E]) -> "Result[_U, _E]":
        """Bind the success value to a function that returns a Result.

        Args:
            func: A function that takes the success value and returns a Result.

        Returns: The Result returned by the function.

        """
        return func(self.value)

    @override
    def map(self, func: Transformer[_T, _U]) -> "Result[_U, _E]":
        """Map the success value to a new Result.

        Args:
            func: A function that takes the success value and returns a new value.

        Returns: A new Success instance with the mapped value.

        """
        return Success(func(self.value))

    @override
    def map_error(self, func: Transformer[_E, _F]) -> "Result[_T, _F]":
        """Map the error to a new Result.

        Args:
            func: A function that takes the error value and returns a new Result.

        Returns: The original Success instance.

        """
        return Success(self.value)


@dataclass(frozen=True, slots=True)
class Failure(ResultBase[_T, _E], Generic[_T, _E]):
    """Represents a failed result with an error."""

    error: _E
    is_ok: Literal[False] = False

    @override
    def bind(self, func: ResultTransformer[_T, _U, _E]) -> "Result[_U, _E]":
        """Bind the failure to a function that returns a Result.

        Args:
            func: A function that takes a value and returns a Result.

        Returns: The original Failure instance.

        """
        return Failure(self.error)

    @override
    def map(self, func: Transformer[_T, _U]) -> "Result[_U, _E]":
        """Map the failure to a new Result.

        Args:
            func: A function that takes the failure value and returns a new value.

        Returns: A new Failure instance with the mapped value.

        """
        return Failure(self.error)

    @override
    def map_error(self, func: Transformer[_E, _F]) -> "Result[_T, _F]":
        """Map the error to a new Result.

        Args:
            func: A function that takes the error value and returns a new Result.

        Returns: A new Failure instance with the mapped error.

        """
        return Failure(func(self.error))


Result: TypeAlias = Success[_T, _E] | Failure[_T, _E]


@dataclass(frozen=True)
class ResultPipeline(Generic[_T, _U, _E]):
    """A flow of Result transformations."""

    _transformer: ResultTransformer[_T, _U, _E]

    def run_result(self, result: Result[_T, _E]) -> Result[_U, _E]:
        """Run the pipeline starting from a Result.

        Args:
            result: A Result instance to start the pipeline.
        """
        return result.bind(self._transformer)

    def bind(self, other: ResultTransformer[_U, _V, _E]) -> "ResultPipeline[_T, _V, _E]":
        """Chain another result_transformer function to the ResultPipeline.

        Args:
            other: A function that takes command of type _U and returns a Result[_V, _E].

        Returns: A new ResultPipeline that applies the original result_transformer
        followed by the other result_transformer.

        """
        return ResultPipeline(lambda data: self._transformer(data).bind(other))

    def map(self, other: Transformer[_U, _V]) -> "ResultPipeline[_T, _V, _E]":
        """Chain another result_transformer function to the ResultPipeline.

        Args:
            other: A function that takes command of type _U and returns a value of type _V.

        Returns: A new ResultPipeline that applies the original result_transformer
        followed by the other result_transformer.

        """
        return ResultPipeline(lambda data: self._transformer(data).map(other))

    def map_error(self, other: Transformer[_E, _F]) -> "ResultPipeline[_T, _U, _F]":
        """Chain another error result_transformer function to the ResultPipeline.

        Args:
            other: A function that takes an error of type _E and returns a Result[_T, _F].

        Returns: A new ResultPipeline that applies the original result_transformer
        followed by the other error result_transformer.

        """
        return ResultPipeline(lambda data: self._transformer(data).map_error(other))

    def flatten(self) -> ResultTransformer[_T, _U, _E]:
        """Return the flattened ResultPipeline."""
        return self._transformer

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

class CollectionResultBase(ABC, Generic[_T]):
    """Base class for evaluation results."""

    is_done: bool

    @abstractmethod
    def bind(
        self, func: Transformer[_T, "CollectionResult[_U]"]
    ) -> "CollectionResult[_U]":
        """Bind the result to a function that returns another result."""
        ...

    @abstractmethod
    def map(self, func: Transformer[_T, _U]) -> "CollectionResult[_U]":
        """Map the result to a new value."""
        ...


@dataclass(frozen=True, slots=True)
class Done(CollectionResultBase[_T]):
    """Indicates that the evaluated resp is complete."""

    value: _T
    is_done: Literal[True] = True

    @override
    def bind(self, func: Transformer[_T, "CollectionResult[_U]"]) -> "CollectionResult[_U]":
        """Bind the Done result to a function that returns another CollectionResult."""
        return func(self.value)

    @override
    def map(self, func: Transformer[_T, _U]) -> "CollectionResult[_U]":
        """Map the Done result to a new value."""
        return Done(func(self.value))


@dataclass(frozen=True, slots=True)
class Waiting(CollectionResultBase[_T]):
    """Indicates that the evaluated resp is irrelevant."""

    is_done: Literal[False] = False

    @override
    def bind(self, func: Transformer[_T, "CollectionResult[_U]"]) -> "CollectionResult[_U]":
        """Bind the Waiting result to a function that returns another CollectionResult."""
        return Waiting()

    @override
    def map(self, func: Transformer[_T, _U]) -> "CollectionResult[_U]":
        """Map the Waiting result to a new value."""
        return Waiting()

CollectionResult: TypeAlias = Done[_T] | Waiting[_T]

Collector: TypeAlias = Callable[[_T], CollectionResult[_U]]

class CollectorPipeline(Generic[_T, _U]):
    """Represents a pipeline of evaluators."""

    @classmethod
    def of_string(cls) -> "CollectorPipeline[str, str]":
        """Create an empty CollectorPipeline."""
        return CollectorPipeline(lambda data: Done(data))

    @classmethod
    def of_string_list(cls) -> "CollectorPipeline[list[str], list[str]]":
        """Create an empty CollectorPipeline for a list of strings."""
        return CollectorPipeline(lambda data: Done(data))

    def __init__(self, collector: Collector[_T, _U]) -> None:
        self._collector: Collector[_T, _U] = collector

    def bind(
        self,
        other: Collector[_U, _V],
    ) -> "CollectorPipeline[_T, _V]":
        """Chain the current _collector with another _collector."""
        return CollectorPipeline(lambda data: self._collector(data).bind(other))

    def map(
        self,
        func: Transformer[_U, _V],
    ) -> "CollectorPipeline[_T, _V]":
        """Map the current _collector's result to a new value."""
        return CollectorPipeline(lambda data: self._collector(data).map(func))

    def flatten(self) -> Collector[_T, _U]:
        """Return the flattened _collector."""
        return self._collector

