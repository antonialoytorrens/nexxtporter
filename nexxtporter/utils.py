"""Utility functions shared across the exporter modules."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexxtporter.logger import Logger


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

def parse_number(value: str | None) -> int | None:
    """Parse a numeric string in decimal, hex (``$``), or binary (``%``) format.

    Returns ``None`` if *value* is empty, whitespace-only, or unparseable.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    try:
        if value.startswith("$"):
            return int(value[1:], 16)
        if value.startswith("%"):
            return int(value[1:], 2)
        return int(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# RLE-encoded binary parsing
# ---------------------------------------------------------------------------

def parse_rle_binary(
    log: Logger,
    source_file: str,
    token: str,
    encoded: str,
) -> bytes:
    """Decode the RLE-compressed hex binary format used in NSS files.

    Format: alternating *data* and *repeat-count* segments:
    ``AABBCC[0A]DDEEFF[02]...``

    - Data segments are pairs of hex digits (``AABB`` → bytes 0xAA, 0xBB).
    - ``[N]`` (hex) means repeat the **last byte** of the preceding data
      segment N times total (so N−1 additional copies are written).
    - ``[01]`` or ``[00]`` is invalid (minimum repeat count is 2).

    Returns ``b""`` and logs an error on any parsing failure.
    """
    if not encoded or not encoded.strip():
        return b""

    # Split by '[' and ']' to get alternating data / count segments.
    # Even indices → data hex strings, odd indices → hex repeat counts.
    segments = re.split(r"[\[\]]", encoded)

    # --- First pass: validate and compute total output size ---
    output_size = 0
    for i, segment in enumerate(segments):
        if i % 2 == 0:  # data segment
            if len(segment) % 2 != 0:
                log.log_error(
                    f"Binary data segment has odd number of characters "
                    f"in token '{token}' in NSS file '{source_file}'"
                )
                return b""
            output_size += len(segment) // 2
        else:  # RLE count segment
            try:
                rle_count = int(segment, 16)
            except ValueError:
                log.log_error(
                    f"Invalid RLE count '{segment}' in token '{token}' "
                    f"in NSS file '{source_file}'"
                )
                return b""
            if rle_count <= 1:
                log.log_error(
                    f"Invalid RLE count {rle_count} (must be ≥ 2) "
                    f"in token '{token}' in NSS file '{source_file}'"
                )
                return b""
            output_size += rle_count - 1  # one copy already in the data segment

    # --- Second pass: build output buffer ---
    output = bytearray(output_size)
    write_idx = 0
    last_chunk: bytes = b""

    for i, segment in enumerate(segments):
        if i % 2 == 0:  # data segment
            chunk = bytes.fromhex(segment) if segment else b""
            for byte_val in chunk:
                output[write_idx] = byte_val
                write_idx += 1
            last_chunk = chunk  # always update (even if empty)
        else:  # RLE count segment
            if not last_chunk:
                log.log_error(
                    f"RLE segment found with no preceding data "
                    f"in token '{token}' in NSS file '{source_file}'"
                )
                return b""
            rle_count = int(segment, 16)
            last_byte = last_chunk[-1]
            for _ in range(rle_count - 1):
                output[write_idx] = last_byte
                write_idx += 1

    if write_idx != len(output):
        log.log_error(
            f"Output size mismatch in token '{token}' in NSS file '{source_file}'"
        )
        return b""

    return bytes(output)


# ---------------------------------------------------------------------------
# File writing helpers
# ---------------------------------------------------------------------------

def write_binary_file(
    log: Logger,
    target_file: Path,
    data: bytes,
    start: int,
    size: int,
) -> None:
    """Write a slice of *data* to *target_file* as raw bytes."""
    if start < 0 or start + size > len(data):
        log.log_error(
            f"Invalid range [{start}, {start + size}) for buffer of "
            f"{len(data)} bytes when writing '{target_file}'"
        )
        return
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_bytes(data[start : start + size])
    except OSError as e:
        log.log_error(f"Error writing {size} bytes to '{target_file}'", e)


def format_byte_line(data: bytes, start: int, count: int) -> str:
    """Return a ca65 ``.byte`` directive for *count* bytes at *start*.

    Example: ``format_byte_line(b'\\x19\\x21\\x0f\\x30', 0, 4)``
    → ``".byte $19,$21,$0F,$30"``
    """
    values = ",".join(f"${data[start + i]:02X}" for i in range(count))
    return f".byte {values}"
