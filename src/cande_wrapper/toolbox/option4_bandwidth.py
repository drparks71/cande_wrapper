"""Option 4: Minimize bandwidth by permanently renumbering nodes.

Renumbers nodes in a Level-3 .cid file to reduce the maximum difference
in node numbers within any single element (the bandwidth). Uses a geometric
column-sweep strategy: start at the lower-left corner and number upward,
then shift right.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from cande_wrapper.toolbox.cid_model import CidProblem
from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.cid_writer import write_cid


def _compute_bandwidth(problem: CidProblem) -> int:
    """Compute the current bandwidth of the mesh."""
    bw = 0
    for elem in problem.elements:
        live = [n for n in elem.nodes if n != 0]
        if len(live) >= 2:
            bw = max(bw, max(live) - min(live))
    return bw


def _geometric_renumber(problem: CidProblem) -> dict[int, int]:
    """Build an old->new node mapping using column-sweep from lower-left.

    Groups nodes into vertical columns by x-coordinate, then numbers
    upward within each column, sweeping left to right.
    """
    nodes = problem.nodes
    if not nodes:
        return {}

    # Tolerance for grouping nodes into the same column
    xs = sorted(set(n.x for n in nodes))
    tol = min((xs[i + 1] - xs[i]) for i in range(len(xs) - 1)) * 0.1 if len(xs) > 1 else 1.0

    # Group nodes by column (x-coordinate)
    columns: dict[float, list] = defaultdict(list)
    for n in nodes:
        # Find the canonical x for this column
        placed = False
        for cx in sorted(columns.keys()):
            if abs(n.x - cx) < tol:
                columns[cx].append(n)
                placed = True
                break
        if not placed:
            columns[n.x].append(n)

    # Sort columns left to right, nodes within each column bottom to top
    mapping: dict[int, int] = {}
    new_id = 1
    for col_x in sorted(columns.keys()):
        col_nodes = sorted(columns[col_x], key=lambda n: n.y)
        for node in col_nodes:
            mapping[node.id] = new_id
            new_id += 1

    return mapping


def _apply_renumbering(problem: CidProblem, mapping: dict[int, int]) -> None:
    """Apply a node renumbering to all nodes, elements, and boundary conditions."""
    for node in problem.nodes:
        node.id = mapping.get(node.id, node.id)

    for elem in problem.elements:
        new_nodes = tuple(mapping.get(n, n) if n != 0 else 0 for n in elem.nodes)
        elem.nodes = new_nodes

    for bc in problem.boundaries:
        bc.node = mapping.get(bc.node, bc.node)


def minimize_bandwidth(
    cid_path: str | Path,
    output_dir: str | Path | None = None,
    problem_index: int = 0,
) -> Path:
    """Minimize bandwidth of a Level-3 mesh by renumbering nodes.

    Parameters
    ----------
    cid_path
        Path to the originating .cid file.
    output_dir
        Directory for the output file. Defaults to the same directory.
    problem_index
        Which problem in the file to process (0-based).

    Returns
    -------
    Path to the new ``Bmin-{name}.cid`` file.
    """
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
            f"Option 4 requires a Level-3 input file, "
            f"got Level-{problem.master.level}"
        )

    old_bw = _compute_bandwidth(problem)
    mapping = _geometric_renumber(problem)
    _apply_renumbering(problem, mapping)
    new_bw = _compute_bandwidth(problem)

    # Add a comment documenting the renumbering
    problem.trailing_comments.append(
        f"* CANDE Tool Box Option 4: Bandwidth minimized from {old_bw} to {new_bw}"
    )

    out_dir = Path(output_dir) if output_dir else cid_path.parent
    out_name = f"Bmin-{cid_path.stem}.cid"
    out_path = out_dir / out_name

    write_cid(cid, out_path)
    return out_path
