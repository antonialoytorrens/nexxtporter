"""Export raw CHR (tile pattern) binary data from an NSS file."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nexxtporter.exporters.base import BaseExporter
from nexxtporter.utils import parse_number, parse_rle_binary, write_binary_file

if TYPE_CHECKING:
    from nexxtporter.config import ExportCHRConfig
    from nexxtporter.logger import Logger
    from nexxtporter.rgb_lookup import RGBLookupRegistry

_CHR_TOKEN = "CHRMain"
_DEFAULT_START = 0
_DEFAULT_SIZE  = 1024


class CHRExporter(BaseExporter):
    """Extracts a slice of CHR data from the NSS file and saves it as binary."""

    def __init__(self, log: Logger, nss_source: str, config: ExportCHRConfig) -> None:
        super().__init__(log, nss_source)
        self._config = config

    def export(self, tokens: dict[str, str], rgb_registry: RGBLookupRegistry) -> None:
        cfg = self._config

        start = parse_number(cfg.start)
        if start is None:
            self._log.log_error(
                f"NSS '{self._nss_source}': CHR export to '{cfg.target_file}' "
                f"has invalid Start '{cfg.start}'"
            )
            return

        size = parse_number(cfg.size)
        if size is None:
            self._log.log_error(
                f"NSS '{self._nss_source}': CHR export to '{cfg.target_file}' "
                f"has invalid Size '{cfg.size}'"
            )
            return

        if _CHR_TOKEN not in tokens:
            self._log.log_error(
                f"NSS '{self._nss_source}' has no '{_CHR_TOKEN}' token — "
                f"cannot export CHR to '{cfg.target_file}'"
            )
            return

        data = parse_rle_binary(self._log, self._nss_source, _CHR_TOKEN, tokens[_CHR_TOKEN])
        if len(data) < start + size:
            self._log.log_error(
                f"NSS '{self._nss_source}': CHRMain is {len(data)} bytes, "
                f"which is smaller than start={start} + size={size}"
            )
            return

        self._log.log(
            f"Writing CHR [{start}, {size}] bytes to '{cfg.target_file}'"
        )
        write_binary_file(self._log, Path(cfg.target_file), data, start, size)
