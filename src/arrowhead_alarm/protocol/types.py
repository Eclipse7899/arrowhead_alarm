"""Type definitions, monads, and pipeline utilities for protocol handling."""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Callable,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
)

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")
_E = TypeVar("_E")
_F = TypeVar("_F")

Transformer: TypeAlias = Callable[[_T], _U]

class ResultBase(ABC, Generic[_T, _E]):
    """Abstract base class for Result types."""

    is_ok: bool

    @abstractmethod
    def bind(self, func: Callable[[_T], "Result[_U, _E]"]) -> "Result[_U, _E]":
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
    def bind(self, func: Callable[[_T], "Result[_U, _E]"]) -> "Result[_U, _E]":
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
    def bind(self, func: Callable[[_T], "Result[_U, _E]"]) -> "Result[_U, _E]":
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

    _transformer: Callable[[_T], "Result[_U, _E]"]

    def bind(self, other: Callable[[_U], "Result[_V, _E]"]) -> "ResultPipeline[_T, _V, _E]":
        """Bind the pipeline to another ResultTransformer.

        Args:
            other: A function that takes a value of type _U and returns a Result[_V, _E].

        Returns: A new ResultPipeline that applies the original result_transformer
        followed by the other result_transformer.

        """
        return ResultPipeline(lambda data: self._transformer(data).bind(other))

    def map(self, other: Transformer[_U, _V]) -> "ResultPipeline[_T, _V, _E]":
        """Map the value of the pipeline to a new value."""
        return ResultPipeline(lambda data: self._transformer(data).map(other))

    def map_error(self, other: Transformer[_E, _F]) -> "ResultPipeline[_T, _U, _F]":
        """Map the error of the pipeline to a new value."""
        return ResultPipeline(lambda data: self._transformer(data).map_error(other))

    def unwrap(self) -> Callable[[_T], "Result[_U, _E]"]:
        """Return the flattened ResultPipeline."""
        return self._transformer


class CollectionResultBase(ABC, Generic[_T]):
    """Base class for evaluation results."""

    is_done: bool

    @abstractmethod
    def bind(self, func: Transformer[_T, "CollectionResult[_U]"]) -> "CollectionResult[_U]":
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
        return func(self.value)

    @override
    def map(self, func: Transformer[_T, _U]) -> "CollectionResult[_U]":
        return Done(func(self.value))


@dataclass(frozen=True, slots=True)
class Waiting(CollectionResultBase[_T]):
    """Indicates that the evaluated resp is irrelevant."""

    is_done: Literal[False] = False

    @override
    def bind(self, func: Transformer[_T, "CollectionResult[_U]"]) -> "CollectionResult[_U]":
        return Waiting()

    @override
    def map(self, func: Transformer[_T, _U]) -> "CollectionResult[_U]":
        return Waiting()


CollectionResult: TypeAlias = Done[_T] | Waiting[_T]

Collector: TypeAlias = Callable[[_T], CollectionResult[_U]]


class CollectorPipeline(Generic[_T, _U]):
    """Represents a pipeline of evaluators."""

    def __init__(self, collector: Collector[_T, _U]) -> None:
        """Initialize the CollectorPipeline.

        Args:
            collector: The underlying collector function to execute.
        """
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

    def unwrap(self) -> Collector[_T, _U]:
        """Return the flattened _collector."""
        return self._collector


@dataclass
class CollectorContext(Generic[_T, _U]):
    """CollectorContext for a transformer."""

    data: _T
    original: _U

    @classmethod
    def of_value(cls, data: _T) -> "CollectorContext[_T, _T]":
        """Create a CollectorContext with a value."""
        return CollectorContext(data, data)

    def map(self, func: Callable[[_T], _V]) -> "CollectorContext[_V, _U]":
        """Map the original to a new value."""
        return CollectorContext(func(self.data), self.original)


@dataclass
class Command(Generic[_T]):
    """Represents a protocol command with its request data and response collector."""

    data: str
    collector: Collector[str, _T]
