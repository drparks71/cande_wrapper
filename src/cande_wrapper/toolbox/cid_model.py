"""Data classes representing the structure of a CANDE .cid input file."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """A finite-element node with 2-D coordinates."""

    id: int
    x: float
    y: float


@dataclass
class Element:
    """A finite element with connectivity, material group, and construction step.

    type_code values (from Fortran IX column 7):
        0 = normal continuum element
        1 = interface element (FACE / XFACE)
        8 = LINK-8 element
        9 = LINK-9 element
    """

    id: int
    nodes: tuple[int, ...]
    mat: int
    step: int
    type_code: int = 0


@dataclass
class BoundaryCondition:
    """Nodal boundary condition: constraint codes + force/displacement values."""

    node: int
    x_code: int
    x_value: float
    y_code: int
    y_value: float
    step: int = 1
    angle: float = 0.0


@dataclass
class MasterControl:
    """A-1 line data: execution mode, solution level, and problem heading."""

    mode: str  # "ANALYS" or "DESIGN"
    level: int  # 1, 2, or 3
    method: int  # 0 or 1 (LRFD flag)
    num_steps: int
    npgrps: int = 1  # number of pipe groups
    itmax: int = 0  # max iterations
    heading: str = ""
    raw_line: str = ""


@dataclass
class PipeGroup:
    """Pipe-type definition (A-2 + B-section lines), preserved as raw text."""

    pipe_type: str  # "STEEL", "ALUMINUM", "CONCRETE", "PLASTIC", "BASIC"
    group_num: int
    raw_lines: list[str] = field(default_factory=list)


@dataclass
class SoilLayer:
    """Soil material definition (D-section lines), preserved as raw text."""

    material_num: int
    num_layers: int
    raw_lines: list[str] = field(default_factory=list)


@dataclass
class PrepLine:
    """C-1.L3 / C-2.L3 mesh-prep header lines."""

    raw_lines: list[str] = field(default_factory=list)


@dataclass
class LoadFactor:
    """E-line: LRFD load factor for a given load step."""

    step: int
    factor: float


@dataclass
class ScalingLine:
    """C-2b.L3 / C-2c.L3 element thickness scaling lines for CLS."""

    raw_line: str


@dataclass
class CidProblem:
    """A single CANDE problem (terminated by STOP)."""

    master: MasterControl
    pipe_groups: list[PipeGroup] = field(default_factory=list)
    prep_lines: list[str] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    boundaries: list[BoundaryCondition] = field(default_factory=list)
    soils: list[SoilLayer] = field(default_factory=list)
    load_factors: list[LoadFactor] = field(default_factory=list)
    scaling_lines: list[ScalingLine] = field(default_factory=list)
    has_line_tags: bool = True
    trailing_comments: list[str] = field(default_factory=list)


@dataclass
class CidFile:
    """A complete .cid file, potentially containing multiple problems."""

    problems: list[CidProblem] = field(default_factory=list)
