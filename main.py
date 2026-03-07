"""Entry point for nexxtporter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from nexxtporter.config import NexxtporterConfig
from nexxtporter.logger import Logger
from nexxtporter.nss_file import NSSFile
from nexxtporter.rgb_lookup import RGBLookup, RGBLookupRegistry


def load_config(path: Path) -> NexxtporterConfig | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return NexxtporterConfig.from_dict(data)
    except FileNotFoundError:
        print(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file {path}: {e}")
    except (KeyError, ValueError) as e:
        print(f"Invalid config structure in {path}: {e}")
    return None


def build_rgb_registry(config: NexxtporterConfig, log: Logger) -> RGBLookupRegistry:
    registry = RGBLookupRegistry()
    registry.add(RGBLookup.default())

    for rgb_config in config.rgb_lookup_tables:
        try:
            lookup = RGBLookup.from_config(rgb_config.id, rgb_config.colors)
            registry.add(lookup)
        except (ValueError, KeyError) as e:
            log.log_error(f"Error parsing RGBLookupTable '{rgb_config.id}'", e)

    return registry


def main(argv: list[str]) -> int:
    config_path = Path(argv[0]) if argv else Path("config.json")

    if not config_path.name:
        print("Config file path is empty")
        return 1

    config = load_config(config_path)
    if config is None:
        return 1

    log_file = Path(config.log_config.log_file) if config.log_config.log_file else None
    log = Logger(echo=config.log_config.echo, log_file=log_file)

    if not config.nss_files:
        log.log_error("Config contains no NSSFiles entries")
        log.write_log_file()
        return 1

    rgb_registry = build_rgb_registry(config, log)

    for nss_config in config.nss_files:
        nss_file = NSSFile(log=log, config=nss_config, rgb_registry=rgb_registry)
        nss_file.process()

    log.write_log_file()
    print("Export Complete")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
