"""Export palette data from an NSS file as ca65 assembly source code."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nexxtporter.exporters.base import BaseExporter
from nexxtporter.utils import format_byte_line, parse_rle_binary

if TYPE_CHECKING:
    from nexxtporter.config import ExportPaletteConfig
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import RGBLookupRegistry

_PALETTE_TOKEN = "Palette"
_BYTES_PER_ROW = 4   # 4 colour entries per .byte line
_ROWS_PER_SET  = 4   # 4 rows make one 16-byte palette set


class PaletteExporter(BaseExporter):
    """Writes one 16-byte palette set to a ca65 ``.inc`` file.

    A palette set consists of four 4-byte sub-palettes, each formatted as a
    separate ``.byte`` directive.  The output is optionally preceded by a
    ``.segment`` directive and a label.
    """

    def __init__(
        self, log: Logger, nss_source: str, config: ExportPaletteConfig
    ) -> None:
        super().__init__(log, nss_source)
        self._config = config

    def export(self, tokens: dict[str, str], rgb_registry: RGBLookupRegistry) -> None:
        cfg = self._config

        if _PALETTE_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}' has no '{_PALETTE_TOKEN}' token — "
                f"cannot export palette to '{cfg.target_file}'"
            )
            return

        palette_data = parse_rle_binary(
            self._log, self._nss_source, _PALETTE_TOKEN, tokens[_PALETTE_TOKEN]
        )

        self._log.log(
            f"Exporting palette set {cfg.source_sub_palette} to "
            f"'{cfg.target_file}' (append={cfg.target_append})"
        )

        lines = self._build_lines(palette_data)
        self._write_file(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_lines(self, palette_data: bytes) -> list[str]:
        cfg = self._config
        lines: list[str] = []

        if cfg.target_segment_name:
            lines.append(f'.segment "{cfg.target_segment_name}"')
        if cfg.target_variable_name:
            lines.append(f"{cfg.target_variable_name}:")

        base = cfg.source_sub_palette * 16
        for row in range(_ROWS_PER_SET):
            offset = base + row * _BYTES_PER_ROW
            lines.append(format_byte_line(palette_data, offset, _BYTES_PER_ROW))

        lines.append("")  # blank line after the palette block
        return lines

    def _write_file(self, lines: list[str]) -> None:
        target = Path(self._config.target_file)
        mode = "a" if self._config.target_append else "w"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open(mode, encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError as e:
            self._log.log_error(
                f"Error writing palette to '{self._config.target_file}'", e
            )
