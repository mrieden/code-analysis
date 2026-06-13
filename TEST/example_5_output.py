import abc
from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

FILE_PATH = "p.txt"


@runtime_checkable
class IValidator(Protocol):
    """Validate a string according to custom rules."""

    def validate(self, data: str) -> bool:
        ...


@runtime_checkable
class IConverter(Protocol):
    """Convert a value to a specific type."""

    def convert(self, value: Any) -> Any:
        ...


@runtime_checkable
class IPersistence(Protocol):
    """Persist and retrieve values."""

    def save(self, value: Any) -> None:
        ...

    def read(self) -> str:
        ...


@runtime_checkable
class IPresenter(Protocol):
    """Present data to the user."""

    def echo(self, data: str) -> None:
        ...


class PalindromeValidator:
    """Check if a string is a palindrome."""

    def validate(self, data: str) -> bool:
        """Return True if *data* reads the same forwards and backwards."""
        length = len(data)
        for i in range(length):
            for j in range(length):
                if i + j == length - 1 and data[i] != data[j]:
                    return False
        return True


class XConverter:
    """Convert value to string."""

    def convert(self, value: Any) -> str:
        """Return *value* as a string."""
        return str(value)


class YConverter:
    """Convert value to int."""

    def convert(self, value: Any) -> int:
        """Return *value* as an int."""
        return int(value)


class ZConverter:
    """Convert value to bool."""

    def convert(self, value: Any) -> bool:
        """Return *value* as a bool."""
        return bool(value)


class IdentityConverter:
    """Return value unchanged."""

    def convert(self, value: Any) -> Any:
        """Return *value* unchanged."""
        return value


class FilePersistence:
    """Append values to a file and read its contents."""

    def __init__(self, path: str = FILE_PATH) -> None:
        self._path = path

    def save(self, value: Any) -> None:
        """Append *value* to the file."""
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(str(value))

    def read(self) -> str:
        """Read and return the entire file contents."""
        with open(self._path, "r", encoding="utf-8") as f:
            return f.read()


class ConsolePresenter:
    """Print data to the console."""

    def echo(self, data: str) -> None:
        """Print *data* to stdout."""
        print(data)


class ConverterFactory:
    """Factory that creates converters based on a mode string."""

    _strategy_map: dict[str, Callable[[], IConverter]] = {
        "x": XConverter,
        "y": YConverter,
        "z": ZConverter,
    }

    @classmethod
    def create(cls, mode: str) -> IConverter:
        """Return a converter instance for *mode* or an identity converter."""
        return cls._strategy_map.get(mode, IdentityConverter)()


@dataclass(frozen=True)
class CheckerConfig:
    """Configuration for assembling a CheckerCoordinator."""

    data: str
    mode: str
    validator: IValidator = PalindromeValidator()
    converter_factory: Callable[[str], IConverter] = ConverterFactory.create
    persistence: IPersistence = FilePersistence()
    presenter: IPresenter = ConsolePresenter()


class ValidatorService:
    """Service responsible for validating data."""

    def __init__(self, validator: IValidator) -> None:
        self._validator = validator

    def validate(self, data: str) -> bool:
        """Validate *data* using the injected validator."""
        return self._validator.validate(data)


class ConverterService:
    """Service responsible for converting values."""

    def __init__(self, factory: Callable[[str], IConverter], mode: str) -> None:
        self._converter = factory(mode)

    def convert(self, value: Any) -> Any:
        """Convert *value* using the selected converter."""
        return self._converter.convert(value)


class PersistenceService:
    """Service responsible for persisting and retrieving values."""

    def __init__(self, persistence: IPersistence) -> None:
        self._persistence = persistence

    def save(self, value: Any) -> None:
        """Persist *value*."""
        self._persistence.save(value)

    def read(self) -> str:
        """Read persisted data."""
        return self._persistence.read()


class PresenterService:
    """Service responsible for presenting data."""

    def __init__(self, presenter: IPresenter) -> None:
        self._presenter = presenter

    def echo(self, data: str) -> None:
        """Present *data* to the user."""
        self._presenter.echo(data)


class CheckerCoordinator:
    """Facade that coordinates validation, conversion, persistence, and presentation."""

    def __init__(self, config: CheckerConfig) -> None:
        self._data = config.data
        self._validator_service = ValidatorService(config.validator)
        self._converter_service = ConverterService(config.converter_factory, config.mode)
        self._persistence_service = PersistenceService(config.persistence)
        self._presenter_service = PresenterService(config.presenter)

    def check(self) -> bool:
        """Validate the stored string."""
        return self._validator_service.validate(self._data)

    def conv(self, value: Any) -> Any:
        """Convert a value using the selected converter."""
        return self._converter_service.convert(value)

    def save(self, value: Any) -> None:
        """Persist a value."""
        self._persistence_service.save(value)

    def read(self) -> str:
        """Read persisted data."""
        return self._persistence_service.read()

    def echo(self) -> None:
        """Present the stored string."""
        self._presenter_service.echo(self._data)