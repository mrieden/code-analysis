import abc
from typing import Any, Iterable, List, Tuple, Set, Protocol


class ShapeStrategy(Protocol):
    """Strategy interface for converting iterables to a specific shape."""

    def convert(self, value: Iterable[Any]) -> Any:
        """Convert the given iterable to the desired shape."""
        ...


class ListStrategy:
    """Convert iterable to a list."""

    def convert(self, value: Iterable[Any]) -> List[Any]:
        """Return a list built from the given iterable."""
        return list(value)


class TupleStrategy:
    """Convert iterable to a tuple."""

    def convert(self, value: Iterable[Any]) -> Tuple[Any, ...]:
        """Return a tuple built from the given iterable."""
        return tuple(value)


class SetStrategy:
    """Convert iterable to a set."""

    def convert(self, value: Iterable[Any]) -> Set[Any]:
        """Return a set built from the given iterable."""
        return set(value)


class IdentityStrategy:
    """Return the value unchanged."""

    def convert(self, value: Iterable[Any]) -> Any:
        """Return the input iterable unchanged."""
        return value


class ShapeConverter:
    """Select and apply a shape conversion strategy based on mode."""

    _STRATEGIES = {
        "l": ListStrategy(),
        "t": TupleStrategy(),
        "s": SetStrategy(),
    }

    def __init__(self, mode: str) -> None:
        # Choose the appropriate strategy; default to identity if mode unknown
        self._strategy: ShapeStrategy = self._STRATEGIES.get(mode, IdentityStrategy())

    def shape(self, value: Iterable[Any]) -> Any:
        """Convert the iterable using the configured strategy."""
        return self._strategy.convert(value)


class SetOperations:
    """Provide set‑related operations."""

    @staticmethod
    def common(a: Iterable[Any], b: Iterable[Any]) -> List[Any]:
        """Return the list of common elements between two iterables."""
        return list(set(a).intersection(b))


class FilePersistence:
    """Handle simple file persistence."""

    _FILE_PATH = "i.txt"

    def write(self, value: Any) -> None:
        """Append the string representation of value to the file."""
        with open(self._FILE_PATH, "a", encoding="utf-8") as f:
            f.write(str(value))

    def read(self) -> str:
        """Read and return the entire contents of the file."""
        with open(self._FILE_PATH, "r", encoding="utf-8") as f:
            return f.read()


class SetOps:
    """Facade that composes set operations, shape conversion, and persistence."""

    def __init__(self, first_iterable: Iterable[Any], second_iterable: Iterable[Any], mode: str) -> None:
        # Store the original iterables for later operations
        self._first_iterable = first_iterable
        self._second_iterable = second_iterable
        # Initialize strategy and persistence components
        self._shape_converter = ShapeConverter(mode)
        self._persistence = FilePersistence()

    def common(self) -> List[Any]:
        """Return common elements between the two stored iterables."""
        return SetOperations.common(self._first_iterable, self._second_iterable)

    def shape(self, value: Iterable[Any]) -> Any:
        """Convert the given iterable according to the configured mode."""
        return self._shape_converter.shape(value)

    def write(self, value: Any) -> None:
        """Persist the given value to the file."""
        self._persistence.write(value)

    def read(self) -> str:
        """Read persisted data from the file."""
        return self._persistence.read()

    def emit(self) -> None:
        """Print the stored iterables."""
        print(self._first_iterable, self._second_iterable)