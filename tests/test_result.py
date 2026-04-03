"""Unit tests for CandeResult."""

from pathlib import Path

from cande_wrapper.engine import CandeResult


class TestCandeResult:
    def test_paths(self, tmp_path):
        result = CandeResult(tmp_path, "EX1")
        assert result.output_file == tmp_path / "EX1.out"
        assert result.log_file == tmp_path / "EX1.log"
        assert result.toc_file == tmp_path / "EX1.ctc"

    def test_prefix(self, tmp_path):
        result = CandeResult(tmp_path, "test_problem")
        assert result.prefix == "test_problem"

    def test_repr(self, tmp_path):
        result = CandeResult(tmp_path, "EX1")
        r = repr(result)
        assert "EX1" in r
        assert "CandeResult" in r

    def test_output_text(self, tmp_path):
        (tmp_path / "EX1.out").write_text("line 1\nline 2\n")
        result = CandeResult(tmp_path, "EX1")
        assert result.output_text == "line 1\nline 2\n"

    def test_output_text_missing_file(self, tmp_path):
        result = CandeResult(tmp_path, "EX1")
        try:
            _ = result.output_text
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass
