"""Logger: accumulates log/error messages and optionally writes them to a file."""

from __future__ import annotations

from pathlib import Path


class Logger:
    """Collects log and error messages, echoes to stdout, and writes a log file."""

    def __init__(self, echo: bool = True, log_file: Path | None = None) -> None:
        self._echo = echo
        self._log_file = log_file
        self._log_lines: list[str] = []
        self._error_lines: list[str] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        """Record an informational message."""
        self._log_lines.append(message)
        if self._echo:
            print(message)

    def log_error(self, message: str, exc: Exception | None = None) -> None:
        """Record an error message and optional exception details."""
        self._log_lines.append(message)
        self._error_lines.append(message)
        if self._echo:
            print(f"ERROR: {message}")

        if exc is not None:
            exc_text = f"Exception Info:\n{exc}"
            self._log_lines.append(exc_text)
            self._error_lines.append(exc_text)
            if self._echo:
                print(exc_text)

    def write_log_file(self) -> None:
        """Write accumulated log contents to the configured log file."""
        if self._log_file is None:
            return

        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with self._log_file.open("w", encoding="utf-8") as fh:
                fh.write("NexxtPorter Log\n")
                fh.write("-" * 80 + "\n")
                fh.write("\n".join(self._log_lines) + "\n")
                fh.write("ERRORS\n")
                fh.write("-" * 80 + "\n")
                fh.write("\n".join(self._error_lines) + "\n")
        except OSError as e:
            print(f"Failed to write log file {self._log_file}: {e}")

    # ------------------------------------------------------------------
    # Accessors (used in tests)
    # ------------------------------------------------------------------

    @property
    def log_lines(self) -> list[str]:
        return list(self._log_lines)

    @property
    def error_lines(self) -> list[str]:
        return list(self._error_lines)
