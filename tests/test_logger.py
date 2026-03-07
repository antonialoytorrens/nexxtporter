"""Tests for nexxtporter.logger.Logger."""

from pathlib import Path

from nexxtporter.logger import Logger


class TestLogger:
    def test_log_stores_message(self):
        log = Logger(echo=False)
        log.log("hello")
        assert "hello" in log.log_lines

    def test_log_error_in_both_collections(self):
        log = Logger(echo=False)
        log.log_error("something went wrong")
        assert "something went wrong" in log.log_lines
        assert "something went wrong" in log.error_lines

    def test_log_error_with_exception(self):
        log = Logger(echo=False)
        exc = ValueError("boom")
        log.log_error("oops", exc)
        combined = "\n".join(log.log_lines)
        assert "oops" in combined
        assert "boom" in combined

    def test_no_log_file_write_if_none(self, tmp_path):
        log = Logger(echo=False, log_file=None)
        log.log("a message")
        log.write_log_file()
        # Nothing should have been created
        assert list(tmp_path.iterdir()) == []

    def test_write_log_file_creates_file(self, tmp_path):
        log_path = tmp_path / "test.log"
        log = Logger(echo=False, log_file=log_path)
        log.log("info line")
        log.log_error("error line")
        log.write_log_file()

        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "NexxtPorter Log" in content
        assert "info line" in content
        assert "error line" in content
        assert "ERRORS" in content

    def test_write_log_file_creates_parent_dirs(self, tmp_path):
        log_path = tmp_path / "subdir" / "nested" / "test.log"
        log = Logger(echo=False, log_file=log_path)
        log.log("x")
        log.write_log_file()
        assert log_path.exists()

    def test_echo_false_does_not_print(self, capsys):
        log = Logger(echo=False)
        log.log("silent")
        log.log_error("also silent")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_echo_true_prints_to_stdout(self, capsys):
        log = Logger(echo=True)
        log.log("visible")
        captured = capsys.readouterr()
        assert "visible" in captured.out
