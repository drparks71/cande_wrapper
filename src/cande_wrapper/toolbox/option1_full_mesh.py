"""Option 1: Convert Level-2 half mesh to Level-3 full mesh.

Takes a Level-2 .cid file (symmetric half mesh) and its .out file
(which contains the generated mesh data) and produces a Level-3 .cid
file with the full mesh by mirroring the right half to the left.
"""

from __future__ import annotations

from pathlib import Path

from cande_wrapper.toolbox.cid_model import (
    BoundaryCondition,
    CidFile,
    CidProblem,
    Element,
    MasterControl,
    Node,
)
from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.cid_writer import write_cid
from cande_wrapper.toolbox.out_parser import parse_out

_CENTERLINE_TOL = 1e-6


def _mirror_nodes(
    nodes: list[Node],
) -> tuple[list[Node], dict[int, int], int]:
    """Mirror right-half nodes to create left-half nodes.

    Returns (full_node_list, old_to_new_mapping_for_left, nhalf).
    Centerline nodes (x=0) are not duplicated.
    """
    nhalf = len(nodes)
    full_nodes = list(nodes)
    mirror_map: dict[int, int] = {}  # right_id -> left_id

    for node in nodes:
        if abs(node.x) < _CENTERLINE_TOL:
            # Centerline node: no mirror
            continue
        new_id = node.id + nhalf
        mirror_node = Node(id=new_id, x=-node.x, y=node.y)
        full_nodes.append(mirror_node)
        mirror_map[node.id] = new_id

    return full_nodes, mirror_map, nhalf


def _mirror_elements(
    elements: list[Element],
    mirror_map: dict[int, int],
    nhalf_elems: int,
) -> list[Element]:
    """Mirror right-half elements to create left-half elements.

    Beam elements on centerline are not duplicated.
    Quad elements with all nodes on centerline are not duplicated.
    """
    new_elements = []
    for elem in elements:
        live_nodes = [n for n in elem.nodes if n != 0]
        # Check if all live nodes are centerline (not mirrored)
        if all(n not in mirror_map for n in live_nodes):
            continue

        new_id = elem.id + nhalf_elems
        # Mirror node connectivity, reversing order to maintain element orientation
        new_nodes = tuple(
            mirror_map.get(n, n) if n != 0 else 0 for n in elem.nodes
        )
        # For quad elements, reverse winding to maintain positive orientation
        if len(new_nodes) == 4 and all(n != 0 for n in new_nodes):
            new_nodes = (new_nodes[1], new_nodes[0], new_nodes[3], new_nodes[2])

        new_elements.append(Element(
            id=new_id, nodes=new_nodes, mat=elem.mat, step=elem.step,
            type_code=elem.type_code,
        ))

    return new_elements


def _mirror_boundaries(
    boundaries: list[BoundaryCondition],
    mirror_map: dict[int, int],
    nodes: list[Node],
) -> list[BoundaryCondition]:
    """Mirror boundary conditions and fix centerline constraints.

    - Centerline BCs: remove lateral (x) displacement constraints,
      double vertical forces
    - Non-centerline BCs: create mirror copies
    """
    node_map = {n.id: n for n in nodes}
    new_bcs = []
    modified_originals = []

    for bc in boundaries:
        if bc.node in node_map and abs(node_map[bc.node].x) < _CENTERLINE_TOL:
            # Centerline node: remove x-constraint, double y-forces
            new_x_code = 0  # Free in x (no lateral constraint for full mesh)
            new_x_value = 0.0
            new_y_code = bc.y_code
            new_y_value = bc.y_value
            if bc.y_code == 0 and bc.y_value != 0.0:
                # y is a force: double it for symmetry
                new_y_value = bc.y_value * 2.0
            modified_originals.append(BoundaryCondition(
                node=bc.node, x_code=new_x_code, x_value=new_x_value,
                y_code=new_y_code, y_value=new_y_value,
                step=bc.step, angle=bc.angle,
            ))
        else:
            # Keep original
            modified_originals.append(bc)
            # Create mirror if node has a mirror
            if bc.node in mirror_map:
                new_bcs.append(BoundaryCondition(
                    node=mirror_map[bc.node],
                    x_code=bc.x_code, x_value=bc.x_value,
                    y_code=bc.y_code, y_value=bc.y_value,
                    step=bc.step, angle=bc.angle,
                ))

    return modified_originals + new_bcs


def _reorder_beam_elements(elements: list[Element], nodes: list[Node]) -> list[Element]:
    """Reorder beam elements so they ascend from left footing to right.

    Beam elements are 2-node elements. Sort them by the x-coordinate
    of their first node, ascending.
    """
    node_map = {n.id: n for n in nodes}
    beams = []
    non_beams = []

    for elem in elements:
        if len(elem.nodes) == 2:
            beams.append(elem)
        else:
            non_beams.append(elem)

    if beams:
        # Sort beams by the average x of their nodes
        def beam_x(e):
            xs = [node_map[n].x for n in e.nodes if n in node_map]
            return sum(xs) / len(xs) if xs else 0.0

        beams.sort(key=beam_x)
        # Reassign beam IDs sequentially starting from 1
        for i, beam in enumerate(beams):
            beam.id = i + 1
        # Non-beams start after beams
        offset = len(beams)
        for i, elem in enumerate(non_beams):
            elem.id = offset + i + 1

    return beams + non_beams


def half_to_full_mesh(
    cid_path: str | Path,
    out_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    problem_index: int = 0,
) -> Path:
    """Convert a Level-2 half mesh to a Level-3 full mesh.

    Parameters
    ----------
    cid_path
        Path to the Level-2 .cid input file.
    out_path
        Path to the corresponding .out file. Defaults to same name
        with .out extension.
    output_dir
        Directory for the output file. Defaults to the same directory.
    problem_index
        Which problem to convert (0-based).

    Returns
    -------
    Path to the new ``Full-{name}.cid`` file.
    """
    cid_path = Path(cid_path)
    if out_path is None:
        out_path = cid_path.with_suffix(".out")
    else:
        out_path = Path(out_path)

    if not out_path.exists():
        raise FileNotFoundError(
            f"Output file not found: {out_path}. "
            "The .cid file must have been executed by CANDE first."
        )

    # Parse the .cid for pipe groups, soil layers, etc.
    cid = parse_cid(cid_path)
    if problem_index >= len(cid.problems):
        raise ValueError(
            f"Problem index {problem_index} out of range "
            f"(file has {len(cid.problems)} problems)"
        )
    orig = cid.problems[problem_index]

    # Parse the .out file for the generated mesh
    out_data = parse_out(out_path)
    if out_data.mesh is None or not out_data.mesh.nodes:
        raise ValueError(
            "Could not extract generated mesh data from the output file. "
            "Ensure the .cid file was successfully executed by CANDE."
        )

    mesh = out_data.mesh

    # Mirror the mesh
    full_nodes, mirror_map, nhalf = _mirror_nodes(mesh.nodes)
    nhalf_elems = len(mesh.elements)
    new_elements = _mirror_elements(mesh.elements, mirror_map, nhalf_elems)
    all_elements = list(mesh.elements) + new_elements

    full_boundaries = _mirror_boundaries(mesh.boundaries, mirror_map, full_nodes)

    # Reorder beam elements for arch meshes
    all_elements = _reorder_beam_elements(all_elements, full_nodes)

    # Build the new Level-3 problem
    new_master = MasterControl(
        mode=orig.master.mode,
        level=3,
        method=orig.master.method,
        num_steps=orig.master.num_steps,
        npgrps=orig.master.npgrps,
        itmax=orig.master.itmax,
        heading=orig.master.heading,
    )

    # Build prep lines for Level-3
    num_nodes = len(full_nodes)
    num_elems = len(all_elements)
    num_bcs = len(full_boundaries)
    tag_c1 = "C-1.L3!!".rjust(24)
    tag_c2 = "C-2.L3!!".rjust(24)
    prep_lines = [
        f"{tag_c1}PREP    Full mesh from Level-2 half mesh",
        f"{tag_c2}    1    4    0    3    0{num_nodes:5d}{num_elems:5d}{num_bcs:5d}    1    0    3",
    ]

    new_problem = CidProblem(
        master=new_master,
        pipe_groups=list(orig.pipe_groups),
        prep_lines=prep_lines,
        nodes=full_nodes,
        elements=all_elements,
        boundaries=full_boundaries,
        soils=list(orig.soils),
        load_factors=list(orig.load_factors),
        has_line_tags=orig.has_line_tags,
    )
    new_problem.trailing_comments.append(
        f"* CANDE Tool Box Option 1: Full mesh created from Level-2 half mesh"
    )
    new_problem.trailing_comments.append(
        f"* Nodes: {nhalf} (half) -> {num_nodes} (full), "
        f"Elements: {nhalf_elems} -> {num_elems}, "
        f"BCs: {len(mesh.boundaries)} -> {num_bcs}"
    )

    new_cid = CidFile(problems=[new_problem])
    out_dir = Path(output_dir) if output_dir else cid_path.parent
    out_name = f"Full-{cid_path.stem}.cid"
    result_path = out_dir / out_name

    write_cid(new_cid, result_path)
    return result_path
