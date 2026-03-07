"""Configuration dataclasses mirroring the JSON config file structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class BitmapLayout(IntEnum):
    """Layout modes for ExportBitmap."""
    LINEAR    = 0  # All tiles in a single row left-to-right
    RECT      = 1  # Tiles in rows 16 tiles wide
    RECT8BY16 = 2  # Rows 16 wide, arranged for NES 8×16 sprite mode


# ---------------------------------------------------------------------------
# Sub-configs
# ---------------------------------------------------------------------------

@dataclass
class LoggerConfig:
    echo: bool = True
    log_file: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoggerConfig:
        return cls(
            echo=data.get("Echo", True),
            log_file=data.get("LogFile"),
        )


@dataclass
class RGBLookupConfig:
    id: str
    colors: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RGBLookupConfig:
        return cls(
            id=data["ID"],
            colors=data["Colors"],
        )


@dataclass
class ExportCHRConfig:
    target_file: str
    start: str = "0"
    size: str = "1024"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportCHRConfig:
        return cls(
            target_file=data["TargetFile"],
            start=data.get("Start", "0"),
            size=data.get("Size", "1024"),
        )


@dataclass
class ExportPaletteConfig:
    target_file: str
    target_segment_name: str | None = None
    target_variable_name: str | None = None
    target_append: bool = False
    source_sub_palette: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportPaletteConfig:
        return cls(
            target_file=data["TargetFile"],
            target_segment_name=data.get("TargetSegmentName"),
            target_variable_name=data.get("TargetVariableName"),
            target_append=data.get("TargetAppend", False),
            source_sub_palette=data.get("SourceSubPalette", 0),
        )


@dataclass
class ExportNametableConfig:
    target_file: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportNametableConfig:
        return cls(target_file=data["TargetFile"])


@dataclass
class ExportNametableAttributesConfig:
    target_file: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportNametableAttributesConfig:
        return cls(target_file=data["TargetFile"])


@dataclass
class ExportBitmapConfig:
    target_file: str
    start_tile_index: str = "0"
    tile_count: str = "256"
    layout: BitmapLayout = BitmapLayout.LINEAR
    rgb_lookup_id: str = "Default"
    palette_set_index: str = "0"
    palette_index: str = "0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportBitmapConfig:
        layout_value = data.get("Layout", 0)
        try:
            layout = BitmapLayout(int(layout_value))
        except (ValueError, KeyError):
            layout = BitmapLayout.LINEAR

        return cls(
            target_file=data["TargetFile"],
            start_tile_index=data.get("StartTileIndex", "0"),
            tile_count=data.get("TileCount", "256"),
            layout=layout,
            rgb_lookup_id=data.get("RGBLookupID", "Default"),
            palette_set_index=data.get("PaletteSetIndex", "0"),
            palette_index=data.get("PaletteIndex", "0"),
        )


@dataclass
class ExportNametableBitmapConfig:
    target_file: str
    rgb_lookup_id: str = "Default"
    chr_index: str = "0"
    palette_set_index: str = "0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportNametableBitmapConfig:
        return cls(
            target_file=data["TargetFile"],
            rgb_lookup_id=data.get("RGBLookupID", "Default"),
            chr_index=data.get("CHRIndex", "0"),
            palette_set_index=data.get("PaletteSetIndex", "0"),
        )


# ---------------------------------------------------------------------------
# NSS file config
# ---------------------------------------------------------------------------

@dataclass
class NSSConfig:
    source_file: str
    export_chr: list[ExportCHRConfig] = field(default_factory=list)
    export_palette: list[ExportPaletteConfig] = field(default_factory=list)
    export_nametable: list[ExportNametableConfig] = field(default_factory=list)
    export_nametable_attributes: list[ExportNametableAttributesConfig] = field(default_factory=list)
    export_bitmap: list[ExportBitmapConfig] = field(default_factory=list)
    export_nametable_bitmap: list[ExportNametableBitmapConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NSSConfig:
        return cls(
            source_file=data["SourceFile"],
            export_chr=[ExportCHRConfig.from_dict(d) for d in data.get("ExportCHR", [])],
            export_palette=[ExportPaletteConfig.from_dict(d) for d in data.get("ExportPalette", [])],
            export_nametable=[ExportNametableConfig.from_dict(d) for d in data.get("ExportNametable", [])],
            export_nametable_attributes=[
                ExportNametableAttributesConfig.from_dict(d)
                for d in data.get("ExportNametableAttributes", [])
            ],
            export_bitmap=[ExportBitmapConfig.from_dict(d) for d in data.get("ExportBitmap", [])],
            export_nametable_bitmap=[
                ExportNametableBitmapConfig.from_dict(d)
                for d in data.get("ExportNametableBitmap", [])
            ],
        )


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------

@dataclass
class NexxtporterConfig:
    log_config: LoggerConfig = field(default_factory=LoggerConfig)
    nss_files: list[NSSConfig] = field(default_factory=list)
    rgb_lookup_tables: list[RGBLookupConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NexxtporterConfig:
        log_config = (
            LoggerConfig.from_dict(data["LogConfig"])
            if "LogConfig" in data
            else LoggerConfig()
        )
        return cls(
            log_config=log_config,
            nss_files=[NSSConfig.from_dict(d) for d in data.get("NSSFiles", [])],
            rgb_lookup_tables=[
                RGBLookupConfig.from_dict(d) for d in data.get("RGBLookupTables", [])
            ],
        )
