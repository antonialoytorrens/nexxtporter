"""Export the raw nametable binary (960 bytes) from an NSS file."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nexxtporter.exporters.base import BaseExporter
from nexxtporter.utils import parse_rle_binary, write_binary_file

if TYPE_CHECKING:
    from nexxtporter.config import ExportNametableConfig
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import RGBLookupRegistry

_NAMETABLE_TOKEN = "NameTable"


class NametableExporter(BaseExporter):
    """Writes the full 960-byte nametable to a binary file."""

    def __init__(
        self, log: Logger, nss_source: str, config: ExportNametableConfig
    ) -> None:
        super().__init__(log, nss_source)
        self._config = config

    def export(self, tokens: dict[str, str], rgb_registry: RGBLookupRegistry) -> None:
        cfg = self._config

        if _NAMETABLE_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}' has no '{_NAMETABLE_TOKEN}' token — "
                f"cannot export nametable to '{cfg.target_file}'"
            )
            return

        data = parse_rle_binary(
            self._log, self._nss_source, _NAMETABLE_TOKEN, tokens[_NAMETABLE_TOKEN]
        )

        self._log.log(f"Writing nametable to '{cfg.target_file}'")
        write_binary_file(self._log, Path(cfg.target_file), data, 0, len(data))
