"""Option 2: Add pavement layer and/or elastic wearing course.

Modifies a Level-3 .cid file to include:
  - A pavement layer (BASIC beam elements) over the soil surface
  - An elastic wearing course replacing the top soil layer
  - Or both
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cande_wrapper.toolbox.cid_model import (
    CidProblem,
    Element,
    PipeGroup,
    SoilLayer,
)
from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.cid_writer import write_cid


@dataclass
class PavementConfig:
    """Material properties for a pavement overlay."""

    thickness: float = 8.0  # inches
    youngs_modulus: float = 200_000.0  # psi
    poisson_ratio: float = 0.2
    density: float = 140.0  # lb/ft^3


@dataclass
class WearingCourseConfig:
    """Material properties for an elastic wearing course."""

    youngs_modulus: float = 1_800.0  # psi
    poisson_ratio: float = 0.33


def _find_surface_elements(problem: CidProblem) -> list[Element]:
    """Find elements whose top face lies on the soil surface.

    Surface elements are those with at least one edge at the maximum
    y-coordinate in the mesh.
    """
    if not problem.nodes:
        return []

    node_map = {n.id: n for n in problem.nodes}
    max_y = max(n.y for n in problem.nodes)
    tol = 1e-6

    surface_elems = []
    for elem in problem.elements:
        # Only consider soil (quad) elements, not beams
        if len(elem.nodes) < 4:
            continue
        live_nodes = [n for n in elem.nodes if n != 0]
        y_vals = [node_map[nid].y for nid in live_nodes if nid in node_map]
        if any(abs(y - max_y) < tol for y in y_vals):
            surface_elems.append(elem)

    return surface_elems


def _get_top_edge_nodes(elem: Element, node_map: dict) -> tuple[int, int] | None:
    """Return the two node IDs forming the top (highest y) edge of an element."""
    live = [n for n in elem.nodes if n != 0]
    if len(live) < 2:
        return None

    # Sort nodes by y descending, take top 2
    sorted_by_y = sorted(live, key=lambda nid: node_map[nid].y, reverse=True)
    top_two = sorted_by_y[:2]
    # Sort by x so the beam goes left to right
    top_two.sort(key=lambda nid: node_map[nid].x)
    return (top_two[0], top_two[1])


def _surface_elements_sorted(problem: CidProblem) -> list[Element]:
    """Surface elements sorted left to right by their leftmost top-edge node."""
    node_map = {n.id: n for n in problem.nodes}
    surface = _find_surface_elements(problem)

    def sort_key(e):
        edge = _get_top_edge_nodes(e, node_map)
        if edge:
            return node_map[edge[0]].x
        return 0.0

    return sorted(surface, key=sort_key)


def _add_pavement_elements(
    problem: CidProblem, config: PavementConfig
) -> None:
    """Add BASIC beam elements over the soil surface."""
    node_map = {n.id: n for n in problem.nodes}
    surface_sorted = _surface_elements_sorted(problem)

    if len(surface_sorted) < 1:
        raise ValueError("No surface elements found for pavement placement")

    # Skip extreme left and right elements when there are enough
    if len(surface_sorted) > 2:
        interior = surface_sorted[1:-1]
    else:
        interior = surface_sorted

    # New pipe group number
    max_group = max(
        (pg.group_num for pg in problem.pipe_groups), default=0
    )
    new_group = max_group + 1

    # Compute section properties
    area = config.thickness  # in^2/in (area per unit length)
    inertia = config.thickness**3 / 12.0  # in^4/in

    # Create the pipe group with BASIC beam properties
    # Format raw lines for A-2 and B-1.Basic
    tag_a2 = "A-2.L3!!".rjust(24)
    tag_b1 = "B-1.Basic!!".rjust(24)
    tag_b2 = "B-2.Basic!!".rjust(24)
    a2_line = f"{tag_a2}BASIC         {len(interior)}"
    b1_line = (
        f"{tag_b1}{new_group:5d}    2"
        f"{config.youngs_modulus:10g}"
        f"{config.poisson_ratio:10g}"
        f"{area:10g}"
        f"{inertia:10g}"
        f"         0"
    )
    b2_line = f"{tag_b2}    0"

    pg = PipeGroup(
        pipe_type="BASIC",
        group_num=new_group,
        raw_lines=[a2_line, b1_line, b2_line],
    )
    problem.pipe_groups.append(pg)

    # Add beam elements
    max_elem = max((e.id for e in problem.elements), default=0)
    for i, surf_elem in enumerate(interior):
        edge = _get_top_edge_nodes(surf_elem, node_map)
        if edge is None:
            continue
        max_elem += 1
        beam = Element(
            id=max_elem,
            nodes=(edge[0], edge[1]),
            mat=new_group,
            step=1,
        )
        problem.elements.append(beam)


def _add_wearing_course(
    problem: CidProblem, config: WearingCourseConfig
) -> None:
    """Change the top soil layer material to isotropic elastic."""
    surface = _find_surface_elements(problem)
    if not surface:
        raise ValueError("No surface elements found")

    # Find the material numbers used by surface elements
    surface_mats = set(e.mat for e in surface)

    # For each surface material, add/replace with isotropic elastic
    new_mat_num = max((s.material_num for s in problem.soils), default=0) + 1

    tag_d1 = "D-1!!".rjust(24)
    tag_d2 = "D-2.Isotropic!!".rjust(24)
    soil = SoilLayer(
        material_num=new_mat_num,
        num_layers=1,
        raw_lines=[
            f"{tag_d1}L{new_mat_num:4d}    1          elastic wearing course",
            f"{tag_d2}{config.youngs_modulus:10g}",
        ],
    )
    problem.soils.append(soil)

    # Update surface elements to use the new material
    for elem in surface:
        if elem.mat in surface_mats and len(elem.nodes) >= 4:
            elem.mat = new_mat_num


def add_pavement(
    cid_path: str | Path,
    pavement: PavementConfig | None = None,
    wearing_course: WearingCourseConfig | None = None,
    output_dir: str | Path | None = None,
    problem_index: int = 0,
) -> Path:
    """Add pavement and/or elastic wearing course to a Level-3 mesh.

    Parameters
    ----------
    cid_path
        Path to the originating Level-3 .cid file.
    pavement
        Pavement configuration. Pass ``PavementConfig()`` for defaults.
        ``None`` to skip.
    wearing_course
        Wearing course configuration. Pass ``WearingCourseConfig()``
        for defaults. ``None`` to skip.
    output_dir
        Directory for output file. Defaults to same directory as input.
    problem_index
        Which problem in the file to process (0-based).

    Returns
    -------
    Path to the new ``Pave-{name}.cid`` file.
    """
    if pavement is None and wearing_course is None:
        raise ValueError("Must specify pavement, wearing_course, or both")

    cid_path = Path(cid_path)
    cid = parse_cid(cid_path)

    if problem_index >= len(cid.problems):
        raise ValueError(
            f"Problem index {problem_index} out of range "
            f"(file has {len(cid.problems)} problems)"
        )

    problem = cid.problems[problem_index]
    if problem.master.level != 3:
        raise ValueError(
            f"Option 2 requires a Level-3 input file, "
            f"got Level-{problem.master.level}"
        )

    if pavement is not None:
        _add_pavement_elements(problem, pavement)

    if wearing_course is not None:
        _add_wearing_course(problem, wearing_course)

    # Document changes
    parts = []
    if pavement:
        parts.append(
            f"Pavement: t={pavement.thickness}\", "
            f"E={pavement.youngs_modulus} psi, "
            f"nu={pavement.poisson_ratio}"
        )
    if wearing_course:
        parts.append(
            f"Wearing course: E={wearing_course.youngs_modulus} psi, "
            f"nu={wearing_course.poisson_ratio}"
        )
    problem.trailing_comments.append(
        f"* CANDE Tool Box Option 2: {'; '.join(parts)}"
    )

    out_dir = Path(output_dir) if output_dir else cid_path.parent
    out_name = f"Pave-{cid_path.stem}.cid"
    out_path = out_dir / out_name

    write_cid(cid, out_path)
    return out_path
