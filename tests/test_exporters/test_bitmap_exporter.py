"""Tests for nexxtporter.exporters.bitmap_exporter.BitmapExporter."""

from unittest.mock import MagicMock

from PIL import Image

from nexxtporter.config import BitmapLayout, ExportBitmapConfig
from nexxtporter.exporters.bitmap_exporter import (
    BitmapExporter,
    _measure_output_size,
    write_tile,
)
from nexxtporter.models import Palette, Pattern
from nexxtporter.rgb_lookup import RGBLookup, RGBLookupRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_registry() -> RGBLookupRegistry:
    reg = RGBLookupRegistry()
    reg.add(RGBLookup.default())
    return reg


def _solid_chr_bytes(color_index: int, tile_count: int = 1) -> bytes:
    """Build CHR data where every pixel has the given color_index (0–3)."""
    tiles = bytearray()
    for _ in range(tile_count):
        # low plane: bit set if color_index & 1
        low  = 0xFF if (color_index & 1) else 0x00
        # high plane: bit set if color_index & 2
        high = 0xFF if (color_index & 2) else 0x00
        tiles += bytes([low] * 8 + [high] * 8)
    return bytes(tiles)


def _palette_64_bytes_zeroed() -> bytes:
    """64 bytes of palette data — all NES colour index 0."""
    return bytes(64)


def _make_tokens(chr_data: bytes, palette_data: bytes) -> dict[str, str]:
    return {
        "CHRMain": chr_data.hex().upper(),
        "Palette": palette_data.hex().upper(),
    }


def _make_exporter(tmp_path, layout: BitmapLayout = BitmapLayout.LINEAR,
                   start: str = "0", count: str = "1",
                   pal_set: str = "0", pal_idx: str = "0"):
    log = MagicMock()
    cfg = ExportBitmapConfig(
        target_file=str(tmp_path / "out.png"),
        start_tile_index=start,
        tile_count=count,
        layout=layout,
        rgb_lookup_id="Default",
        palette_set_index=pal_set,
        palette_index=pal_idx,
    )
    return BitmapExporter(log=log, nss_source="game.nss", config=cfg), log


# ---------------------------------------------------------------------------
# _measure_output_size
# ---------------------------------------------------------------------------

class TestMeasureOutputSize:
    def test_linear_1_tile(self):
        w, h = _measure_output_size(BitmapLayout.LINEAR, 1)
        assert w == 8 and h == 8

    def test_linear_4_tiles(self):
        w, h = _measure_output_size(BitmapLayout.LINEAR, 4)
        assert w == 32 and h == 8

    def test_rect_16_tiles_single_row(self):
        w, h = _measure_output_size(BitmapLayout.RECT, 16)
        assert w == 128 and h == 8

    def test_rect_32_tiles_two_rows(self):
        w, h = _measure_output_size(BitmapLayout.RECT, 32)
        assert w == 128 and h == 16

    def test_rect_1_tile(self):
        w, h = _measure_output_size(BitmapLayout.RECT, 1)
        assert w == 8 and h == 8

    def test_rect8by16_64_tiles(self):
        w, h = _measure_output_size(BitmapLayout.RECT8BY16, 64)
        assert w == 128 and h == 32


# ---------------------------------------------------------------------------
# write_tile
# ---------------------------------------------------------------------------

class TestWriteTile:
    def test_writes_solid_color(self):
        image = Image.new("RGB", (8, 8), (0, 0, 0))
        pixels = image.load()

        # Pattern: all pixels = palette index 1
        raw = _solid_chr_bytes(1)
        pattern = Pattern.parse(raw, 0)

        # Palette: index 1 → NES color 1 (dark blue in default table)
        palette_data = bytes([0, 1, 2, 3])  # parsed_data
        palette = Palette(raw_data=palette_data, raw_data_start=0, parsed_data=palette_data)

        rgb = RGBLookup.default()
        write_tile(pixels, 0, 0, pattern, palette, rgb)

        expected_color = rgb.get_color(1)
        assert pixels[0, 0] == expected_color
        assert pixels[7, 7] == expected_color


# ---------------------------------------------------------------------------
# BitmapExporter.export
# ---------------------------------------------------------------------------

class TestBitmapExporter:
    def test_creates_png_file(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _make_tokens(_solid_chr_bytes(0), _palette_64_bytes_zeroed())
        exporter.export(tokens, _default_registry())
        out = tmp_path / "out.png"
        assert out.exists()
        img = Image.open(out)
        assert img.size == (8, 8)
        log.log_error.assert_not_called()

    def test_missing_palette_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export({"CHRMain": "00" * 16}, _default_registry())
        log.log_error.assert_called()

    def test_missing_chr_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export({"Palette": "00" * 64}, _default_registry())
        log.log_error.assert_called()

    def test_invalid_palette_set_index_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, pal_set="99")
        tokens = _make_tokens(_solid_chr_bytes(0), _palette_64_bytes_zeroed())
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_invalid_palette_index_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, pal_idx="99")
        tokens = _make_tokens(_solid_chr_bytes(0), _palette_64_bytes_zeroed())
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_rect_layout_produces_correct_size(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, layout=BitmapLayout.RECT, count="16")
        tokens = _make_tokens(_solid_chr_bytes(0, 16), _palette_64_bytes_zeroed())
        exporter.export(tokens, _default_registry())
        img = Image.open(tmp_path / "out.png")
        assert img.size == (128, 8)

    def test_unknown_rgb_lookup_logs_error(self, tmp_path):
        log = MagicMock()
        cfg = ExportBitmapConfig(
            target_file=str(tmp_path / "out.png"),
            rgb_lookup_id="nonexistent",
        )
        exporter = BitmapExporter(log=log, nss_source="game.nss", config=cfg)
        tokens = _make_tokens(_solid_chr_bytes(0), _palette_64_bytes_zeroed())
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()
