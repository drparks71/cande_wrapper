"""Parse CANDE .cid input files into CidFile/CidProblem data structures."""

from __future__ import annotations

import re
from pathlib import Path

from cande_wrapper.toolbox.cid_model import (
    BoundaryCondition,
    CidFile,
    CidProblem,
    Element,
    LoadFactor,
    MasterControl,
    Node,
    PipeGroup,
    ScalingLine,
    SoilLayer,
)

# Regex to detect a line-tag: optional whitespace, tag text, then `!!`
_TAG_RE = re.compile(r"^(\s*\S+!!)(.*)$")


def _split_tag(line: str) -> tuple[str, bool, str]:
    """Split a tagged line into (tag_id, is_last, data).

    Returns ('', False, line) for untagged lines.
    """
    m = _TAG_RE.match(line)
    if not m:
        return "", False, line
    tag_part = m.group(1).strip()  # e.g. "C-3.L3!!"
    rest = m.group(2)
    is_last = rest.startswith("L")
    if is_last:
        rest = rest[1:]
    return tag_part, is_last, rest


def _tag_section(tag: str) -> str:
    """Extract the section letter from a tag like 'C-3.L3!!' -> 'C-3'."""
    # Remove trailing '!!'
    t = tag.rstrip("!")
    # Return the part before any dot-level qualifier, but keep sub-number
    return t


def _parse_ints(text: str, count: int | None = None) -> list[int]:
    """Parse whitespace-separated integers from text."""
    parts = text.split()
    if count is not None:
        parts = parts[:count]
    return [int(p) for p in parts]


def _parse_floats(text: str, count: int | None = None) -> list[float]:
    """Parse whitespace-separated floats from text."""
    parts = text.split()
    if count is not None:
        parts = parts[:count]
    return [float(p) for p in parts]


def _parse_a1(data: str) -> MasterControl:
    """Parse the A-1 line data portion.

    Level 3 format: MODE LEVEL LRFD NPGRPS HED(15A4) ITMAX
    Level 1/2 format: MODE LEVEL LRFD NUM_STEPS HED(15A4) ITMAX

    The 4th field is NPGRPS for Level 3, or NUM_STEPS for Level 1/2.
    Both can appear as int or float (e.g. '160.').
    """
    parts = data.split()
    mode = parts[0] if parts else "ANALYS"
    level = int(parts[1]) if len(parts) > 1 else 3
    method = int(parts[2]) if len(parts) > 2 else 0
    # 4th field: NPGRPS (Level 3) or NUM_STEPS (Level 1/2)
    field4 = int(float(parts[3])) if len(parts) > 3 else 1
    # Remaining parts form the heading; ITMAX may be the last integer
    rest = parts[4:] if len(parts) > 4 else []
    itmax = 0
    heading = ""
    if rest:
        try:
            itmax = int(rest[-1])
            heading = " ".join(rest[:-1])
        except ValueError:
            heading = " ".join(rest)

    npgrps = field4 if level == 3 else 1
    num_steps = field4
    return MasterControl(
        mode=mode, level=level, method=method,
        num_steps=num_steps, npgrps=npgrps, itmax=itmax, heading=heading,
    )


def _parse_node_line(data: str) -> Node:
    """Parse a C-3.L3 node line: node_id constraint x y."""
    parts = data.split()
    node_id = int(parts[0])
    # parts[1] is the constraint code (not stored on Node, used in BCs)
    x = float(parts[2])
    y = float(parts[3])
    return Node(id=node_id, x=x, y=y)


def _parse_element_line(data: str) -> Element:
    """Parse a C-4.L3 element line.

    Fortran format: I4,7I5 → elem_id n1 n2 n3 n4 mat step type_code
    """
    parts = data.split()
    elem_id = int(parts[0])
    n1 = int(parts[1])
    n2 = int(parts[2])
    n3 = int(parts[3]) if len(parts) > 3 else 0
    n4 = int(parts[4]) if len(parts) > 4 else 0
    mat = int(parts[5]) if len(parts) > 5 else 1
    step = int(parts[6]) if len(parts) > 6 else 1
    type_code = int(parts[7]) if len(parts) > 7 else 0
    nodes = (n1, n2) if n3 == 0 and n4 == 0 else (n1, n2, n3, n4)
    return Element(id=elem_id, nodes=nodes, mat=mat, step=step, type_code=type_code)


def _parse_bc_line(data: str) -> BoundaryCondition:
    """Parse a C-5.L3 boundary condition line.

    Format: node x_code x_value y_code y_value [angle] [step_info...]
    """
    parts = data.split()
    node = int(parts[0])
    x_code = int(parts[1])
    x_value = float(parts[2])
    y_code = int(parts[3])
    y_value = float(parts[4])
    angle = float(parts[5]) if len(parts) > 5 else 0.0
    step = int(parts[6]) if len(parts) > 6 else 1
    return BoundaryCondition(
        node=node, x_code=x_code, x_value=x_value,
        y_code=y_code, y_value=y_value, step=step, angle=angle,
    )


def _parse_problem(lines: list[str]) -> CidProblem:
    """Parse a single CANDE problem from its lines (excluding STOP)."""
    problem = CidProblem(
        master=MasterControl(mode="ANALYS", level=3, method=0, num_steps=1),
    )

    has_tags = any("!!" in ln for ln in lines)
    problem.has_line_tags = has_tags

    i = 0
    pipe_group_count = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        tag, is_last, data = _split_tag(line)
        section = _tag_section(tag).upper() if tag else ""

        # ---- A-1: Master control ----
        if section == "A-1":
            problem.master = _parse_a1(data)
            problem.master.raw_line = line
            i += 1
            continue

        # ---- A-2: Pipe group header ----
        if section.startswith("A-2"):
            pipe_group_count += 1
            parts = data.split()
            pipe_type = parts[0] if parts else "BASIC"
            num_b_lines = int(parts[1]) if len(parts) > 1 else 1
            pg = PipeGroup(
                pipe_type=pipe_type.upper(),
                group_num=pipe_group_count,
                raw_lines=[line],
            )
            i += 1
            # Consume B-lines for this pipe group
            while i < len(lines):
                btag, bis_last, bdata = _split_tag(lines[i])
                bsection = _tag_section(btag).upper() if btag else ""
                if bsection.startswith("B-"):
                    pg.raw_lines.append(lines[i])
                    i += 1
                    if bis_last:
                        break
                else:
                    break
            problem.pipe_groups.append(pg)
            continue

        # ---- C-1 / C-2: Prep lines ----
        if section.startswith("C-1") or section.startswith("C-2"):
            # Check if this is a C-2b or C-2c scaling line
            if "C-2B" in section or "C-2C" in section:
                problem.scaling_lines.append(ScalingLine(raw_line=line))
                i += 1
                continue
            problem.prep_lines.append(line)
            i += 1
            continue

        # ---- C-3: Node coordinates (Level 3) ----
        if section.startswith("C-3") and problem.master.level == 3:
            problem.nodes.append(_parse_node_line(data))
            i += 1
            continue

        # ---- C-4: Element connectivity (Level 3) ----
        if section.startswith("C-4") and problem.master.level == 3:
            problem.elements.append(_parse_element_line(data))
            i += 1
            continue

        # ---- C-5: Boundary conditions (Level 3) ----
        if section.startswith("C-5") and problem.master.level == 3:
            problem.boundaries.append(_parse_bc_line(data))
            i += 1
            continue

        # ---- Level 1/2 C-lines: preserve as prep ----
        if section.startswith("C-") and problem.master.level != 3:
            problem.prep_lines.append(line)
            i += 1
            continue

        # ---- D-1: Soil group header ----
        if section.startswith("D-1"):
            parts = data.split()
            mat_num = int(parts[0]) if parts else 1
            num_layers = int(parts[1]) if len(parts) > 1 else 1
            soil = SoilLayer(
                material_num=mat_num,
                num_layers=num_layers,
                raw_lines=[line],
            )
            is_last_d1 = is_last
            i += 1
            # Consume D-2+ lines for this soil group
            while i < len(lines) and not is_last_d1:
                dtag, dis_last, ddata = _split_tag(lines[i])
                dsection = _tag_section(dtag).upper() if dtag else ""
                if dsection.startswith("D-"):
                    soil.raw_lines.append(lines[i])
                    i += 1
                    if dis_last:
                        break
                else:
                    break
            problem.soils.append(soil)
            continue

        # ---- D-2+: Additional soil lines (may appear without D-1 context) ----
        if section.startswith("D-"):
            if problem.soils:
                problem.soils[-1].raw_lines.append(line)
            i += 1
            continue

        # ---- E-lines: Load factors ----
        if section.startswith("E-") or (stripped and stripped[0].upper() == "E"):
            parts = data.split()
            if len(parts) >= 2:
                problem.load_factors.append(
                    LoadFactor(step=int(parts[0]), factor=float(parts[1]))
                )
            i += 1
            continue

        # ---- Unrecognized: treat as trailing comment ----
        problem.trailing_comments.append(line)
        i += 1

    return problem


def parse_cid(path: str | Path) -> CidFile:
    """Parse a .cid file into a CidFile containing one or more problems."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    cid = CidFile()
    problem_lines: list[str] = []

    for line in lines:
        if line.strip().upper() == "STOP":
            if problem_lines:
                cid.problems.append(_parse_problem(problem_lines))
                problem_lines = []
        else:
            problem_lines.append(line)

    # Handle file without trailing STOP
    if problem_lines:
        cid.problems.append(_parse_problem(problem_lines))

    return cid
