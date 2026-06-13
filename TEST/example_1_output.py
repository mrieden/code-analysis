import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Protocol


LOG_FILE = Path("log.txt")
DATA_FILE = Path("data.txt")


class IProcessor(Protocol):
    """Interface for processing data collections."""

    def process(self, data: List[Any]) -> List[Any]:
        ...


class IRenderer(Protocol):
    """Interface for rendering data into various formats."""

    def render(self, data: Any) -> str:
        ...


class ILogger(Protocol):
    """Interface for persisting log entries."""

    def write(self, entry: Any) -> None:
        ...


class IFetcher(Protocol):
    """Interface for retrieving raw data."""

    def fetch(self) -> str:
        ...


class INotifier(Protocol):
    """Interface for notifying about completed operations."""

    def notify(self, data: List[Any]) -> None:
        ...


class DataProcessor:
    """Detect duplicate elements in a list with O(n) complexity."""

    def process(self, data: List[Any]) -> List[Any]:
        """Return a list of duplicate elements found in *data*."""
        seen: set[Any] = set()
        duplicates: List[Any] = []
        for item in data:
            if item in seen:
                duplicates.append(item)
            else:
                seen.add(item)
        return duplicates


class JsonRenderer:
    """Render data as a JSON‑like string."""

    def render(self, data: Any) -> str:
        """Return a JSON‑like string representation of *data*."""
        return str(data)


class CsvRenderer:
    """Render data as a comma‑separated values string."""

    def render(self, data: Any) -> str:
        """Return a CSV string representation of *data*."""
        return ",".join(map(str, data))


class HtmlRenderer:
    """Render data wrapped in an HTML paragraph."""

    def render(self, data: Any) -> str:
        """Return *data* wrapped in an HTML <p> tag."""
        return f"<p>{data}</p>"


class FileLogger:
    """Append log entries to a file."""

    def __init__(
        self,
        file_path: Path = LOG_FILE,
        logger: logging.Logger | None = None,
        handler: logging.Handler | None = None,
    ) -> None:
        """
        Initialise the logger.

        If *logger* is provided it is used; otherwise a new logger named
        ``DataManagerLogger`` is created. An optional *handler* can be supplied;
        if omitted a ``FileHandler`` writing to *file_path* is attached.
        """
        if logger is not None:
            self._logger = logger
        else:
            self._logger = logging.getLogger("DataManagerLogger")
            self._logger.setLevel(logging.INFO)

        if handler is None:
            handler = logging.FileHandler(file_path, mode="a", encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s - %(message)s")
            handler.setFormatter(formatter)

        if not any(isinstance(h, type(handler)) for h in self._logger.handlers):
            self._logger.addHandler(handler)

    def write(self, entry: Any) -> None:
        """Log the string representation of *entry* at INFO level."""
        self._logger.info(str(entry))


class DataFetcher:
    """Read raw data from a predefined file."""

    def __init__(self, file_path: Path = DATA_FILE) -> None:
        """Initialise the fetcher with *file_path*."""
        self._file_path = file_path

    def fetch(self) -> str:
        """Read and return the entire contents of the configured file."""
        with self._file_path.open("r", encoding="utf-8") as f:
            return f.read()


class LoggerNotifier:
    """Notify completion using the logging system."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        handler: logging.Handler | None = None,
    ) -> None:
        """
        Initialise the notifier.

        If *logger* is supplied it is used; otherwise a new logger named
        ``DataManagerNotifier`` is created. An optional *handler* can be
        supplied; if omitted a ``StreamHandler`` is attached.
        """
        if logger is not None:
            self._logger = logger
        else:
            self._logger = logging.getLogger("DataManagerNotifier")
            self._logger.setLevel(logging.INFO)

        if handler is None:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(message)s")
            handler.setFormatter(formatter)

        if not any(isinstance(h, type(handler)) for h in self._logger.handlers):
            self._logger.addHandler(handler)

    def notify(self, data: List[Any]) -> None:
        """Log a completion message containing *data*."""
        self._logger.info(f"done {data}")


@dataclass(frozen=True)
class DataManagerConfig:
    """Configuration holder for DataManager collaborators."""

    processor: IProcessor
    renderer: IRenderer
    logger: ILogger
    fetcher: IFetcher
    notifier: INotifier


class DataManager:
    """Facade that coordinates processing, rendering, logging, fetching, and notifying."""

    def __init__(self, data: List[Any], config: DataManagerConfig) -> None:
        """
        Initialise the manager with *data* and a *config* containing collaborators.
        """
        self._data = data
        self._processor = config.processor
        self._renderer = config.renderer
        self._logger = config.logger
        self._fetcher = config.fetcher
        self._notifier = config.notifier

    def process(self) -> List[Any]:
        """Return duplicate elements found in the managed data."""
        return self._processor.process(self._data)

    def render(self, payload: Any) -> str:
        """Render the given *payload* using the configured renderer."""
        return self._renderer.render(payload)

    def save(self, payload: Any) -> None:
        """Persist the rendered *payload* via the configured logger."""
        self._logger.write(payload)

    def fetch(self) -> str:
        """Retrieve raw data from the configured source."""
        return self._fetcher.fetch()

    def notify(self) -> None:
        """Notify completion using the configured notifier."""
        self._notifier.notify(self._data)