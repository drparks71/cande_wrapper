"""Parse CANDE .out output files for mesh data (Option 1) and rating data (Option 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from cande_wrapper.toolbox.cid_model import BoundaryCondition, Element, Node


# ---------------------------------------------------------------------------
# Data structures for parsed output
# ---------------------------------------------------------------------------


@dataclass
class GeneratedMesh:
    """Mesh data extracted from a Level-2 output file (for Option 1)."""

    nodes: list[Node] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    boundaries: list[BoundaryCondition] = field(default_factory=list)
    num_beam_elements: int = 0


@dataclass
class AssessmentEntry:
    """A single design-criterion result from an assessment summary."""

    criterion: str
    node: int
    demand: float
    capacity: float
    ratio: float


@dataclass
class AssessmentSummary:
    """Assessment summary for one pipe group at one load step."""

    pipe_type: str
    group: int
    step: int
    entries: list[AssessmentEntry] = field(default_factory=list)


@dataclass
class StructuralResponse:
    """Structural response data for one node at one load step."""

    node: int
    x: float
    y: float
    moment: float
    thrust: float
    shear: float
    max_stress: float
    hoop_stress: float


@dataclass
class ParsedOutput:
    """Complete parsed data from a CANDE .out file."""

    mesh: GeneratedMesh | None = None
    assessments: list[AssessmentSummary] = field(default_factory=list)
    structural_responses: dict[int, list[StructuralResponse]] = field(
        default_factory=dict
    )  # step -> responses
    num_load_steps: int = 0
    normal_exit: bool = False


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_NODE_COORD_RE = re.compile(
    r"^\s*[I ]?\s*(\d+)\s+\d*\s*([\d.Ee+-]+)\s+([\d.Ee+-]+)\s*$"
)

_ELEM_DATA_RE = re.compile(
    r"^\s*[I ]?\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"
    r"\s+(\d+)\s+(\d+)\s+(\w+)"
)

_BC_LINE_RE = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+([DF])\s*=\s*([\d.Ee+-]+)\s+"
    r"([DF])\s*=\s*([\d.Ee+-]+)"
)

_ASSESSMENT_HEADER_RE = re.compile(
    r"ASSESSMENT SUMMARY\s+(\w+)-GROUP\s+(\d+),\s*LOAD-STEP\s+(\d+)"
)

_CRITERION_RE = re.compile(
    r"^\s+([\w\s&()-]+?)\s{2,}(\d+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s*$"
)

_STRUCTURAL_HEADER_RE = re.compile(
    r"STRUCTURAL RESPONSES OF\s+(\w+)-GROUP\s+(\d+),\s*LOAD STEP\s+(\d+)"
)

_KEY_NUMBERS_STEPS_RE = re.compile(
    r"NUMBER OF LOAD STEPS IS[-\s]+(\d+)"
)

_NORMAL_EXIT_RE = re.compile(r"NORMAL EXIT FROM CANDE")


# ---------------------------------------------------------------------------
# Node coordinate parsing from generated mesh section
# ---------------------------------------------------------------------------

def _parse_node_coordinates(lines: list[str], start: int) -> tuple[list[Node], int]:
    """Parse the 'NODE COORDINATES AS GENERATED' table."""
    nodes = []
    i = start
    # Skip header lines until we see data
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*[I ]?\s*\d+\s+", line):
            break
        i += 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        # Check if we've left the node table
        m = re.match(r"^\s*[I ]?\s*(\d+)\s+\S*\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)", line)
        if m:
            node_id = int(m.group(1))
            x = float(m.group(2))
            y = float(m.group(3))
            nodes.append(Node(id=node_id, x=x, y=y))
            i += 1
        else:
            break
    return nodes, i


def _parse_element_data(lines: list[str], start: int) -> tuple[list[Element], int, int]:
    """Parse the 'ALL ELEMENT DATA' table. Returns (elements, next_line, num_beams)."""
    elements = []
    num_beams = 0
    i = start
    # Skip header
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*[I ]?\s*\d+\s+\d+\s+\d+", line):
            break
        i += 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        m = re.match(
            r"^\s*[I ]?\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"
            r"\s+(\d+)\s+(\d+)\s+(\w+)",
            line,
        )
        if m:
            eid = int(m.group(1))
            n1, n2, n3, n4 = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
            mat = int(m.group(6))
            step = int(m.group(7))
            etype = m.group(8)
            if n3 == 0 and n4 == 0:
                nodes = (n1, n2)
            else:
                nodes = (n1, n2, n3, n4)
            elements.append(Element(id=eid, nodes=nodes, mat=mat, step=step))
            if etype.upper() == "BEAM":
                num_beams += 1
            i += 1
        else:
            break
    return elements, i, num_beams


def _parse_boundary_conditions(
    lines: list[str], start: int
) -> tuple[list[BoundaryCondition], int]:
    """Parse the 'BOUNDARY CONDITIONS AS GENERATED' table."""
    bcs = []
    i = start
    while i < len(lines):
        line = lines[i]
        m = _BC_LINE_RE.search(line)
        if m:
            node = int(m.group(1))
            step = int(m.group(2))
            x_type = m.group(3)  # D or F
            x_val = float(m.group(4))
            y_type = m.group(5)
            y_val = float(m.group(6))
            x_code = 1 if x_type == "D" else 0  # D=displacement(fixed), F=force(free)
            y_code = 1 if y_type == "D" else 0
            bcs.append(BoundaryCondition(
                node=node, x_code=x_code, x_value=x_val,
                y_code=y_code, y_value=y_val, step=step,
            ))
            i += 1
        elif line.strip() and "BOUNDARY" not in line.upper() and "FORCE" not in line.upper() and "NODE" not in line.upper() and "LOAD" not in line.upper():
            # Check if we've passed the table
            if bcs:
                break
            i += 1
        else:
            i += 1
    return bcs, i


def _parse_assessment(lines: list[str], start: int, pipe_type: str,
                      group: int, step: int) -> AssessmentSummary:
    """Parse an assessment summary block."""
    summary = AssessmentSummary(pipe_type=pipe_type, group=group, step=step)
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        # End of assessment block markers
        if "+" * 5 in line or "FINITE ELEMENT OUTPUT" in line:
            break
        if "SERVICE PERFORMANCE" in line:
            # Skip the service performance section
            break
        # Try to match a criterion line
        m = _CRITERION_RE.match(line)
        if m:
            criterion = m.group(1).strip()
            node = int(m.group(2))
            demand = float(m.group(3))
            capacity = float(m.group(4))
            ratio = float(m.group(5))
            summary.entries.append(AssessmentEntry(
                criterion=criterion, node=node,
                demand=demand, capacity=capacity, ratio=ratio,
            ))
        i += 1
    return summary


def _parse_structural_responses(
    lines: list[str], start: int
) -> list[StructuralResponse]:
    """Parse a structural responses block (2 lines per node)."""
    responses = []
    i = start
    # Skip header lines
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*\d+\s+[\d.]+", line):
            break
        i += 1

    while i < len(lines):
        line1 = lines[i].strip()
        if not line1:
            i += 1
            continue
        # Check for end of section
        if "ASSESSMENT" in line1 or "STRAIN" in line1 or "COMBINED" in line1:
            break
        m1 = re.match(
            r"^\s*(\d+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)"
            r"\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)",
            lines[i],
        )
        if not m1:
            i += 1
            continue
        node = int(m1.group(1))
        x = float(m1.group(2))
        moment = float(m1.group(5))
        max_stress = float(m1.group(6))
        shear = float(m1.group(7))

        # Next line has y, thrust, hoop_stress, etc.
        i += 1
        if i < len(lines):
            m2 = re.match(
                r"^\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)"
                r"\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)",
                lines[i],
            )
            if m2:
                y = float(m2.group(1))
                thrust = float(m2.group(4))
                hoop_stress = float(m2.group(5))
            else:
                y = 0.0
                thrust = 0.0
                hoop_stress = 0.0
        else:
            y = 0.0
            thrust = 0.0
            hoop_stress = 0.0

        responses.append(StructuralResponse(
            node=node, x=x, y=y, moment=moment,
            thrust=thrust, shear=shear,
            max_stress=max_stress, hoop_stress=hoop_stress,
        ))
        i += 1

    return responses


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_out(path: str | Path) -> ParsedOutput:
    """Parse a CANDE .out file.

    Extracts:
    - Generated mesh data (node coordinates, elements, boundary conditions)
    - Assessment summaries per load step per pipe group
    - Structural responses per load step
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    result = ParsedOutput()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Number of load steps
        m = _KEY_NUMBERS_STEPS_RE.search(line)
        if m:
            result.num_load_steps = int(m.group(1))

        # Node coordinates table
        if "NODE COORDINATES AS GENERATED" in line:
            nodes, i = _parse_node_coordinates(lines, i + 1)
            if result.mesh is None:
                result.mesh = GeneratedMesh()
            result.mesh.nodes = nodes
            continue

        # Element data table
        if "ALL ELEMENT DATA" in line:
            elements, i, num_beams = _parse_element_data(lines, i + 1)
            if result.mesh is None:
                result.mesh = GeneratedMesh()
            result.mesh.elements = elements
            result.mesh.num_beam_elements = num_beams
            continue

        # Boundary conditions
        if "BOUNDARY CONDITIONS AS GENERATED" in line:
            bcs, i = _parse_boundary_conditions(lines, i + 1)
            if result.mesh is None:
                result.mesh = GeneratedMesh()
            result.mesh.boundaries = bcs
            continue

        # Assessment summary
        m = _ASSESSMENT_HEADER_RE.search(line)
        if m:
            pipe_type = m.group(1)
            group = int(m.group(2))
            step = int(m.group(3))
            summary = _parse_assessment(lines, i + 1, pipe_type, group, step)
            result.assessments.append(summary)
            i += 1
            continue

        # Structural responses
        m = _STRUCTURAL_HEADER_RE.search(line)
        if m:
            step = int(m.group(3))
            responses = _parse_structural_responses(lines, i + 1)
            result.structural_responses[step] = responses
            i += 1
            continue

        # Normal exit
        if _NORMAL_EXIT_RE.search(line):
            result.normal_exit = True

        i += 1

    return result
