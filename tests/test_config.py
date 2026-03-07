"""Tests for nexxtporter.config — dataclass parsing from JSON-like dicts."""

import pytest

from nexxtporter.config import (
    BitmapLayout,
    ExportBitmapConfig,
    ExportCHRConfig,
    ExportNametableBitmapConfig,
    ExportNametableConfig,
    ExportNametableAttributesConfig,
    ExportPaletteConfig,
    LoggerConfig,
    NexxtporterConfig,
    NSSConfig,
    RGBLookupConfig,
)


# ---------------------------------------------------------------------------
# LoggerConfig
# ---------------------------------------------------------------------------

class TestLoggerConfig:
    def test_defaults(self):
        cfg = LoggerConfig.from_dict({})
        assert cfg.echo is True
        assert cfg.log_file is None

    def test_explicit_values(self):
        cfg = LoggerConfig.from_dict({"Echo": False, "LogFile": "out.log"})
        assert cfg.echo is False
        assert cfg.log_file == "out.log"


# ---------------------------------------------------------------------------
# ExportCHRConfig
# ---------------------------------------------------------------------------

class TestExportCHRConfig:
    def test_required_field(self):
        cfg = ExportCHRConfig.from_dict({"TargetFile": "out.chr"})
        assert cfg.target_file == "out.chr"
        assert cfg.start == "0"
        assert cfg.size == "1024"

    def test_explicit_start_and_size(self):
        cfg = ExportCHRConfig.from_dict(
            {"TargetFile": "out.chr", "Start": "$100", "Size": "$400"}
        )
        assert cfg.start == "$100"
        assert cfg.size == "$400"

    def test_missing_target_file_raises(self):
        with pytest.raises(KeyError):
            ExportCHRConfig.from_dict({"Start": "0"})


# ---------------------------------------------------------------------------
# ExportPaletteConfig
# ---------------------------------------------------------------------------

class TestExportPaletteConfig:
    def test_defaults(self):
        cfg = ExportPaletteConfig.from_dict({"TargetFile": "pal.inc"})
        assert cfg.target_file == "pal.inc"
        assert cfg.target_segment_name is None
        assert cfg.target_variable_name is None
        assert cfg.target_append is False
        assert cfg.source_sub_palette == 0

    def test_all_fields(self):
        cfg = ExportPaletteConfig.from_dict({
            "TargetFile": "pal.inc",
            "TargetSegmentName": "PRG",
            "TargetVariableName": "my_palette",
            "TargetAppend": True,
            "SourceSubPalette": 3,
        })
        assert cfg.target_segment_name == "PRG"
        assert cfg.target_variable_name == "my_palette"
        assert cfg.target_append is True
        assert cfg.source_sub_palette == 3


# ---------------------------------------------------------------------------
# ExportBitmapConfig
# ---------------------------------------------------------------------------

class TestExportBitmapConfig:
    def test_defaults(self):
        cfg = ExportBitmapConfig.from_dict({"TargetFile": "tiles.png"})
        assert cfg.layout == BitmapLayout.LINEAR
        assert cfg.rgb_lookup_id == "Default"
        assert cfg.start_tile_index == "0"
        assert cfg.tile_count == "256"
        assert cfg.palette_set_index == "0"
        assert cfg.palette_index == "0"

    def test_layout_rect(self):
        cfg = ExportBitmapConfig.from_dict({"TargetFile": "x.png", "Layout": 1})
        assert cfg.layout == BitmapLayout.RECT

    def test_layout_rect8by16(self):
        cfg = ExportBitmapConfig.from_dict({"TargetFile": "x.png", "Layout": 2})
        assert cfg.layout == BitmapLayout.RECT8BY16

    def test_invalid_layout_falls_back_to_linear(self):
        cfg = ExportBitmapConfig.from_dict({"TargetFile": "x.png", "Layout": 99})
        assert cfg.layout == BitmapLayout.LINEAR


# ---------------------------------------------------------------------------
# ExportNametableBitmapConfig
# ---------------------------------------------------------------------------

class TestExportNametableBitmapConfig:
    def test_defaults(self):
        cfg = ExportNametableBitmapConfig.from_dict({"TargetFile": "nam.png"})
        assert cfg.chr_index == "0"
        assert cfg.palette_set_index == "0"
        assert cfg.rgb_lookup_id == "Default"

    def test_explicit_values(self):
        cfg = ExportNametableBitmapConfig.from_dict({
            "TargetFile": "nam.png",
            "CHRIndex": "2",
            "PaletteSetIndex": "1",
            "RGBLookupID": "custom",
        })
        assert cfg.chr_index == "2"
        assert cfg.palette_set_index == "1"
        assert cfg.rgb_lookup_id == "custom"


# ---------------------------------------------------------------------------
# NSSConfig
# ---------------------------------------------------------------------------

class TestNSSConfig:
    def test_source_file_required(self):
        cfg = NSSConfig.from_dict({"SourceFile": "game.nss"})
        assert cfg.source_file == "game.nss"

    def test_empty_lists_by_default(self):
        cfg = NSSConfig.from_dict({"SourceFile": "game.nss"})
        assert cfg.export_chr == []
        assert cfg.export_palette == []
        assert cfg.export_nametable == []
        assert cfg.export_nametable_attributes == []
        assert cfg.export_bitmap == []
        assert cfg.export_nametable_bitmap == []

    def test_export_chr_parsed(self):
        cfg = NSSConfig.from_dict({
            "SourceFile": "game.nss",
            "ExportCHR": [{"TargetFile": "bank.chr"}],
        })
        assert len(cfg.export_chr) == 1
        assert cfg.export_chr[0].target_file == "bank.chr"


# ---------------------------------------------------------------------------
# NexxtporterConfig
# ---------------------------------------------------------------------------

class TestNexxtporterConfig:
    def test_empty_dict_uses_defaults(self):
        cfg = NexxtporterConfig.from_dict({})
        assert cfg.log_config.echo is True
        assert cfg.nss_files == []
        assert cfg.rgb_lookup_tables == []

    def test_full_config(self):
        data = {
            "LogConfig": {"Echo": False, "LogFile": "log.txt"},
            "NSSFiles": [{"SourceFile": "game.nss"}],
            "RGBLookupTables": [
                {"ID": "custom", "Colors": ["#FFFFFF"] * 64}
            ],
        }
        cfg = NexxtporterConfig.from_dict(data)
        assert cfg.log_config.echo is False
        assert cfg.log_config.log_file == "log.txt"
        assert len(cfg.nss_files) == 1
        assert len(cfg.rgb_lookup_tables) == 1
        assert cfg.rgb_lookup_tables[0].id == "custom"
