"""Abstract base class for all export operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import RGBLookupRegistry


class BaseExporter(ABC):
    """Common interface for every export operation.

    Subclasses are initialised with a logger, the path of the source NSS file
    (for error messages), and their specific configuration object.  The
    ``export`` method does the actual work.
    """

    def __init__(self, log: Logger, nss_source: str) -> None:
        self._log = log
        self._nss_source = nss_source

    @abstractmethod
    def export(
        self,
        tokens: dict[str, str],
        rgb_registry: RGBLookupRegistry,
    ) -> None:
        """Perform the export using the parsed NSS *tokens*.

        Args:
            tokens: Key-value pairs parsed from the NSS file.
            rgb_registry: Registry of available RGB lookup tables.
        """
