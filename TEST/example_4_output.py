import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


DEFAULT_FILE = Path("c.txt")


@runtime_checkable
class Calculator(Protocol):
    """Protocol for calculator objects."""

    def calculate(self) -> int:
        ...


@runtime_checkable
class Formatter(Protocol):
    """Protocol for formatter objects."""

    def format(self, value: int) -> str | int:
        ...


@runtime_checkable
class Persistable(Protocol):
    """Protocol for persistence objects."""

    def persist(self, value: int) -> None:
        ...

    def read(self) -> str:
        ...


@runtime_checkable
class Displayable(Protocol):
    """Protocol for displayable objects."""

    def show(self) -> None:
        ...


class FibonacciCalculator:
    """Calculate the nth Fibonacci number."""

    def __init__(self, n: int) -> None:
        self.n = n

    def _fib(self, k: int) -> int:
        if k < 2:
            return k
        return self._fib(k - 1) + self._fib(k - 2)

    def calculate(self) -> int:
        """Return the Fibonacci number for the configured n."""
        return self._fib(self.n)


class StringFormatter:
    """Return the integer as a decimal string."""

    def format(self, value: int) -> str:
        """Return the decimal string representation of the integer."""
        return str(value)


class HexFormatter:
    """Return the integer formatted as hexadecimal."""

    def format(self, value: int) -> str:
        """Return the hexadecimal string representation of the integer."""
        return hex(value)


class BinaryFormatter:
    """Return the integer formatted as binary."""

    def format(self, value: int) -> str:
        """Return the binary string representation of the integer."""
        return bin(value)


class FilePersistence:
    """Handle persistence of values to a text file."""

    def __init__(self, file_path: Path = DEFAULT_FILE) -> None:
        self.file_path = file_path

    def persist(self, value: int) -> None:
        """Append the string representation of value to the configured file."""
        with self.file_path.open("a", encoding="utf-8") as f:
            f.write(str(value))

    def read(self) -> str:
        """Read and return the entire contents of the configured file."""
        with self.file_path.open("r", encoding="utf-8") as f:
            return f.read()


class ConsoleViewer:
    """Display information on the console."""

    def __init__(self, message: str) -> None:
        self.message = message

    def show(self) -> None:
        """Print the configured message to the console."""
        print(self.message)


class CalculationService:
    """Service responsible for performing calculations."""

    def __init__(self, calculator: Calculator) -> None:
        self.calculator = calculator

    def execute(self) -> int:
        """Execute the calculation and return the result."""
        return self.calculator.calculate()


class FormattingService:
    """Service responsible for formatting calculation results."""

    def __init__(self, formatter: Formatter) -> None:
        self.formatter = formatter

    def apply(self, value: int) -> str | int:
        """Format the given integer value."""
        return self.formatter.format(value)


class PersistenceService:
    """Service responsible for persisting and retrieving data."""

    def __init__(self, persistor: Persistable) -> None:
        self.persistor = persistor

    def store(self, value: int) -> None:
        """Persist the integer value."""
        self.persistor.persist(value)

    def retrieve(self) -> str:
        """Retrieve persisted data."""
        return self.persistor.read()


class DisplayService:
    """Service responsible for displaying messages."""

    def __init__(self, viewer: Displayable) -> None:
        self.viewer = viewer

    def present(self) -> None:
        """Delegate display to the viewer."""
        self.viewer.show()


@dataclass
class CalcOrchestrator:
    """Thin façade that coordinates calculation, formatting, persistence, and display."""

    calculation_service: CalculationService
    formatting_service: FormattingService
    persistence_service: PersistenceService
    display_service: DisplayService

    def run(self) -> str | int:
        """Orchestrate calculation, formatting, persistence and return formatted result."""
        result = self.calculation_service.execute()
        formatted = self.formatting_service.apply(result)
        self.persistence_service.store(result)
        return formatted

    def read_persisted(self) -> str:
        """Return persisted data from the persistence layer."""
        return self.persistence_service.retrieve()

    def display(self) -> None:
        """Delegate to the display service to show the message."""
        self.display_service.present()