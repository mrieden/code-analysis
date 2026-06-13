from __future__ import annotations

import abc
from typing import Protocol

# Constants for formatter selection
MODE_STRING: int = 1
MODE_HEX: int = 2
MODE_BIN: int = 3

# Mapping of mode constants to formatter classes (OCP)
FORMATTERS: dict[int, type[IFormatter]] = {
    MODE_STRING: lambda: StringFormatter(),
    MODE_HEX: lambda: HexFormatter(),
    MODE_BIN: lambda: BinFormatter(),
}


class ICalculator(Protocol):
    """Calculator protocol defining Fibonacci operations."""

    def run(self) -> int:
        """Execute the calculation and return the result as an int."""
        ...


class Calculator:
    """Performs Fibonacci calculations."""

    def __init__(self, n: int) -> None:
        self.n: int = n

    def _fib(self, k: int) -> int:
        """Iterative Fibonacci implementation with O(n) time and O(1) space."""
        if k < 2:
            return k
        a, b = 0, 1
        for _ in range(2, k + 1):
            a, b = b, a + b
        return b

    def run(self) -> int:
        """Calculate the Fibonacci number for the configured n."""
        return self._fib(self.n)


class IFormatter(Protocol):
    """Formatter protocol for converting integers to strings."""

    def format(self, value: int) -> str:
        ...


class StringFormatter:
    """Formats an integer as a decimal string."""

    def format(self, value: int) -> str:
        """Return the decimal string representation of the integer."""
        return str(value)


class HexFormatter:
    """Formats an integer as a hexadecimal string."""

    def format(self, value: int) -> str:
        """Return the hexadecimal string representation of the integer."""
        return hex(value)


class BinFormatter:
    """Formats an integer as a binary string."""

    def format(self, value: int) -> str:
        """Return the binary string representation of the integer."""
        return bin(value)


def get_formatter(mode: int) -> IFormatter:
    """Return an IFormatter based on the supplied mode constant.

    Supported modes:
        MODE_STRING – decimal string formatter
        MODE_HEX    – hexadecimal string formatter
        MODE_BIN    – binary string formatter
    """
    try:
        return FORMATTERS[mode]()
    except KeyError as exc:
        raise ValueError(f"Unsupported mode: {mode}") from exc


class IPersistence(Protocol):
    """Persistence protocol for writing and reading values."""

    def persist(self, value: int) -> None:
        ...

    def read(self) -> str:
        ...


class PersistenceHandler:
    """Handles persisting values to a file."""

    def __init__(self, file_path: str = "c.txt") -> None:
        self.file_path: str = file_path

    def persist(self, value: int) -> None:
        """Append the string representation of value to the configured file."""
        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(str(value))

    def read(self) -> str:
        """Return the full contents of the file as a string."""
        with open(self.file_path, "r", encoding="utf-8") as file:
            return file.read()


class UIHelper:
    """Utility class for displaying information."""

    @staticmethod
    def show(value: int) -> None:
        """Print the provided integer value."""
        print(value)