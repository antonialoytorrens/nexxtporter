"""NSSFile: loads a Nexxt save file and runs all configured export operations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nexxtporter.exporters.bitmap_exporter import BitmapExporter
from nexxtporter.exporters.chr_exporter import CHRExporter
from nexxtporter.exporters.nametable_attributes_exporter import NametableAttributesExporter
from nexxtporter.exporters.nametable_bitmap_exporter import NametableBitmapExporter
from nexxtporter.exporters.nametable_exporter import NametableExporter
from nexxtporter.exporters.palette_exporter import PaletteExporter

if TYPE_CHECKING:
    from nexxtporter.config import NSSConfig
    from nexxtporter.exporters.base import BaseExporter
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import RGBLookupRegistry


class NSSFile:
    """Represents one Nexxt NSS file with all its configured export operations.

    NSS files store data as ``key=value`` text lines.  Binary data values use
    a run-length encoded hex format decoded by ``utils.parse_rle_binary``.
    """

    def __init__(
        self,
        log: Logger,
        config: NSSConfig,
        rgb_registry: RGBLookupRegistry,
    ) -> None:
        self._log = log
        self._config = config
        self._rgb_registry = rgb_registry
        self._exporters: list[BaseExporter] = self._build_exporters()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def process(self) -> None:
        """Parse the NSS file and run every configured exporter."""
        source = self._config.source_file
        if not source or not source.strip():
            self._log.log_error("NSSConfig has a missing or empty SourceFile")
            return

        self._log.log(f"Opening NSS file: {source}")
        try:
            tokens = self._parse_tokens(Path(source))
        except OSError as e:
            self._log.log_error(f"Error reading NSS file '{source}'", e)
            return

        self._log.log(
            f"Finished parsing '{source}' — found {len(tokens)} tokens"
        )

        for exporter in self._exporters:
            exporter.export(tokens, self._rgb_registry)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_tokens(self, path: Path) -> dict[str, str]:
        """Read the NSS file and return a ``{key: value}`` dictionary."""
        tokens: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                tokens[key] = value
        return tokens

    def _build_exporters(self) -> list[BaseExporter]:
        """Instantiate one exporter object per configured export operation."""
        cfg = self._config
        source = cfg.source_file
        exporters: list[BaseExporter] = []

        for c in cfg.export_chr:
            exporters.append(CHRExporter(self._log, source, c))
        for c in cfg.export_palette:
            exporters.append(PaletteExporter(self._log, source, c))
        for c in cfg.export_nametable:
            exporters.append(NametableExporter(self._log, source, c))
        for c in cfg.export_nametable_attributes:
            exporters.append(NametableAttributesExporter(self._log, source, c))
        for c in cfg.export_bitmap:
            exporters.append(BitmapExporter(self._log, source, c))
        for c in cfg.export_nametable_bitmap:
            exporters.append(NametableBitmapExporter(self._log, source, c))

        return exporters
