# cande-wrapper

<img alt="Pipeline" src="https://daneparks.com/Dane/cande-wrapper/badges/main/pipeline.svg">
<img alt="Coverage" src="https://daneparks.com/Dane/cande-wrapper/badges/main/coverage.svg">
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/cande-wrapper">
![PyPI - License](https://img.shields.io/pypi/l/cande-wrapper)
[![PyPI Downloads](https://static.pepy.tech/badge/cande-wrapper/month)](https://pepy.tech/projects/cande-wrapper)

Python wrapper for the [CANDE](https://www.fhwa.dot.gov/engineering/hydraulics/software/culvertanalysis.cfm) (Culvert ANalysis and DEsign) finite element engine.

The CANDE-2025 Fortran source is compiled via [f2py](https://numpy.org/doc/stable/f2py/) into a native Python extension module, allowing direct calls from Python without subprocess overhead or DLL wrappers.

**[Source](https://daneparks.com/Dane/cande-wrapper) · [PyPI](https://pypi.org/project/cande-wrapper/)**

---

## Installation

Install from PyPI (includes pre-built wheels for Windows and Linux):

```bash
pip install cande-wrapper
```

For development (requires gfortran):

```bash
pip install -e ".[dev]"
```

### Build prerequisites (development only)

| Dependency | Version | Purpose |
|---|---|---|
| Python | >= 3.10 | Runtime |
| gfortran | any recent | Compiles the CANDE Fortran engine |
| NumPy | >= 1.26 | f2py extension building and runtime |
| Meson | >= 1.1 | Build system |
| Ninja | any recent | Build backend for Meson |

<details>
<summary>Installing gfortran on Windows</summary>

Via MSYS2:

```bash
# In MSYS2 terminal
pacman -S mingw-w64-x86_64-gcc-fortran

# Add to PATH (PowerShell)
$env:PATH += ";C:\msys64\mingw64\bin"
```

Or via conda:

```bash
conda install -c conda-forge gfortran
```

</details>

## Quick Start

```python
from cande_wrapper import CandeEngine

engine = CandeEngine(work_dir="path/to/my/models")
result = engine.run("EX1")  # reads EX1.cid, writes EX1.out
print(result.output_text)
```

### Vehicle definitions

Standard AASHTO design vehicles are available for live-load analysis:

```python
from cande_wrapper import Vehicle

hs20 = Vehicle.hs20()       # AASHTO HS-20 (72 kip)
hs25 = Vehicle.hs25()       # AASHTO HS-25 (90 kip)
tandem = Vehicle.tandem()   # AASHTO design tandem (50 kip)
cooper = Vehicle.cooper_e80()  # Cooper E-80 railroad (160 kip)
```

Custom vehicles can be defined with arbitrary axle configurations:

```python
from cande_wrapper import Vehicle, WheelFootprint, Axle

truck = Vehicle(
    name="Custom Truck",
    footprint=WheelFootprint(length=12.0, width=24.0, spacing=84.0),
    axles=[
        Axle(weight=12000, spacing=0),
        Axle(weight=40000, spacing=180),
        Axle(weight=40000, spacing=54),
    ],
)
print(f"{truck.name}: {truck.total_weight/1000:.0f} kip")
```

## CANDE Input Files

CANDE reads `.cid` input files (CANDE Input Data). These are fixed-format text files with sections:

- **A-1**: Master control line (analysis/design mode, solution level, title)
- **A-2**: Pipe type and element counts
- **B-\***: Pipe material properties
- **C-\***: Mesh, node, and element definitions
- **D-\***: Soil properties and load steps
- **STOP**: End-of-problem marker

Multiple problems can be run back-to-back in a single `.cid` file, each terminated by `STOP`.

An example input file is included at `tests/example_data/MGK-IO.cid`.

## Output Files

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

## Testing

```bash
pytest -v                    # unit tests (no build required)
pytest -m integration -v     # integration tests (requires build)
pytest -m "" -v              # all tests
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
