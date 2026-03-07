"""Immutable data models for NES graphics structures.

Each model exposes a class-method ``parse`` factory that validates the raw
binary data and returns ``None`` on failure instead of raising.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Palette (4 bytes — one sub-palette)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Palette:
    """A single 4-colour NES sub-palette extracted from raw palette data."""

    raw_data: bytes
    raw_data_start: int
    parsed_data: bytes  # Always exactly 4 bytes

    def __post_init__(self) -> None:
        if len(self.parsed_data) != 4:
            raise ValueError("parsed_data must contain exactly 4 bytes")

    @classmethod
    def parse(cls, raw_data: bytes, raw_data_start: int) -> Palette | None:
        """Return a Palette from *raw_data* at *raw_data_start*, or None."""
        if raw_data_start + 4 > len(raw_data):
            return None
        parsed = raw_data[raw_data_start : raw_data_start + 4]
        return cls(raw_data=raw_data, raw_data_start=raw_data_start, parsed_data=parsed)


# ---------------------------------------------------------------------------
# PaletteSet (16 bytes — 4 sub-palettes)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PaletteSet:
    """A set of 4 sub-palettes (one palette-set as stored in NSS files)."""

    raw_data: bytes
    raw_data_start: int
    palettes: tuple[Palette, ...]  # Always 4 elements

    def __post_init__(self) -> None:
        if len(self.palettes) != 4:
            raise ValueError("palettes must contain exactly 4 palettes")

    @classmethod
    def parse(cls, raw_data: bytes, raw_data_start: int) -> PaletteSet | None:
        """Return a PaletteSet from *raw_data* at *raw_data_start*, or None."""
        if raw_data_start + 16 > len(raw_data):
            return None
        palettes: list[Palette] = []
        for i in range(4):
            palette = Palette.parse(raw_data, raw_data_start + 4 * i)
            if palette is None:
                return None
            palettes.append(palette)
        return cls(
            raw_data=raw_data,
            raw_data_start=raw_data_start,
            palettes=tuple(palettes),
        )


# ---------------------------------------------------------------------------
# Pattern (16 bytes CHR → 64 pixel palette indices)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Pattern:
    """An 8×8 tile decoded from NES CHR data.

    Each element of ``parsed_data`` is a palette index 0–3 for one pixel,
    stored in row-major order (left-to-right, top-to-bottom).
    """

    raw_data: bytes
    raw_data_start: int
    parsed_data: bytes  # Always exactly 64 bytes

    def __post_init__(self) -> None:
        if len(self.parsed_data) != 64:
            raise ValueError("parsed_data must contain exactly 64 bytes")

    @classmethod
    def parse(cls, raw_data: bytes, raw_data_start: int) -> Pattern | None:
        """Decode a 16-byte CHR tile into 64 palette indices, or return None.

        NES CHR format (https://www.nesdev.org/wiki/PPU_pattern_tables):
        - Bytes 0–7:  low bit-plane
        - Bytes 8–15: high bit-plane
        - Pixel colour = (high_bit << 1) | low_bit  → value 0–3
        """
        if raw_data_start + 16 > len(raw_data):
            return None

        pixels = bytearray(64)
        idx = 0
        for y in range(8):
            low_byte  = raw_data[raw_data_start + y]
            high_byte = raw_data[raw_data_start + y + 8]
            for x in range(8):
                bit = 7 - x
                low  = (low_byte  >> bit) & 1
                high = (high_byte >> bit) & 1
                pixels[idx] = (high << 1) | low
                idx += 1

        return cls(
            raw_data=raw_data,
            raw_data_start=raw_data_start,
            parsed_data=bytes(pixels),
        )


# ---------------------------------------------------------------------------
# AttributeTable (64 raw bytes → 1024 per-tile palette selectors)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AttributeTable:
    """NES PPU attribute table decoded to per-tile palette selectors.

    ``parsed_data`` has one byte per tile in the 32×30 nametable (stored as
    32×32 for simplicity), giving the 2-bit palette selector for that tile.
    """

    raw_data: bytes
    parsed_data: bytes  # Always exactly 1024 bytes (32×32)

    def __post_init__(self) -> None:
        if len(self.parsed_data) != 1024:
            raise ValueError("parsed_data must contain exactly 1024 bytes")

    @classmethod
    def parse(cls, raw_data: bytes) -> AttributeTable | None:
        """Decode 64 raw attribute bytes into per-tile selectors, or None.

        Reference: https://www.nesdev.org/wiki/PPU_attribute_tables
        Each attribute byte controls a 4×4 block of tiles split into four
        2×2 quadrants (UL, UR, LL, LR), each holding a 2-bit palette index.
        """
        if len(raw_data) != 64:
            return None

        parsed = bytearray(1024)
        for y in range(32):
            for x in range(32):
                attr_x = x >> 2
                attr_y = y >> 2
                attr_byte = raw_data[attr_y * 8 + attr_x]

                if x % 4 < 2:
                    selector = (attr_byte & 0b00000011) if y % 4 < 2 else (attr_byte & 0b00110000) >> 4
                else:
                    selector = (attr_byte & 0b00001100) >> 2 if y % 4 < 2 else (attr_byte & 0b11000000) >> 6

                parsed[y * 32 + x] = selector

        return cls(raw_data=raw_data, parsed_data=bytes(parsed))

    def get_for_position(self, x: int, y: int) -> int:
        """Return the palette selector for tile at grid position (x, y)."""
        if not (0 <= x < 32):
            raise ValueError(f"x out of bounds: {x}")
        if not (0 <= y < 32):
            raise ValueError(f"y out of bounds: {y}")
        return self.parsed_data[y * 32 + x]
