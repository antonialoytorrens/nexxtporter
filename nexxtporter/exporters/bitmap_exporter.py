"""Export a PNG bitmap of CHR tiles using palette and RGB lookup data."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from nexxtporter.config import BitmapLayout
from nexxtporter.exporters.base import BaseExporter
from nexxtporter.models import Palette, PaletteSet, Pattern
from nexxtporter.utils import parse_number, parse_rle_binary

if TYPE_CHECKING:
    from nexxtporter.config import ExportBitmapConfig
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import Color, RGBLookup, RGBLookupRegistry

_CHR_TOKEN     = "CHRMain"
_PALETTE_TOKEN = "Palette"
_TILE_PIXELS   = 8   # NES tiles are always 8×8 pixels
_TILES_PER_ROW = 16  # Standard Nexxt display width in tiles


class BitmapExporter(BaseExporter):
    """Renders a subset of CHR tiles with a chosen palette to a PNG file."""

    def __init__(
        self, log: Logger, nss_source: str, config: ExportBitmapConfig
    ) -> None:
        super().__init__(log, nss_source)
        self._config = config

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def export(self, tokens: dict[str, str], rgb_registry: RGBLookupRegistry) -> None:
        cfg = self._config

        start_tile = parse_number(cfg.start_tile_index)
        if start_tile is None:
            self._log.log_error(
                f"NSS '{self._nss_source}': bitmap export to '{cfg.target_file}' "
                f"has invalid StartTileIndex '{cfg.start_tile_index}'"
            )
            return

        tile_count = parse_number(cfg.tile_count)
        if tile_count is None:
            self._log.log_error(
                f"NSS '{self._nss_source}': bitmap export to '{cfg.target_file}' "
                f"has invalid TileCount '{cfg.tile_count}'"
            )
            return

        palette_set_idx = parse_number(cfg.palette_set_index)
        if palette_set_idx is None or not (0 <= palette_set_idx < 4):
            self._log.log_error(
                f"NSS '{self._nss_source}': bitmap export to '{cfg.target_file}' "
                f"has invalid PaletteSetIndex '{cfg.palette_set_index}'"
            )
            return

        palette_idx = parse_number(cfg.palette_index)
        if palette_idx is None or not (0 <= palette_idx < 4):
            self._log.log_error(
                f"NSS '{self._nss_source}': bitmap export to '{cfg.target_file}' "
                f"has invalid PaletteIndex '{cfg.palette_index}'"
            )
            return

        palette_sets = self._load_palette_sets(tokens, cfg.target_file)
        if palette_sets is None:
            return

        try:
            rgb_lookup = rgb_registry.get(cfg.rgb_lookup_id)
        except KeyError:
            self._log.log_error(
                f"NSS '{self._nss_source}': RGB lookup '{cfg.rgb_lookup_id}' not found"
            )
            return

        patterns = self._load_patterns(tokens, cfg.target_file, start_tile, tile_count)
        if patterns is None:
            return

        palette = palette_sets[palette_set_idx].palettes[palette_idx]
        self._render(cfg.target_file, cfg.layout, patterns, palette, rgb_lookup)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_palette_sets(
        self, tokens: dict[str, str], target_file: str
    ) -> list[PaletteSet] | None:
        if _PALETTE_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}': bitmap export to '{target_file}' "
                f"is missing '{_PALETTE_TOKEN}' token"
            )
            return None

        raw = parse_rle_binary(
            self._log, self._nss_source, _PALETTE_TOKEN, tokens[_PALETTE_TOKEN]
        )
        if len(raw) != 64:
            self._log.log_error(
                f"NSS '{self._nss_source}': Palette token has {len(raw)} bytes "
                f"(expected 64) for bitmap export to '{target_file}'"
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
        self,
        tokens: dict[str, str],
        target_file: str,
        start_tile: int,
        tile_count: int,
    ) -> list[Pattern] | None:
        if _CHR_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}': bitmap export to '{target_file}' "
                f"is missing '{_CHR_TOKEN}' token"
            )
            return None

        chr_data = parse_rle_binary(
            self._log, self._nss_source, _CHR_TOKEN, tokens[_CHR_TOKEN]
        )
        required = (start_tile + tile_count) * 16
        if required > len(chr_data):
            self._log.log_error(
                f"NSS '{self._nss_source}': CHRMain is {len(chr_data)} bytes, "
                f"smaller than required {required} for StartTileIndex={start_tile}, "
                f"TileCount={tile_count}"
            )
            return None

        patterns: list[Pattern] = []
        for i in range(tile_count):
            p = Pattern.parse(chr_data, (start_tile + i) * 16)
            if p is None:
                self._log.log_error(
                    f"NSS '{self._nss_source}': failed to parse pattern {i}"
                )
                return None
            patterns.append(p)
        return patterns

    def _render(
        self,
        target_file: str,
        layout: BitmapLayout,
        patterns: list[Pattern],
        palette: Palette,
        rgb_lookup: RGBLookup,
    ) -> None:
        width, height = _measure_output_size(layout, len(patterns))
        if width == 0 or height == 0:
            self._log.log_error(
                f"NSS '{self._nss_source}': unknown BitmapLayout '{layout}'"
            )
            return

        bg_index = palette.parsed_data[0]
        bg_color = rgb_lookup.get_color(bg_index)
        image = Image.new("RGB", (width, height), bg_color)
        pixels = image.load()

        if layout == BitmapLayout.LINEAR:
            _write_linear(pixels, patterns, palette, rgb_lookup)
        elif layout == BitmapLayout.RECT:
            _write_rect(pixels, patterns, palette, rgb_lookup)
        elif layout == BitmapLayout.RECT8BY16:
            _write_rect8by16(pixels, patterns, palette, rgb_lookup)

        self._log.log(
            f"Writing {width}×{height} bitmap to '{target_file}'"
        )
        try:
            out = Path(target_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(out), "PNG")
        except OSError as e:
            self._log.log_error(f"Error saving bitmap to '{target_file}'", e)


# ---------------------------------------------------------------------------
# Layout helpers (module-level, reused by NametableBitmapExporter)
# ---------------------------------------------------------------------------

def _measure_output_size(layout: BitmapLayout, tile_count: int) -> tuple[int, int]:
    if layout == BitmapLayout.LINEAR:
        return _TILE_PIXELS * tile_count, _TILE_PIXELS

    if layout == BitmapLayout.RECT:
        width  = min(128, _TILE_PIXELS * tile_count)
        height = _TILE_PIXELS * math.ceil(tile_count / _TILES_PER_ROW)
        return width, height

    if layout == BitmapLayout.RECT8BY16:
        half   = math.ceil(tile_count / 2)
        width  = min(128, half * _TILE_PIXELS)
        height = 16 * (half // _TILES_PER_ROW)
        return width, height

    return 0, 0


def write_tile(
    pixels: object,
    target_x: int,
    target_y: int,
    pattern: Pattern,
    palette: Palette,
    rgb_lookup: RGBLookup,
) -> None:
    """Paint one 8×8 tile into a Pillow PixelAccess object."""
    for y in range(_TILE_PIXELS):
        for x in range(_TILE_PIXELS):
            palette_idx = pattern.parsed_data[y * _TILE_PIXELS + x]
            color_idx   = palette.parsed_data[palette_idx]
            pixels[target_x + x, target_y + y] = rgb_lookup.get_color(color_idx)  # type: ignore[index]


def _write_linear(
    pixels: object,
    patterns: list[Pattern],
    palette: Palette,
    rgb_lookup: RGBLookup,
) -> None:
    for i, pattern in enumerate(patterns):
        write_tile(pixels, i * _TILE_PIXELS, 0, pattern, palette, rgb_lookup)


def _write_rect(
    pixels: object,
    patterns: list[Pattern],
    palette: Palette,
    rgb_lookup: RGBLookup,
) -> None:
    for i, pattern in enumerate(patterns):
        col = i % _TILES_PER_ROW
        row = i // _TILES_PER_ROW
        write_tile(pixels, col * _TILE_PIXELS, row * _TILE_PIXELS, pattern, palette, rgb_lookup)


def _write_rect8by16(
    pixels: object,
    patterns: list[Pattern],
    palette: Palette,
    rgb_lookup: RGBLookup,
) -> None:
    for i, pattern in enumerate(patterns):
        # Tiles are arranged in pairs for 8×16 sprite mode:
        # even-index tile goes top, odd-index tile goes directly below it.
        row = 2 * (i // 32) + (i % 2)
        col = (i // 2) % _TILES_PER_ROW
        write_tile(pixels, col * _TILE_PIXELS, row * _TILE_PIXELS, pattern, palette, rgb_lookup)
