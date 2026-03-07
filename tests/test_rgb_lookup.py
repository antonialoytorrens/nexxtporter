"""Tests for nexxtporter.rgb_lookup."""

import pytest

from nexxtporter.rgb_lookup import RGBLookup, RGBLookupRegistry, parse_color


# ---------------------------------------------------------------------------
# parse_color
# ---------------------------------------------------------------------------

class TestParseColor:
    def test_no_hash(self):
        assert parse_color("AABBCC") == (0xAA, 0xBB, 0xCC)

    def test_with_hash(self):
        assert parse_color("#AABBCC") == (0xAA, 0xBB, 0xCC)

    def test_all_zeros(self):
        assert parse_color("000000") == (0, 0, 0)

    def test_all_max(self):
        assert parse_color("FFFFFF") == (255, 255, 255)

    def test_invalid_length_raises(self):
        with pytest.raises(ValueError):
            parse_color("AAB")

    def test_invalid_hex_raises(self):
        with pytest.raises(ValueError):
            parse_color("GGHHII")


# ---------------------------------------------------------------------------
# RGBLookup
# ---------------------------------------------------------------------------

class TestRGBLookup:
    def test_default_has_64_colors(self):
        lookup = RGBLookup.default()
        assert len(lookup.colors) == 64

    def test_default_id(self):
        lookup = RGBLookup.default()
        assert lookup.id == "Default"

    def test_from_config_valid(self):
        colors = ["FFFFFF"] * 64
        lookup = RGBLookup.from_config("my_table", colors)
        assert lookup.id == "my_table"
        assert len(lookup.colors) == 64
        assert lookup.colors[0] == (255, 255, 255)

    def test_from_config_wrong_count_raises(self):
        with pytest.raises(ValueError):
            RGBLookup.from_config("bad", ["FFFFFF"] * 63)

    def test_get_color(self):
        colors = [f"{i:02X}{i:02X}{i:02X}" for i in range(64)]
        lookup = RGBLookup.from_config("t", colors)
        assert lookup.get_color(0) == (0, 0, 0)
        assert lookup.get_color(63) == (63, 63, 63)

    def test_constructor_rejects_wrong_count(self):
        with pytest.raises(ValueError):
            RGBLookup(id="x", colors=tuple((0, 0, 0) for _ in range(10)))

    def test_immutable(self):
        lookup = RGBLookup.default()
        with pytest.raises((AttributeError, TypeError)):
            lookup.id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RGBLookupRegistry
# ---------------------------------------------------------------------------

class TestRGBLookupRegistry:
    def _make_lookup(self, name: str = "test") -> RGBLookup:
        return RGBLookup.from_config(name, ["000000"] * 64)

    def test_add_and_get(self):
        reg = RGBLookupRegistry()
        lookup = self._make_lookup("myTable")
        reg.add(lookup)
        assert reg.get("myTable") is lookup

    def test_get_missing_raises_key_error(self):
        reg = RGBLookupRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_contains_true(self):
        reg = RGBLookupRegistry()
        reg.add(self._make_lookup("x"))
        assert "x" in reg

    def test_contains_false(self):
        reg = RGBLookupRegistry()
        assert "x" not in reg

    def test_add_overwrites_existing(self):
        reg = RGBLookupRegistry()
        first  = RGBLookup.from_config("id", ["000000"] * 64)
        second = RGBLookup.from_config("id", ["FFFFFF"] * 64)
        reg.add(first)
        reg.add(second)
        assert reg.get("id") is second
