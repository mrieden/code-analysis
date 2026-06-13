import abc
from pathlib import Path
from typing import List, Protocol, runtime_checkable


DEFAULT_FILE_PATH = Path("t.txt")


@runtime_checkable
class ProfitCalculatorProtocol(Protocol):
    """Protocol for profit calculation."""

    def max_profit(self) -> float:
        ...


@runtime_checkable
class PersistenceProtocol(Protocol):
    """Protocol for persistence operations."""

    def save(self, value: str) -> None:
        ...

    def load(self) -> str:
        ...


class ProfitCalculator:
    """Calculate maximum profit from a list of prices."""

    def __init__(self, prices: List[float]) -> None:
        self._prices = prices

    def max_profit(self) -> float:
        """Return the greatest difference between a later higher price and an earlier lower price."""
        best = 0.0
        for i in range(len(self._prices)):
            for j in range(i + 1, len(self._prices)):
                diff = self._prices[j] - self._prices[i]
                if diff > best:
                    best = diff
        return best

    def show_prices(self) -> None:
        """Print the stored price list."""
        print(self._prices)


class CurrencyFormatter(Protocol):
    """Strategy interface for formatting monetary values."""

    def format(self, value: float) -> str:
        ...


class USDFormatter:
    """Format values as US dollars."""

    def format(self, value: float) -> str:
        return f"${value}"


class EURFormatter:
    """Format values as euros."""

    def format(self, value: float) -> str:
        return f"{value}E"


class GBPFormatter:
    """Format values as British pounds."""

    def format(self, value: float) -> str:
        return f"{value}P"


class TradePersistence:
    """Handle saving to and loading from a persistent text file."""

    def __init__(self, file_path: Path = DEFAULT_FILE_PATH) -> None:
        self._file_path = file_path

    def save(self, value: str) -> None:
        """Append a string representation of *value* to the file."""
        with self._file_path.open("a", encoding="utf-8") as f:
            f.write(value)

    def load(self) -> str:
        """Read the entire contents of the file."""
        return self._file_path.read_text(encoding="utf-8")


class Trader:
    """Facade that composes profit calculation, currency formatting, and persistence."""

    def __init__(
        self,
        calculator: ProfitCalculatorProtocol,
        formatter: CurrencyFormatter,
        persistence: PersistenceProtocol | None = None,
    ) -> None:
        self._calculator = calculator
        self._formatter = formatter
        self._persistence = persistence
        if self._persistence is None:
            raise ValueError("Persistence implementation must be provided.")

    def profit(self) -> float:
        """Delegate to ProfitCalculator to compute maximum profit."""
        return self._calculator.max_profit()

    def tag(self, value: float) -> str:
        """Format *value* using the injected CurrencyFormatter."""
        return self._formatter.format(value)

    def save(self, value: str) -> None:
        """Persist *value* using the injected persistence implementation."""
        self._persistence.save(value)

    def load(self) -> str:
        """Load persisted data using the injected persistence implementation."""
        return self._persistence.load()

    def show(self) -> None:
        """Display the stored price list."""
        if hasattr(self._calculator, "show_prices"):
            self._calculator.show_prices()