"""cande-wrapper: Python wrapper for the CANDE FEA culvert analysis engine."""

from cande_wrapper.engine import CandeEngine, CandeResult
from cande_wrapper.pipes import (
    CorrugatedAluminum,
    CorrugatedHDPE,
    CorrugatedPVC,
    CorrugatedSteel,
    DuctileIron,
    PrecastConcrete,
    SmoothHDPE,
    SmoothSteelCasing,
)
from cande_wrapper.vehicle import Axle, Vehicle, WheelFootprint

__all__ = [
    "Axle",
    "CandeEngine",
    "CandeResult",
    "CorrugatedAluminum",
    "CorrugatedHDPE",
    "CorrugatedPVC",
    "CorrugatedSteel",
    "DuctileIron",
    "PrecastConcrete",
    "SmoothHDPE",
    "SmoothSteelCasing",
    "Vehicle",
    "WheelFootprint",
]


def __getattr__(name):
    """Lazy-load visualization functions and toolbox subpackage."""
    _viz_names = {
        "parse_beam_results",
        "parse_mesh_geom",
        "parse_mesh_results",
        "plot_beam_forces",
        "plot_beam_results",
        "plot_deformed_mesh",
        "plot_displacement",
        "plot_load_history",
        "plot_mesh",
        "plot_soil_stress",
    }
    if name in _viz_names:
        from cande_wrapper import visualization
        return getattr(visualization, name)
    if name == "toolbox":
        from cande_wrapper import toolbox as _toolbox
        return _toolbox
    raise AttributeError(f"module 'cande_wrapper' has no attribute {name!r}")
