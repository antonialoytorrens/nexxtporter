"""Tests for nexxtporter.models — NES data structure parsing."""

import pytest

from nexxtporter.models import AttributeTable, Palette, PaletteSet, Pattern


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

class TestPalette:
    def test_parse_valid(self):
        raw = bytes(range(16))
        palette = Palette.parse(raw, 4)
        assert palette is not None
        assert palette.parsed_data == bytes([4, 5, 6, 7])
        assert palette.raw_data_start == 4

    def test_parse_at_start(self):
        raw = bytes([0x0F, 0x21, 0x16, 0x30])
        palette = Palette.parse(raw, 0)
        assert palette is not None
        assert palette.parsed_data == bytes([0x0F, 0x21, 0x16, 0x30])

    def test_parse_returns_none_if_too_short(self):
        raw = bytes([0x01, 0x02, 0x03])  # only 3 bytes, need 4
        assert Palette.parse(raw, 0) is None

    def test_parse_returns_none_if_offset_out_of_range(self):
        raw = bytes(8)
        assert Palette.parse(raw, 6) is None  # 6 + 4 = 10 > 8

    def test_constructor_rejects_wrong_parsed_data_length(self):
        with pytest.raises(ValueError):
            Palette(raw_data=b"\x00" * 4, raw_data_start=0, parsed_data=b"\x01\x02\x03")

    def test_immutable(self):
        raw = bytes(4)
        p = Palette.parse(raw, 0)
        with pytest.raises((AttributeError, TypeError)):
            p.raw_data_start = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PaletteSet
# ---------------------------------------------------------------------------

class TestPaletteSet:
    def test_parse_valid(self):
        raw = bytes(range(32))
        ps = PaletteSet.parse(raw, 0)
        assert ps is not None
        assert len(ps.palettes) == 4
        assert ps.palettes[0].parsed_data == bytes([0, 1, 2, 3])
        assert ps.palettes[3].parsed_data == bytes([12, 13, 14, 15])

    def test_parse_returns_none_if_too_short(self):
        raw = bytes(15)  # need 16
        assert PaletteSet.parse(raw, 0) is None

    def test_parse_with_offset(self):
        raw = bytes(32)
        ps = PaletteSet.parse(raw, 16)
        assert ps is not None
        assert ps.raw_data_start == 16

    def test_constructor_rejects_wrong_palette_count(self):
        raw = bytes(16)
        palettes = tuple(Palette.parse(raw, i * 4) for i in range(3))
        with pytest.raises(ValueError):
            PaletteSet(raw_data=raw, raw_data_start=0, palettes=palettes)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------

def _make_chr_bytes(low: list[int], high: list[int]) -> bytes:
    """Build 16 CHR bytes from two lists of 8 bit-plane bytes."""
    assert len(low) == 8 and len(high) == 8
    return bytes(low + high)


class TestPattern:
    def test_parse_all_zeros_gives_zero_pixels(self):
        raw = bytes(16)
        p = Pattern.parse(raw, 0)
        assert p is not None
        assert all(b == 0 for b in p.parsed_data)
        assert len(p.parsed_data) == 64

    def test_parse_all_ones_low_plane(self):
        # Low bit-plane all 0xFF, high all 0x00 → every pixel = 1
        raw = _make_chr_bytes([0xFF] * 8, [0x00] * 8)
        p = Pattern.parse(raw, 0)
        assert p is not None
        assert all(b == 1 for b in p.parsed_data)

    def test_parse_all_ones_high_plane(self):
        # Low = 0x00, high = 0xFF → every pixel = 2
        raw = _make_chr_bytes([0x00] * 8, [0xFF] * 8)
        p = Pattern.parse(raw, 0)
        assert p is not None
        assert all(b == 2 for b in p.parsed_data)

    def test_parse_both_planes(self):
        # Low = high = 0xFF → every pixel = 3
        raw = _make_chr_bytes([0xFF] * 8, [0xFF] * 8)
        p = Pattern.parse(raw, 0)
        assert p is not None
        assert all(b == 3 for b in p.parsed_data)

    def test_parse_single_pixel_top_left(self):
        # Only bit 7 (leftmost) of row 0 set in low plane
        low  = [0b10000000] + [0] * 7
        high = [0] * 8
        raw = _make_chr_bytes(low, high)
        p = Pattern.parse(raw, 0)
        assert p is not None
        assert p.parsed_data[0] == 1   # top-left pixel
        assert p.parsed_data[1] == 0   # rest zero

    def test_parse_returns_none_if_too_short(self):
        assert Pattern.parse(bytes(15), 0) is None

    def test_parse_with_offset(self):
        raw = bytes(32)
        p = Pattern.parse(raw, 16)
        assert p is not None
        assert p.raw_data_start == 16

    def test_constructor_rejects_wrong_parsed_data_length(self):
        with pytest.raises(ValueError):
            Pattern(raw_data=bytes(16), raw_data_start=0, parsed_data=bytes(63))


# ---------------------------------------------------------------------------
# AttributeTable
# ---------------------------------------------------------------------------

class TestAttributeTable:
    def _zeroed_table(self) -> AttributeTable:
        return AttributeTable.parse(bytes(64))

    def test_parse_zeroed_data(self):
        table = AttributeTable.parse(bytes(64))
        assert table is not None
        assert len(table.parsed_data) == 1024
        assert all(b == 0 for b in table.parsed_data)

    def test_parse_returns_none_for_wrong_size(self):
        assert AttributeTable.parse(bytes(63)) is None
        assert AttributeTable.parse(bytes(65)) is None

    def test_get_for_position_valid(self):
        table = self._zeroed_table()
        assert table.get_for_position(0, 0) == 0
        assert table.get_for_position(31, 31) == 0

    def test_get_for_position_out_of_bounds(self):
        table = self._zeroed_table()
        with pytest.raises(ValueError):
            table.get_for_position(-1, 0)
        with pytest.raises(ValueError):
            table.get_for_position(0, 32)
        with pytest.raises(ValueError):
            table.get_for_position(32, 0)

    def test_upper_left_quadrant_selector(self):
        # Attribute byte at index 0 covers tiles (0,0)–(3,3).
        # Bits 1:0 → upper-left 2×2 quadrant (tiles 0–1, 0–1)
        raw = bytearray(64)
        raw[0] = 0b00000011  # UL = 3
        table = AttributeTable.parse(bytes(raw))
        assert table is not None
        assert table.get_for_position(0, 0) == 3
        assert table.get_for_position(1, 1) == 3
        assert table.get_for_position(2, 0) == 0  # UR quadrant → still 0

    def test_upper_right_quadrant_selector(self):
        raw = bytearray(64)
        raw[0] = 0b00001100  # UR bits 3:2 = 3
        table = AttributeTable.parse(bytes(raw))
        assert table is not None
        assert table.get_for_position(2, 0) == 3
        assert table.get_for_position(3, 1) == 3
        assert table.get_for_position(0, 0) == 0  # UL still 0

    def test_lower_left_quadrant_selector(self):
        raw = bytearray(64)
        raw[0] = 0b00110000  # LL bits 5:4 = 3
        table = AttributeTable.parse(bytes(raw))
        assert table is not None
        assert table.get_for_position(0, 2) == 3
        assert table.get_for_position(1, 3) == 3

    def test_lower_right_quadrant_selector(self):
        raw = bytearray(64)
        raw[0] = 0b11000000  # LR bits 7:6 = 3
        table = AttributeTable.parse(bytes(raw))
        assert table is not None
        assert table.get_for_position(2, 2) == 3
        assert table.get_for_position(3, 3) == 3
