"""Tests for nexxtporter.utils — number parsing, RLE decoding, file writing."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexxtporter.utils import (
    format_byte_line,
    parse_number,
    parse_rle_binary,
    write_binary_file,
)


# ---------------------------------------------------------------------------
# parse_number
# ---------------------------------------------------------------------------

class TestParseNumber:
    def test_decimal(self):
        assert parse_number("100") == 100

    def test_decimal_zero(self):
        assert parse_number("0") == 0

    def test_hex_lowercase_prefix(self):
        assert parse_number("$100") == 256

    def test_hex_leading_zeros(self):
        assert parse_number("$0400") == 1024

    def test_binary(self):
        assert parse_number("%10000000") == 128

    def test_binary_all_ones(self):
        assert parse_number("%11111111") == 255

    def test_none_returns_none(self):
        assert parse_number(None) is None

    def test_empty_string_returns_none(self):
        assert parse_number("") is None

    def test_whitespace_returns_none(self):
        assert parse_number("   ") is None

    def test_invalid_string_returns_none(self):
        assert parse_number("abc") is None

    def test_invalid_hex_returns_none(self):
        assert parse_number("$ZZZZ") is None

    def test_whitespace_stripped(self):
        assert parse_number("  42  ") == 42


# ---------------------------------------------------------------------------
# parse_rle_binary
# ---------------------------------------------------------------------------

class TestParseRleBinary:
    def _make_log(self):
        return MagicMock()

    def test_empty_string_returns_empty(self):
        log = self._make_log()
        assert parse_rle_binary(log, "src.nss", "tok", "") == b""
        log.log_error.assert_not_called()

    def test_whitespace_returns_empty(self):
        log = self._make_log()
        assert parse_rle_binary(log, "src.nss", "tok", "   ") == b""

    def test_simple_hex_data(self):
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "AABB")
        assert result == bytes([0xAA, 0xBB])
        log.log_error.assert_not_called()

    def test_rle_repeats_last_byte(self):
        # "AABB[03]" → AA BB BB BB  (BB appears 3 times total)
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "AABB[03]")
        assert result == bytes([0xAA, 0xBB, 0xBB, 0xBB])

    def test_rle_at_end_is_fine(self):
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "AA[02]")
        assert result == bytes([0xAA, 0xAA])

    def test_rle_in_middle(self):
        # "AA[02]BB" → AA AA BB
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "AA[02]BB")
        assert result == bytes([0xAA, 0xAA, 0xBB])

    def test_multiple_rle_segments(self):
        # "AA[02]BB[02]" → AA AA BB BB
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "AA[02]BB[02]")
        assert result == bytes([0xAA, 0xAA, 0xBB, 0xBB])

    def test_rle_hex_count(self):
        # "FF[0A]" → FF × 10
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "FF[0A]")
        assert result == bytes([0xFF] * 10)

    def test_invalid_rle_count_one_logs_error(self):
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "AA[01]")
        assert result == b""
        log.log_error.assert_called_once()

    def test_odd_length_data_logs_error(self):
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "ABC")
        assert result == b""
        log.log_error.assert_called_once()

    def test_rle_without_preceding_data_logs_error(self):
        # Starts with RLE segment → last_chunk is empty
        log = self._make_log()
        result = parse_rle_binary(log, "src.nss", "tok", "[03]AA")
        assert result == b""
        log.log_error.assert_called_once()


# ---------------------------------------------------------------------------
# format_byte_line
# ---------------------------------------------------------------------------

class TestFormatByteLine:
    def test_single_byte(self):
        assert format_byte_line(bytes([0x00]), 0, 1) == ".byte $00"

    def test_four_bytes(self):
        result = format_byte_line(bytes([0x19, 0x21, 0x0F, 0x30]), 0, 4)
        assert result == ".byte $19,$21,$0F,$30"

    def test_with_offset(self):
        data = bytes([0x00, 0x01, 0xAA, 0xBB])
        assert format_byte_line(data, 2, 2) == ".byte $AA,$BB"

    def test_uppercase_hex(self):
        result = format_byte_line(bytes([0xab, 0xcd]), 0, 2)
        assert result == ".byte $AB,$CD"


# ---------------------------------------------------------------------------
# write_binary_file
# ---------------------------------------------------------------------------

class TestWriteBinaryFile:
    def test_writes_slice_to_file(self, tmp_path):
        log = MagicMock()
        data = bytes(range(16))
        target = tmp_path / "out.chr"
        write_binary_file(log, target, data, 4, 4)
        assert target.read_bytes() == bytes([4, 5, 6, 7])
        log.log_error.assert_not_called()

    def test_creates_parent_directories(self, tmp_path):
        log = MagicMock()
        target = tmp_path / "sub" / "nested" / "out.bin"
        write_binary_file(log, target, b"\x01\x02", 0, 2)
        assert target.exists()

    def test_invalid_range_logs_error(self, tmp_path):
        log = MagicMock()
        target = tmp_path / "out.bin"
        write_binary_file(log, target, bytes(4), 2, 4)  # 2+4 > 4
        log.log_error.assert_called_once()
        assert not target.exists()

    def test_negative_start_logs_error(self, tmp_path):
        log = MagicMock()
        target = tmp_path / "out.bin"
        write_binary_file(log, target, bytes(4), -1, 2)
        log.log_error.assert_called_once()
