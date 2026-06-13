import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Protocol, Callable, runtime_checkable, Optional


DEFAULT_FILE_PATH = "s.txt"


@runtime_checkable
class Averager(Protocol):
    """Protocol for calculating cumulative averages."""

    def averages(self, data: List[float]) -> List[float]:
        ...


@runtime_checkable
class Labeler(Protocol):
    """Protocol for converting a value to a labeled representation."""

    def label(self, value: float) -> object:
        ...


class StringLabeler:
    """Return the value as a string."""

    def label(self, value: float) -> str:
        return str(value)


class RoundedLabeler:
    """Return the value rounded to two decimal places."""

    def label(self, value: float) -> float:
        return round(value, 2)


class IntLabeler:
    """Return the value as an integer."""

    def label(self, value: float) -> int:
        return int(value)


class IdentityLabeler:
    """Return the value unchanged."""

    def label(self, value: float) -> float:
        return value


class LabelKind(Enum):
    STRING = auto()
    ROUNDED = auto()
    INT = auto()
    IDENTITY = auto()


class LabelerFactory:
    """Factory that creates Labeler instances based on a LabelKind."""

    _creators: dict[LabelKind, Callable[[], Labeler]] = {
        LabelKind.STRING: StringLabeler,
        LabelKind.ROUNDED: RoundedLabeler,
        LabelKind.INT: IntLabeler,
        LabelKind.IDENTITY: IdentityLabeler,
    }

    @classmethod
    def create(cls, kind: LabelKind) -> Labeler:
        """Return a Labeler instance for the given kind."""
        creator = cls._creators.get(kind, IdentityLabeler)
        return creator()


@runtime_checkable
class Persistable(Protocol):
    """Protocol for persisting and retrieving values."""

    def store(self, value: object) -> None:
        ...

    def fetch(self) -> str:
        ...


class StatsRepository:
    """File‑based repository for storing and fetching values."""

    def __init__(self, file_path: str = DEFAULT_FILE_PATH) -> None:
        self._file_path = file_path
        # Ensure the file exists
        open(self._file_path, "a").close()

    def store(self, value: object) -> None:
        with open(self._file_path, "a", encoding="utf-8") as f:
            f.write(str(value))

    def fetch(self) -> str:
        with open(self._file_path, "r", encoding="utf-8") as f:
            return f.read()


@runtime_checkable
class Traceable(Protocol):
    """Protocol for tracing internal data."""

    def trace(self) -> None:
        ...


class StatsTracer:
    """Utility to trace a list of numbers."""

    def __init__(self, data: List[float]) -> None:
        self._data = data

    def trace(self) -> None:
        print(self._data)


@dataclass
class StatsConfig:
    """Configuration for Stats composition."""

    data: List[float]
    label_kind: LabelKind = LabelKind.STRING
    file_path: str = DEFAULT_FILE_PATH


class Stats(Averager, Labeler, Persistable, Traceable):
    """Facade that delegates statistical operations to dedicated collaborators."""

    def __init__(
        self,
        config: StatsConfig,
        labeler_factory: Callable[[LabelKind], Labeler] = LabelerFactory.create,
    ) -> None:
        self._data = config.data
        self._averager = RunningAverageCalculator()
        self._labeler = labeler_factory(config.label_kind)
        self._repository = StatsRepository(config.file_path)
        self._tracer = StatsTracer(self._data)

    def averages(self, data: Optional[List[float]] = None) -> List[float]:
        """Return running averages of the provided data or the stored data."""
        target = data if data is not None else self._data
        return self._averager.averages(target)

    def label(self, value: float) -> object:
        """Convert a value according to the configured labeling strategy."""
        return self._labeler.label(value)

    def store(self, value: object) -> None:
        """Persist a value to the underlying repository."""
        self._repository.store(value)

    def fetch(self) -> str:
        """Retrieve all persisted values from the repository."""
        return self._repository.fetch()

    def trace(self) -> None:
        """Print the internal data for debugging purposes."""
        self._tracer.trace()


class RunningAverageCalculator:
    """Calculate running averages in O(n) time."""

    def averages(self, data: List[float]) -> List[float]:
        out: List[float] = []
        total = 0.0
        for index, value in enumerate(data):
            total += value
            out.append(total / (index + 1))
        return out