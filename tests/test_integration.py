"""Integration tests that require the compiled Fortran extension.

Run with: pytest -m integration
These are skipped by default in normal test runs.
"""

import shutil
from pathlib import Path

import pytest

from cande_wrapper.engine import CandeEngine

EXAMPLE_DATA = Path(__file__).parent / "example_data"


@pytest.mark.integration
class TestIntegration:
    def test_run_example_problem(self, tmp_path):
        """Run the MGK-IO example and verify CANDE completes normally."""
        shutil.copy2(EXAMPLE_DATA / "MGK-IO.cid", tmp_path / "MGK-IO.cid")

        engine = CandeEngine(work_dir=tmp_path)
        result = engine.run("MGK-IO")

        assert result.output_file.exists()
        output = result.output_text
        assert "NORMAL EXIT FROM CANDE" in output

    def test_output_files_created(self, tmp_path):
        """Verify all expected output files are created."""
        shutil.copy2(EXAMPLE_DATA / "MGK-IO.cid", tmp_path / "MGK-IO.cid")

        engine = CandeEngine(work_dir=tmp_path)
        result = engine.run("MGK-IO")

        assert result.output_file.exists()
        assert result.log_file.exists()
        assert result.toc_file.exists()
