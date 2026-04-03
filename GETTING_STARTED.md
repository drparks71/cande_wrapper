# Getting Started with cande-wrapper

A Python wrapper for the CANDE (Culvert ANalysis and DEsign) finite element engine.

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | >= 3.10 | Runtime |
| gfortran | any recent | Compiles the CANDE Fortran engine |
| NumPy | >= 1.26 | f2py extension building and runtime |
| Meson | >= 1.1 | Build system |
| Ninja | any recent | Build backend for Meson |

### Installing gfortran on Windows

The easiest way is via MSYS2:

```bash
# In MSYS2 terminal
pacman -S mingw-w64-x86_64-gcc-fortran

# Add to PATH (PowerShell)
$env:PATH += ";C:\msys64\mingw64\bin"
```

Or install via conda:

```bash
conda install -c conda-forge gfortran
```

### Installing build tools

```bash
pip install meson-python meson ninja numpy
```

## Installation

From the project root:

```bash
pip install -e ".[dev]"
```

This compiles the Fortran engine via f2py and installs the Python package in editable mode. The `[dev]` extra includes pytest and jupyter for testing and notebooks.

If the build fails, see [Troubleshooting](#troubleshooting) below.

## Quick Start

```python
from cande_wrapper import CandeEngine

engine = CandeEngine(work_dir="path/to/my/models")
result = engine.run("EX1")  # reads EX1.cid, writes EX1.out
print(result.output_text)
```

## Understanding CANDE Input Files

CANDE reads `.cid` input files (CANDE Input Data). These are fixed-format text files with sections:

- **A-1**: Master control line (analysis/design mode, solution level, title)
- **A-2**: Pipe type and element counts
- **B-\***: Pipe material properties
- **C-\***: Mesh, node, and element definitions
- **D-\***: Soil properties and load steps
- **STOP**: End-of-problem marker

Multiple problems can be run back-to-back in a single `.cid` file, each terminated by `STOP`.

An example input file is included at `tests/example_data/MGK-IO.cid`.

## Understanding Output

After running `engine.run("prefix")`, these files are created in the working directory:

| File | Description |
|---|---|
| `prefix.out` | Main analysis output report |
| `prefix.log` | Engine log messages |
| `prefix.ctc` | Table of contents for the output |
| `prefix_MeshGeom.xml` | Mesh geometry (for visualization) |
| `prefix_MeshResults.xml` | Mesh results (for visualization) |
| `prefix_BeamResults.xml` | Beam element results |
| `prefix_PLOT1.dat` | Plot data file 1 |
| `prefix_PLOT2.dat` | Plot data file 2 |

The `CandeResult` object returned by `engine.run()` gives convenient access to the main output files:

```python
result = engine.run("EX1")
print(result.output_file)   # Path to EX1.out
print(result.log_file)      # Path to EX1.log
print(result.output_text)   # Full contents of EX1.out
```

## Running Tests

Unit tests (no Fortran build required):

```bash
pytest -v
```

Integration tests (requires successful build):

```bash
pytest -m integration -v
```

All tests:

```bash
pytest -m "" -v
```

## Troubleshooting

### `gfortran: command not found`

gfortran is not on your PATH. Verify with `gfortran --version`. On Windows, ensure the MSYS2/MinGW or conda bin directory is in your PATH.

### Linker errors about missing symbols

The `meson.build` file lists Engine source files explicitly. If you see unresolved symbols like `plasti_` or `prhero_`, the corresponding `.f` file needs to be added to the `engine_sources` list in `meson.build`.

### `ImportError: CANDE Fortran extension not found`

The package was imported but the compiled extension (`_cande.pyd` / `_cande.so`) was not found. Rebuild with:

```bash
pip install -e . --no-build-isolation
```

### Large memory usage

The CANDE engine statically allocates ~320 MB for the stiffness matrix (`REAL*8 A(20000,2000)` in `system.fi`). This is normal for FEA solvers and is mapped as virtual memory.
