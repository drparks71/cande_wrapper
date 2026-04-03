# cande-wrapper

Python wrapper for the [CANDE](https://www.fhwa.dot.gov/engineering/hydraulics/software/culvertanalysis.cfm) (Culvert ANalysis and DEsign) finite element engine.

The CANDE-2025 Fortran source is compiled via [f2py](https://numpy.org/doc/stable/f2py/) into a native Python extension module, allowing direct calls from Python without subprocess overhead or DLL wrappers.

## Quick Start

```python
from cande_wrapper import CandeEngine

engine = CandeEngine(work_dir="path/to/my/models")
result = engine.run("EX1")  # reads EX1.cid, writes EX1.out
print(result.output_text)
```

## Installation

Requires gfortran, Meson, Ninja, and NumPy. See [GETTING_STARTED.md](GETTING_STARTED.md) for full prerequisites and troubleshooting.

```bash
pip install -e ".[dev]"
```

## Testing

```bash
pytest -v                    # unit tests (no build required)
pytest -m integration -v     # integration tests (requires build)
```

## Documentation

See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed setup, input file format, output descriptions, and troubleshooting.
