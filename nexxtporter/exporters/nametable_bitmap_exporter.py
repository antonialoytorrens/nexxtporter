"""Export a 256×240 PNG bitmap of the full nametable view from an NSS file."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from nexxtporter.exporters.base import BaseExporter
from nexxtporter.exporters.bitmap_exporter import write_tile
from nexxtporter.models import AttributeTable, PaletteSet, Pattern
from nexxtporter.utils import parse_number, parse_rle_binary

if TYPE_CHECKING:
    from nexxtporter.config import ExportNametableBitmapConfig
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import RGBLookupRegistry

_CHR_TOKEN       = "CHRMain"
_PALETTE_TOKEN   = "Palette"
_NAMETABLE_TOKEN = "NameTable"
_ATTR_TOKEN      = "AttrTable"

_SCREEN_TILES_W  = 32   # NES nametable: 32 tiles wide
_SCREEN_TILES_H  = 30   # NES nametable: 30 tiles tall
_SCREEN_WIDTH_PX = 256  # 32 × 8
_SCREEN_HEIGHT_PX = 240 # 30 × 8
_TILES_PER_CHR_SET = 256
_CHR_BYTES_PER_SET = 4096  # 256 tiles × 16 bytes each


class NametableBitmapExporter(BaseExporter):
    """Renders the nametable visible in Nexxt to a 256×240 PNG file.

    Combines CHR patterns, nametable tile indices, attribute table palette
    selectors, palette data, and an RGB lookup table.
    """

    def __init__(
        self,
        log: Logger,
        nss_source: str,
        config: ExportNametableBitmapConfig,
    ) -> None:
        super().__init__(log, nss_source)
        self._config = config

    def export(self, tokens: dict[str, str], rgb_registry: RGBLookupRegistry) -> None:
        cfg = self._config

        chr_index = parse_number(cfg.chr_index)
        if chr_index is None or not (0 <= chr_index < 4):
            self._log.log_error(
                f"NSS '{self._nss_source}': nametable bitmap export to "
                f"'{cfg.target_file}' has invalid CHRIndex '{cfg.chr_index}'"
            )
            return

        palette_set_idx = parse_number(cfg.palette_set_index)
        if palette_set_idx is None or not (0 <= palette_set_idx < 4):
            self._log.log_error(
                f"NSS '{self._nss_source}': nametable bitmap export to "
                f"'{cfg.target_file}' has invalid PaletteSetIndex '{cfg.palette_set_index}'"
            )
            return

        try:
            rgb_lookup = rgb_registry.get(cfg.rgb_lookup_id)
        except KeyError:
            self._log.log_error(
                f"NSS '{self._nss_source}': RGB lookup '{cfg.rgb_lookup_id}' not found"
            )
            return

        palette_sets = self._load_palette_sets(tokens, cfg.target_file)
        if palette_sets is None:
            return

        patterns = self._load_patterns(tokens, cfg.target_file, chr_index)
        if patterns is None:
            return

        nametable = self._load_nametable(tokens, cfg.target_file)
        if nametable is None:
            return

        attr_table = self._load_attribute_table(tokens, cfg.target_file)
        if attr_table is None:
            return

        self._render(
            cfg.target_file,
            patterns,
            nametable,
            attr_table,
            palette_sets[palette_set_idx],
            rgb_lookup,
        )

    # ------------------------------------------------------------------
    # Private data loaders
    # ------------------------------------------------------------------

    def _load_palette_sets(
        self, tokens: dict[str, str], target_file: str
    ) -> list[PaletteSet] | None:
        if _PALETTE_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}': nametable bitmap export to "
                f"'{target_file}' is missing '{_PALETTE_TOKEN}' token"
            )
            return None

        raw = parse_rle_binary(
            self._log, self._nss_source, _PALETTE_TOKEN, tokens[_PALETTE_TOKEN]
        )
        if len(raw) != 64:
            self._log.log_error(
                f"NSS '{self._nss_source}': Palette token has {len(raw)} bytes "
                f"(expected 64) for nametable bitmap export to '{target_file}'"
            )
            return None

        sets: list[PaletteSet] = []
        for i in range(4):
            ps = PaletteSet.parse(raw, i * 16)
            if ps is None:
                self._log.log_error(
                    f"NSS '{self._nss_source}': failed to parse PaletteSet {i}"
                )
                return None
            sets.append(ps)
        return sets

    def _load_patterns(
        self, tokens: dict[str, str], target_file: str, chr_index: int
    ) -> list[Pattern] | None:
        if _CHR_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}': nametable bitmap export to "
                f"'{target_file}' is missing '{_CHR_TOKEN}' token"
            )
            return None

        chr_data = parse_rle_binary(
            self._log, self._nss_source, _CHR_TOKEN, tokens[_CHR_TOKEN]
        )
        required = chr_index * _CHR_BYTES_PER_SET + _CHR_BYTES_PER_SET
        if required > len(chr_data):
            self._log.log_error(
                f"NSS '{self._nss_source}': CHRMain is {len(chr_data)} bytes, "
                f"too small for CHRIndex={chr_index}"
            )
            return None

        patterns: list[Pattern] = []
        for i in range(_TILES_PER_CHR_SET):
            p = Pattern.parse(chr_data, chr_index * _CHR_BYTES_PER_SET + i * 16)
            if p is None:
                self._log.log_error(
                    f"NSS '{self._nss_source}': failed to parse pattern {i}"
                )
                return None
            patterns.append(p)
        return patterns

    def _load_nametable(
        self, tokens: dict[str, str], target_file: str
    ) -> bytes | None:
        if _NAMETABLE_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}': nametable bitmap export to "
                f"'{target_file}' is missing '{_NAMETABLE_TOKEN}' token"
            )
            return None

        data = parse_rle_binary(
            self._log, self._nss_source, _NAMETABLE_TOKEN, tokens[_NAMETABLE_TOKEN]
        )
        if len(data) != 960:
            self._log.log_error(
                f"NSS '{self._nss_source}': NameTable token has {len(data)} bytes "
                f"(expected 960) for nametable bitmap export to '{target_file}'"
            )
            return None
        return data

    def _load_attribute_table(
        self, tokens: dict[str, str], target_file: str
    ) -> AttributeTable | None:
        if _ATTR_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}': nametable bitmap export to "
                f"'{target_file}' is missing '{_ATTR_TOKEN}' token"
            )
            return None

        raw = parse_rle_binary(
            self._log, self._nss_source, _ATTR_TOKEN, tokens[_ATTR_TOKEN]
        )
        table = AttributeTable.parse(raw)
        if table is None:
            self._log.log_error(
                f"NSS '{self._nss_source}': failed to parse AttributeTable "
                f"for nametable bitmap export to '{target_file}'"
            )
        return table

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(
        self,
        target_file: str,
        patterns: list[Pattern],
        nametable: bytes,
        attr_table: AttributeTable,
        palette_set: PaletteSet,
        rgb_lookup: object,
    ) -> None:
        bg_index = palette_set.palettes[0].parsed_data[0]
        bg_color = rgb_lookup.get_color(bg_index)  # type: ignore[union-attr]

        image = Image.new("RGB", (_SCREEN_WIDTH_PX, _SCREEN_HEIGHT_PX), bg_color)
        pixels = image.load()

        for tile_y in range(_SCREEN_TILES_H):
            for tile_x in range(_SCREEN_TILES_W):
                pattern_idx = nametable[_SCREEN_TILES_W * tile_y + tile_x]
                palette_idx = attr_table.get_for_position(tile_x, tile_y)
                write_tile(
                    pixels,
                    tile_x * 8,
                    tile_y * 8,
                    patterns[pattern_idx],
                    palette_set.palettes[palette_idx],
                    rgb_lookup,  # type: ignore[arg-type]
                )

        self._log.log(
            f"Writing {_SCREEN_WIDTH_PX}×{_SCREEN_HEIGHT_PX} nametable bitmap "
            f"to '{target_file}'"
        )
        try:
            out = Path(target_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(out), "PNG")
        except OSError as e:
            self._log.log_error(f"Error saving nametable bitmap to '{target_file}'", e)
