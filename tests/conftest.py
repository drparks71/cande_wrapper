"""Shared fixtures for cande-wrapper tests."""

import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

EXAMPLE_DATA = Path(__file__).parent / "example_data"


@pytest.fixture
def tmp_workdir(tmp_path):
    """Create a temporary working directory with the example .cid file."""
    src = EXAMPLE_DATA / "MGK-IO.cid"
    dst = tmp_path / "MGK-IO.cid"
    shutil.copy2(src, dst)
    return tmp_path


@pytest.fixture
def mock_fortran(monkeypatch):
    """Patch the Fortran extension so tests run without a compiled build.

    Injects a fake ``cande_wrapper._cande`` module whose ``run_cande``
    returns 0 (success) by default. Tests can override via::

        mock_fortran.run_cande.return_value = 1  # simulate error
    """
    fake_module = MagicMock()
    fake_module.run_cande = MagicMock(return_value=0)
    monkeypatch.setitem(sys.modules, "cande_wrapper._cande", fake_module)
    return fake_module


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: requires the compiled Fortran extension (deselect with '-m \"not integration\"')",
    )
