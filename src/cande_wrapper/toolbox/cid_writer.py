"""Write CidProblem/CidFile data structures back to CANDE .cid format."""

from __future__ import annotations

from pathlib import Path

from cande_wrapper.toolbox.cid_model import (
    BoundaryCondition,
    CidFile,
    CidProblem,
    Element,
    LoadFactor,
    Node,
)

_TAG_WIDTH = 24  # Right-justified tag field width


def _fmt_tag(tag: str, is_last: bool = False) -> str:
    """Format a line tag right-justified in the tag field."""
    suffix = "L" if is_last else ""
    return tag.rjust(_TAG_WIDTH) + suffix


def _fmt_int(val: int, width: int = 5) -> str:
    return f"{val:>{width}d}"


def _fmt_float(val: float, width: int = 10) -> str:
    # Use integer-like formatting if value is a whole number
    if val == int(val) and abs(val) < 1e8:
        return f"{int(val):>{width}d}"
    return f"{val:>{width}g}"


def _write_a1(master, has_tags: bool) -> str:
    """Write the A-1 master control line."""
    if master.raw_line:
        return master.raw_line
    tag = _fmt_tag("A-1!!") if has_tags else ""
    data = f"{master.mode:6s} {master.level:3d} {master.method}{master.num_steps:3d}"
    if master.heading:
        data += f" {master.heading}"
    return tag + data


def _write_node(node: Node, has_tags: bool, is_last: bool = False) -> str:
    """Write a C-3.L3 node line."""
    tag = _fmt_tag("C-3.L3!!", is_last) if has_tags else ""
    return (
        f"{tag}{_fmt_int(node.id)}{_fmt_int(0)}"
        f"{_fmt_float(node.x)}{_fmt_float(node.y)}"
    )


def _write_element(elem: Element, has_tags: bool, is_last: bool = False) -> str:
    """Write a C-4.L3 element line."""
    tag = _fmt_tag("C-4.L3!!", is_last) if has_tags else ""
    n = elem.nodes
    if len(n) == 2:
        nodes_str = f"{_fmt_int(n[0])}{_fmt_int(n[1])}{_fmt_int(0)}{_fmt_int(0)}"
    else:
        nodes_str = "".join(_fmt_int(ni) for ni in n[:4])
    return f"{tag}{_fmt_int(elem.id)}{nodes_str}{_fmt_int(elem.mat)}"


def _write_bc(bc: BoundaryCondition, has_tags: bool, is_last: bool = False) -> str:
    """Write a C-5.L3 boundary condition line."""
    tag = _fmt_tag("C-5.L3!!", is_last) if has_tags else ""
    return (
        f"{tag}{_fmt_int(bc.node)}{_fmt_int(bc.x_code)}"
        f"{_fmt_float(bc.x_value)}{_fmt_int(bc.y_code)}"
        f"{_fmt_float(bc.y_value)}"
    )


def _write_load_factor(lf: LoadFactor, has_tags: bool, is_last: bool = False) -> str:
    tag = _fmt_tag("E-1!!", is_last) if has_tags else ""
    return f"{tag}{_fmt_int(lf.step)}{_fmt_float(lf.factor)}"


def write_problem(problem: CidProblem) -> list[str]:
    """Convert a CidProblem to a list of output lines."""
    lines: list[str] = []
    ht = problem.has_line_tags

    # A-1 line
    lines.append(_write_a1(problem.master, ht))

    # Pipe groups (A-2 + B lines, preserved raw)
    for pg in problem.pipe_groups:
        lines.extend(pg.raw_lines)

    # Prep lines (C-1, C-2 — preserved raw)
    lines.extend(problem.prep_lines)

    # Scaling lines (C-2b, C-2c)
    for sl in problem.scaling_lines:
        lines.append(sl.raw_line)

    # Nodes (C-3.L3)
    if problem.master.level == 3:
        for idx, node in enumerate(problem.nodes):
            is_last = idx == len(problem.nodes) - 1
            lines.append(_write_node(node, ht, is_last))

        # Elements (C-4.L3)
        for idx, elem in enumerate(problem.elements):
            is_last = idx == len(problem.elements) - 1
            lines.append(_write_element(elem, ht, is_last))

        # Boundary conditions (C-5.L3)
        for idx, bc in enumerate(problem.boundaries):
            is_last = idx == len(problem.boundaries) - 1
            lines.append(_write_bc(bc, ht, is_last))

    # Soil layers (D lines, preserved raw)
    for soil in problem.soils:
        lines.extend(soil.raw_lines)

    # Load factors (E lines)
    for idx, lf in enumerate(problem.load_factors):
        is_last = idx == len(problem.load_factors) - 1
        lines.append(_write_load_factor(lf, ht, is_last))

    # Trailing comments
    lines.extend(problem.trailing_comments)

    return lines


def write_cid(cid: CidFile, path: str | Path) -> Path:
    """Write a CidFile to disk."""
    path = Path(path)
    all_lines: list[str] = []
    for problem in cid.problems:
        all_lines.extend(write_problem(problem))
        all_lines.append("STOP")

    path.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    return path
