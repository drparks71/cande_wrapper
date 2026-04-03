"""Python interface to the CANDE Fortran engine."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


class CandeEngine:
    """Wrapper around the CANDE FEA engine compiled via f2py.

    Usage::

        engine = CandeEngine(work_dir="path/to/working/directory")
        result = engine.run("my_problem")
        # Reads my_problem.cid, writes my_problem.out in work_dir

    Parameters
    ----------
    work_dir : str or Path, optional
        Working directory where .cid input files live and output files
        will be written. Defaults to current directory.
    """

    def __init__(self, work_dir: Optional[str | Path] = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()

    def run(self, prefix: str) -> "CandeResult":
        """Run a CANDE analysis.

        Parameters
        ----------
        prefix : str
            File prefix (without extension). The engine will read
            ``{prefix}.cid`` and produce ``{prefix}.out`` and other
            output files in the working directory.

        Returns
        -------
        CandeResult
            Object with paths to all output files and the return code.

        Raises
        ------
        FileNotFoundError
            If the input .cid file does not exist.
        RuntimeError
            If the Fortran engine returns a nonzero error code.
        """
        cid_file = self.work_dir / f"{prefix}.cid"
        if not cid_file.exists():
            raise FileNotFoundError(f"Input file not found: {cid_file}")

        # Import the f2py-compiled extension
        try:
            from cande_wrapper._cande import run_cande
        except ImportError as e:
            raise ImportError(
                "CANDE Fortran extension not found. "
                "Build it with: pip install -e . "
                "(requires gfortran and numpy)"
            ) from e

        # CANDE reads/writes files relative to CWD, so we chdir
        original_dir = os.getcwd()
        try:
            os.chdir(self.work_dir)
            ierror = run_cande(prefix)
        finally:
            os.chdir(original_dir)

        if ierror != 0:
            raise RuntimeError(
                f"CANDE engine returned error code {ierror}. "
                f"Check {prefix}.out and {prefix}.log for details."
            )

        return CandeResult(self.work_dir, prefix)

    def check_input(self, prefix: str) -> bool:
        """Validate that a .cid input file exists and is readable.

        Parameters
        ----------
        prefix : str
            File prefix (without extension).

        Returns
        -------
        bool
            True if the input file exists.
        """
        return (self.work_dir / f"{prefix}.cid").exists()


class CandeResult:
    """Container for CANDE analysis output file paths.

    Attributes
    ----------
    prefix : str
        The file prefix used for this run.
    output_file : Path
        Path to the main .out output file.
    log_file : Path
        Path to the .log file.
    toc_file : Path
        Path to the .ctc table-of-contents file.
    """

    def __init__(self, work_dir: Path, prefix: str):
        self.prefix = prefix
        self.work_dir = work_dir
        self.output_file = work_dir / f"{prefix}.out"
        self.log_file = work_dir / f"{prefix}.log"
        self.toc_file = work_dir / f"{prefix}.ctc"

    @property
    def output_text(self) -> str:
        """Read and return the full output file contents."""
        return self.output_file.read_text()

    def __repr__(self) -> str:
        return f"CandeResult(prefix={self.prefix!r}, output={self.output_file})"
