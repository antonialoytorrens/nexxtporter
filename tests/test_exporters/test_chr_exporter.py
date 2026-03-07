"""Tests for nexxtporter.exporters.chr_exporter.CHRExporter."""

from pathlib import Path
from unittest.mock import MagicMock

from nexxtporter.config import ExportCHRConfig
from nexxtporter.exporters.chr_exporter import CHRExporter
from nexxtporter.rgb_lookup import RGBLookupRegistry


def _make_exporter(tmp_path, target: str = "out.chr", start: str = "0", size: str = "4"):
    log = MagicMock()
    cfg = ExportCHRConfig(target_file=str(tmp_path / target), start=start, size=size)
    return CHRExporter(log=log, nss_source="game.nss", config=cfg), log


def _chr_token(data: bytes) -> dict[str, str]:
    """Return a tokens dict with a CHRMain token containing plain hex data."""
    return {"CHRMain": data.hex().upper()}


class TestCHRExporter:
    def test_exports_full_range(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        data = bytes(range(16))
        tokens = _chr_token(data)
        exporter.export(tokens, RGBLookupRegistry())
        out = tmp_path / "out.chr"
        assert out.exists()
        assert out.read_bytes() == data[:4]
        log.log_error.assert_not_called()

    def test_exports_slice_with_start(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, start="4", size="4")
        data = bytes(range(16))
        exporter.export(_chr_token(data), RGBLookupRegistry())
        assert (tmp_path / "out.chr").read_bytes() == bytes([4, 5, 6, 7])

    def test_missing_chr_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export({}, RGBLookupRegistry())
        log.log_error.assert_called_once()
        assert not (tmp_path / "out.chr").exists()

    def test_invalid_start_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, start="not_a_number")
        exporter.export(_chr_token(bytes(16)), RGBLookupRegistry())
        log.log_error.assert_called_once()

    def test_invalid_size_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, size="????")
        exporter.export(_chr_token(bytes(16)), RGBLookupRegistry())
        log.log_error.assert_called_once()

    def test_data_too_small_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, start="0", size="100")
        exporter.export(_chr_token(bytes(8)), RGBLookupRegistry())
        log.log_error.assert_called_once()

    def test_hex_start_works(self, tmp_path):
        exporter, log = _make_exporter(tmp_path, start="$02", size="2")
        data = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        exporter.export(_chr_token(data), RGBLookupRegistry())
        assert (tmp_path / "out.chr").read_bytes() == bytes([0xCC, 0xDD])
