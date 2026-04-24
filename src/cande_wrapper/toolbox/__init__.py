"""CANDE Tool Box: utilities for manipulating CANDE input/output files.

Provides five main operations corresponding to the original CANDE Tool Box:

1. :func:`half_to_full_mesh` — Convert Level-2 half mesh to Level-3 full mesh
2. :func:`add_pavement` — Add pavement layer and/or elastic wearing course
3. :func:`add_live_loads` — Add live loads on the upper surface
4. :func:`minimize_bandwidth` — Minimize bandwidth by renumbering nodes
5. :func:`compute_rating_factor` — Compute load rating factor RF
"""

from cande_wrapper.toolbox.cid_model import (
    BoundaryCondition,
    CidFile,
    CidProblem,
    Element,
    LoadFactor,
    MasterControl,
    Node,
    PipeGroup,
    SoilLayer,
)
from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.cid_writer import write_cid
from cande_wrapper.toolbox.option1_full_mesh import half_to_full_mesh
from cande_wrapper.toolbox.option2_pavement import (
    PavementConfig,
    WearingCourseConfig,
    add_pavement,
)
from cande_wrapper.toolbox.option3_live_loads import LiveLoadConfig, add_live_loads
from cande_wrapper.toolbox.option4_bandwidth import minimize_bandwidth
from cande_wrapper.toolbox.option5_rating import (
    RatingConfig,
    RatingResult,
    compute_rating_factor,
)
from cande_wrapper.toolbox.out_parser import parse_out

__all__ = [
    # Core model
    "BoundaryCondition",
    "CidFile",
    "CidProblem",
    "Element",
    "LoadFactor",
    "MasterControl",
    "Node",
    "PipeGroup",
    "SoilLayer",
    # Parsers
    "parse_cid",
    "parse_out",
    "write_cid",
    # Option 1
    "half_to_full_mesh",
    # Option 2
    "PavementConfig",
    "WearingCourseConfig",
    "add_pavement",
    # Option 3
    "LiveLoadConfig",
    "add_live_loads",
    # Option 4
    "minimize_bandwidth",
    # Option 5
    "RatingConfig",
    "RatingResult",
    "compute_rating_factor",
]
