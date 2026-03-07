"""RGB lookup tables that map NES palette indices to RGB colour values."""

from __future__ import annotations

from dataclasses import dataclass

# RGB triple: (red, green, blue) each 0–255
Color = tuple[int, int, int]

# Default NES palette colours — identical to those used by Nexxt.
_DEFAULT_HEX_COLORS: list[str] = [
    "6A6D6A", "001380", "1E008A", "39007A", "550056", "5A0018", "4F1000", "3D1C00",
    "253200", "003D00", "004000", "003924", "002E55", "000000", "000000", "000000",
    "B9BCB9", "1850C7", "4B30E3", "7322D6", "951FA9", "9D285C", "983700", "7F4C00",
    "5E6400", "227700", "027E02", "007645", "006E8A", "000000", "000000", "000000",
    "FFFFFF", "68A6FF", "8C9CFF", "B586FF", "D975FD", "E377B9", "E58D68", "D49D29",
    "B3AF0C", "7BC211", "55CA47", "46CB81", "47C1C5", "4A4D4A", "000000", "000000",
    "FFFFFF", "CCEAFF", "DDDEFF", "ECDAFF", "F8D7FE", "FCD6F5", "FDDBCF", "F9E7B5",
    "F1F0AA", "DAFAA9", "C9FFBC", "C3FBD7", "C4F6F6", "BEC1BE", "000000", "000000",
]


def parse_color(hex_str: str) -> Color:
    """Parse a hex color string (with or without leading ``#``) to an RGB tuple."""
    hex_str = hex_str.lstrip("#").strip()
    if len(hex_str) != 6:
        raise ValueError(f"Invalid hex color string: '{hex_str}'")
    return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


@dataclass(frozen=True)
class RGBLookup:
    """An immutable table mapping the 64 NES palette indices to RGB colours."""

    id: str
    colors: tuple[Color, ...]  # Always exactly 64 entries

    def __post_init__(self) -> None:
        if len(self.colors) != 64:
            raise ValueError(f"colors must contain exactly 64 entries, got {len(self.colors)}")

    def get_color(self, nes_index: int) -> Color:
        """Return the RGB color for NES palette index *nes_index*."""
        return self.colors[nes_index]

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def default(cls) -> RGBLookup:
        """Return the built-in default NES palette (matches Nexxt)."""
        colors = tuple(parse_color(h) for h in _DEFAULT_HEX_COLORS)
        return cls(id="Default", colors=colors)

    @classmethod
    def from_config(cls, lookup_id: str, hex_colors: list[str]) -> RGBLookup:
        """Build an RGBLookup from an ID and a list of 64 hex color strings."""
        if len(hex_colors) != 64:
            raise ValueError(
                f"colors must contain exactly 64 entries, got {len(hex_colors)}"
            )
        colors = tuple(parse_color(h) for h in hex_colors)
        return cls(id=lookup_id, colors=colors)


class RGBLookupRegistry:
    """Holds named RGBLookup tables and provides lookup by ID."""

    def __init__(self) -> None:
        self._tables: dict[str, RGBLookup] = {}

    def add(self, lookup: RGBLookup) -> None:
        self._tables[lookup.id] = lookup

    def get(self, lookup_id: str) -> RGBLookup:
        if lookup_id not in self._tables:
            raise KeyError(f"RGB lookup table '{lookup_id}' not found")
        return self._tables[lookup_id]

    def __contains__(self, lookup_id: str) -> bool:
        return lookup_id in self._tables
