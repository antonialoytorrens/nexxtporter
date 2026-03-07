"""Tests for NametableBitmapExporter."""

from unittest.mock import MagicMock

from PIL import Image

from nexxtporter.config import ExportNametableBitmapConfig
from nexxtporter.exporters.nametable_bitmap_exporter import NametableBitmapExporter
from nexxtporter.rgb_lookup import RGBLookup, RGBLookupRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_registry() -> RGBLookupRegistry:
    reg = RGBLookupRegistry()
    reg.add(RGBLookup.default())
    return reg


def _zero_chr(tiles: int = 256) -> bytes:
    """CHR data for *tiles* blank tiles (all pixels = colour 0)."""
    return bytes(tiles * 16)


def _zero_palette() -> bytes:
    """64-byte all-zero palette."""
    return bytes(64)


def _zero_nametable() -> bytes:
    """960-byte all-zero nametable (all tiles reference tile 0)."""
    return bytes(960)


def _zero_attr() -> bytes:
    """64-byte all-zero attribute table."""
    return bytes(64)


def _full_tokens(
    chr_sets: int = 1,
    nametable: bytes | None = None,
    attr: bytes | None = None,
    palette: bytes | None = None,
) -> dict[str, str]:
    chr_data = _zero_chr(256 * chr_sets)
    return {
        "CHRMain":   chr_data.hex().upper(),
        "Palette":   (palette or _zero_palette()).hex().upper(),
        "NameTable": (nametable or _zero_nametable()).hex().upper(),
        "AttrTable": (attr or _zero_attr()).hex().upper(),
    }


def _make_exporter(tmp_path, target: str = "nam.png",
                   chr_index: str = "0", pal_set: str = "0"):
    log = MagicMock()
    cfg = ExportNametableBitmapConfig(
        target_file=str(tmp_path / target),
        rgb_lookup_id="Default",
        chr_index=chr_index,
        palette_set_index=pal_set,
    )
    return NametableBitmapExporter(log=log, nss_source="game.nss", config=cfg), log


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNametableBitmapExporter:
    def test_creates_256x240_png(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export(_full_tokens(), _default_registry())
        out = tmp_path / "nam.png"
        assert out.exists()
        img = Image.open(out)
        assert img.size == (256, 240)
        log.log_error.assert_not_called()

    def test_missing_palette_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _full_tokens()
        del tokens["Palette"]
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_missing_chr_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _full_tokens()
        del tokens["CHRMain"]
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_missing_nametable_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _full_tokens()
        del tokens["NameTable"]
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_missing_attr_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _full_tokens()
        del tokens["AttrTable"]
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_invalid_chr_index_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, chr_index="99")
        exporter.export(_full_tokens(), _default_registry())
        log.log_error.assert_called()

    def test_invalid_palette_set_index_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, pal_set="bad")
        exporter.export(_full_tokens(), _default_registry())
        log.log_error.assert_called()

    def test_chr_index_1_requires_two_chr_sets(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, chr_index="1")
        # Only one CHR set — should fail
        exporter.export(_full_tokens(chr_sets=1), _default_registry())
        log.log_error.assert_called()

    def test_chr_index_1_with_sufficient_data(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, chr_index="1")
        exporter.export(_full_tokens(chr_sets=2), _default_registry())
        out = tmp_path / "nam.png"
        assert out.exists()
        log.log_error.assert_not_called()

    def test_wrong_nametable_size_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _full_tokens(nametable=bytes(500))  # should be 960
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()

    def test_wrong_attr_size_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        tokens = _full_tokens(attr=bytes(32))  # should be 64
        exporter.export(tokens, _default_registry())
        log.log_error.assert_called()
