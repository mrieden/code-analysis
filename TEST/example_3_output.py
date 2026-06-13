from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, runtime_checkable

FILE_NAME = "r.txt"


@runtime_checkable
class ReportCalculatorProtocol(Protocol):
    """Protocol for calculating a report total."""

    def total(self, data: List[float]) -> float:
        ...


@runtime_checkable
class ReportPersistenceProtocol(Protocol):
    """Protocol for persisting a report total."""

    def save(self, total: float) -> None:
        ...


@runtime_checkable
class ReportPresenterProtocol(Protocol):
    """Protocol for presenting a report total."""

    def show(self, total: float) -> None:
        ...


class ReportCalculator:
    """Concrete calculator that sums numeric data."""

    def total(self, data: List[float]) -> float:
        return sum(data)


class ReportPersistence:
    """Concrete persistence that writes the total to a file."""

    def __init__(self, file_name: str = FILE_NAME) -> None:
        self._file_name = file_name

    def save(self, total: float) -> None:
        try:
            with open(self._file_name, "w", encoding="utf-8") as f:
                f.write(str(total))
        except OSError as exc:
            raise IOError(f"Failed to write report to {self._file_name}") from exc


class ReportPresenter:
    """Concrete presenter that prints the total to stdout."""

    def show(self, total: float) -> None:
        print(total)


class Report:
    """Aggregates data and delegates responsibilities to collaborators."""

    def __init__(
        self,
        data: List[float],
        calculator: ReportCalculatorProtocol = ReportCalculator(),
        persistence: ReportPersistenceProtocol = ReportPersistence(),
        presenter: ReportPresenterProtocol = ReportPresenter(),
    ) -> None:
        """Initialize Report with data and optional collaborators."""
        self.data: List[float] = data
        self._calculator: ReportCalculatorProtocol = calculator
        self._persistence: ReportPersistenceProtocol = persistence
        self._presenter: ReportPresenterProtocol = presenter

    def set_calculator(self, calculator: ReportCalculatorProtocol) -> None:
        """Inject a custom calculator."""
        self._calculator = calculator

    def set_persistence(self, persistence: ReportPersistenceProtocol) -> None:
        """Inject a custom persistence mechanism."""
        self._persistence = persistence

    def set_presenter(self, presenter: ReportPresenterProtocol) -> None:
        """Inject a custom presenter."""
        self._presenter = presenter

    def total(self) -> float:
        """Calculate the total of the report data."""
        return self._calculator.total(self.data)

    def save(self) -> None:
        """Persist the report total using the configured persistence."""
        self._persistence.save(self.total())

    def show(self) -> None:
        """Display the report total using the configured presenter."""
        self._presenter.show(self.total())