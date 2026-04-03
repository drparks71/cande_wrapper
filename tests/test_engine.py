"""Unit tests for CandeEngine."""

import os
from pathlib import Path

import pytest

from cande_wrapper.engine import CandeEngine


class TestCandeEngineInit:
    def test_default_workdir(self):
        engine = CandeEngine()
        assert engine.work_dir == Path.cwd()

    def test_custom_workdir_string(self, tmp_path):
        engine = CandeEngine(work_dir=str(tmp_path))
        assert engine.work_dir == tmp_path

    def test_custom_workdir_path(self, tmp_path):
        engine = CandeEngine(work_dir=tmp_path)
        assert engine.work_dir == tmp_path


class TestCheckInput:
    def test_exists(self, tmp_workdir):
        engine = CandeEngine(work_dir=tmp_workdir)
        assert engine.check_input("MGK-IO") is True

    def test_missing(self, tmp_path):
        engine = CandeEngine(work_dir=tmp_path)
        assert engine.check_input("nonexistent") is False


class TestRun:
    def test_missing_cid_raises(self, tmp_path):
        engine = CandeEngine(work_dir=tmp_path)
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            engine.run("nonexistent")

    def test_missing_extension_raises(self, tmp_workdir, monkeypatch):
        """Simulates missing _cande extension by blocking the import."""
        import sys

        # Remove cached module and make it unimportable
        monkeypatch.setitem(sys.modules, "cande_wrapper._cande", None)

        engine = CandeEngine(work_dir=tmp_workdir)
        with pytest.raises(ImportError):
            engine.run("MGK-IO")

    def test_success_returns_result(self, tmp_workdir, mock_fortran):
        # Create the .out file that CandeResult expects
        (tmp_workdir / "MGK-IO.out").write_text("NORMAL EXIT FROM CANDE")
        (tmp_workdir / "MGK-IO.log").write_text("")
        (tmp_workdir / "MGK-IO.ctc").write_text("")

        engine = CandeEngine(work_dir=tmp_workdir)
        result = engine.run("MGK-IO")

        mock_fortran.run_cande.assert_called_once_with("MGK-IO")
        assert result.prefix == "MGK-IO"
        assert result.output_file == tmp_workdir / "MGK-IO.out"

    def test_engine_error_raises(self, tmp_workdir, mock_fortran):
        mock_fortran.run_cande.return_value = 1

        engine = CandeEngine(work_dir=tmp_workdir)
        with pytest.raises(RuntimeError, match="error code 1"):
            engine.run("MGK-IO")

    def test_restores_cwd_on_success(self, tmp_workdir, mock_fortran):
        original = os.getcwd()
        engine = CandeEngine(work_dir=tmp_workdir)
        engine.run("MGK-IO")
        assert os.getcwd() == original

    def test_restores_cwd_on_error(self, tmp_workdir, mock_fortran):
        mock_fortran.run_cande.return_value = 1
        original = os.getcwd()
        engine = CandeEngine(work_dir=tmp_workdir)
        with pytest.raises(RuntimeError):
            engine.run("MGK-IO")
        assert os.getcwd() == original

    def test_restores_cwd_on_exception(self, tmp_workdir, mock_fortran):
        mock_fortran.run_cande.side_effect = Exception("boom")
        original = os.getcwd()
        engine = CandeEngine(work_dir=tmp_workdir)
        with pytest.raises(Exception, match="boom"):
            engine.run("MGK-IO")
        assert os.getcwd() == original
