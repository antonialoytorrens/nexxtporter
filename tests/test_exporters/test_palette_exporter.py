"""Tests for nexxtporter.exporters.palette_exporter.PaletteExporter."""

from unittest.mock import MagicMock

from nexxtporter.config import ExportPaletteConfig
from nexxtporter.exporters.palette_exporter import PaletteExporter
from nexxtporter.rgb_lookup import RGBLookupRegistry


def _palette_64_bytes() -> bytes:
    """Build a realistic 64-byte palette block (4 sets × 4 × 4 bytes)."""
    # Each byte is just its index for easy verification
    return bytes(range(64))


def _palette_token(data: bytes) -> dict[str, str]:
    return {"Palette": data.hex().upper()}


def _make_exporter(tmp_path, sub_palette: int = 0, append: bool = False,
                   segment: str | None = None, variable: str | None = None):
    log = MagicMock()
    cfg = ExportPaletteConfig(
        target_file=str(tmp_path / "palette.inc"),
        target_segment_name=segment,
        target_variable_name=variable,
        target_append=append,
        source_sub_palette=sub_palette,
    )
    return PaletteExporter(log=log, nss_source="game.nss", config=cfg), log


class TestPaletteExporter:
    def test_creates_file_with_byte_directives(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export(_palette_token(_palette_64_bytes()), RGBLookupRegistry())
        out = (tmp_path / "palette.inc").read_text(encoding="utf-8")
        assert ".byte" in out
        log.log_error.assert_not_called()

    def test_first_palette_set_correct_bytes(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, sub_palette=0)
        data = _palette_64_bytes()
        exporter.export(_palette_token(data), RGBLookupRegistry())
        out = (tmp_path / "palette.inc").read_text(encoding="utf-8")
        # Row 0 should be bytes 0-3
        assert "$00,$01,$02,$03" in out

    def test_second_palette_set(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, sub_palette=1)
        data = _palette_64_bytes()
        exporter.export(_palette_token(data), RGBLookupRegistry())
        out = (tmp_path / "palette.inc").read_text(encoding="utf-8")
        # Sub-palette 1 starts at byte 16
        assert "$10,$11,$12,$13" in out

    def test_segment_name_written(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, segment="MY_SEG")
        exporter.export(_palette_token(_palette_64_bytes()), RGBLookupRegistry())
        out = (tmp_path / "palette.inc").read_text(encoding="utf-8")
        assert '.segment "MY_SEG"' in out

    def test_variable_name_written(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, variable="my_pal")
        exporter.export(_palette_token(_palette_64_bytes()), RGBLookupRegistry())
        out = (tmp_path / "palette.inc").read_text(encoding="utf-8")
        assert "my_pal:" in out

    def test_append_mode_does_not_overwrite(self, tmp_path):
        existing = tmp_path / "palette.inc"
        existing.write_text("EXISTING\n", encoding="utf-8")
        exporter, log = _make_exporter(tmp_path, append=True)
        exporter.export(_palette_token(_palette_64_bytes()), RGBLookupRegistry())
        out = existing.read_text(encoding="utf-8")
        assert out.startswith("EXISTING")
        assert ".byte" in out

    def test_no_append_overwrites_file(self, tmp_path):
        existing = tmp_path / "palette.inc"
        existing.write_text("OLD CONTENT\n", encoding="utf-8")
        exporter, log = _make_exporter(tmp_path, append=False)
        exporter.export(_palette_token(_palette_64_bytes()), RGBLookupRegistry())
        out = existing.read_text(encoding="utf-8")
        assert "OLD CONTENT" not in out

    def test_missing_palette_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export({}, RGBLookupRegistry())
        log.log_error.assert_called_once()

    def test_four_byte_rows_written(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export(_palette_token(_palette_64_bytes()), RGBLookupRegistry())
        out = (tmp_path / "palette.inc").read_text(encoding="utf-8")
        byte_lines = [l for l in out.splitlines() if l.startswith(".byte")]
        assert len(byte_lines) == 4
