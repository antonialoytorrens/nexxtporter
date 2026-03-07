"""Tests for NametableAttributesExporter."""

from unittest.mock import MagicMock

from nexxtporter.config import ExportNametableAttributesConfig
from nexxtporter.exporters.nametable_attributes_exporter import NametableAttributesExporter
from nexxtporter.rgb_lookup import RGBLookupRegistry


def _make_exporter(tmp_path, target: str = "attr.dat"):
    log = MagicMock()
    cfg = ExportNametableAttributesConfig(target_file=str(tmp_path / target))
    return NametableAttributesExporter(log=log, nss_source="game.nss", config=cfg), log


def _attr_token(data: bytes) -> dict[str, str]:
    return {"AttrTable": data.hex().upper()}


class TestNametableAttributesExporter:
    def test_writes_attribute_data(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        data = bytes(range(64))
        exporter.export(_attr_token(data), RGBLookupRegistry())
        out = tmp_path / "attr.dat"
        assert out.exists()
        assert out.read_bytes() == data
        log.log_error.assert_not_called()

    def test_missing_token_logs_error(self, tmp_path):
        exporter, log = _make_exporter(tmp_path)
        exporter.export({}, RGBLookupRegistry())
        log.log_error.assert_called_once()
        assert not (tmp_path / "attr.dat").exists()
