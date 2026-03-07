"""Tests for nexxtporter.exporters.nametable_exporter.NametableExporter."""

from unittest.mock import MagicMock

from nexxtporter.config import ExportNametableConfig
from nexxtporter.exporters.nametable_exporter import NametableExporter
from nexxtporter.rgb_lookup import RGBLookupRegistry


def _make_exporter(tmp_path, target: str = "nam.dat"):
    log = MagicMock()
    cfg = ExportNametableConfig(target_file=str(tmp_path / target))
    return NametableExporter(log=log, nss_source="game.nss", config=cfg), log


def _nametable_token(data: bytes) -> dict[str, str]:
    return {"NameTable": data.hex().upper()}


class TestNametableExporter:
    def test_writes_nametable_data(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        data = bytes(range(128)) * 2  # 256 bytes
        exporter.export(_nametable_token(data), RGBLookupRegistry())
        out = tmp_path / "nam.dat"
        assert out.exists()
        assert out.read_bytes() == data
        log.log_error.assert_not_called()

    def test_missing_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export({}, RGBLookupRegistry())
        log.log_error.assert_called_once()
        assert not (tmp_path / "nam.dat").exists()

    def test_empty_data_writes_empty_file(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export(_nametable_token(b""), RGBLookupRegistry())
        out = tmp_path / "nam.dat"
        assert out.exists()
        assert out.read_bytes() == b""
