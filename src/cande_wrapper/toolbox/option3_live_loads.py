"""Option 3: Add live loads on the upper surface.

Extends a Level-3 .cid file with boundary conditions that simulate
a vehicle (truck) traveling over the mesh surface. Supports AASHTO
HL93 design truck, tandem, or user-defined vehicles with up to 10 axles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cande_wrapper.toolbox.cid_model import (
    BoundaryCondition,
    CidProblem,
    LoadFactor,
    Node,
    ScalingLine,
)
from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.cid_writer import write_cid
from cande_wrapper.toolbox.load_spreading import (
    compute_cls_thickness_factor,
    compute_fox_beta_w,
    compute_impact_factor,
    compute_rsl_factor,
    two_wheel_interaction_depth,
)
from cande_wrapper.vehicle import Vehicle


@dataclass
class LiveLoadConfig:
    """Configuration for adding live loads (Option 3)."""

    pipe_group: int = 1
    vehicle: Vehicle | None = None  # None = HL93 design truck

    # Load modifications
    lane_pressure: float | None = None  # psi; None=skip, 0.444=AASHTO
    impact_factor: float | str | None = None  # float=constant, "variable", None=skip
    multilane_factor: float | None = None  # None=skip, 0.2=AASHTO

    # Longitudinal load spreading
    spreading_method: str | None = None  # "RSL", "CLS", or None
    rsl_variant: int = 1  # 1=constant, 2=variable; sign: +1=span term, -1=no span
    include_span_term: bool = True

    # Pavement Fox parameters
    pavement_thickness: float = 0.0  # inches
    epave_esoil: float = 100.0

    # 3DSE
    culvert_length_ft: float = 0.0  # feet; 0=disabled
    w_min: float | None = None  # inches; None=AASHTO default
    w_critical: float | None = None

    # Vehicle travel
    key_axle: int | None = None  # None=auto (heaviest)
    start_node: int | None = None  # None=auto
    end_node: int | None = None  # None=auto
    start_step: int | None = None  # None=auto
    non_key_method: int = 1  # 1=nearest, 2=proportional

    # Clearing old live loads
    clear_previous_step: int | None = None

    # LRFD
    load_factor: float = 1.75


def _get_surface_nodes(problem: CidProblem) -> list[Node]:
    """Find surface nodes sorted left to right by x-coordinate."""
    if not problem.nodes:
        return []

    node_map = {n.id: n for n in problem.nodes}
    max_y = max(n.y for n in problem.nodes)
    tol = 1e-6

    surface_node_ids: set[int] = set()
    for elem in problem.elements:
        if len(elem.nodes) < 4:
            continue
        live = [n for n in elem.nodes if n != 0]
        for nid in live:
            if nid in node_map and abs(node_map[nid].y - max_y) < tol:
                surface_node_ids.add(nid)

    surface = [node_map[nid] for nid in surface_node_ids]
    surface.sort(key=lambda n: n.x)
    return surface


def _find_cover_and_span(
    problem: CidProblem, pipe_group: int
) -> tuple[float, float, list[Node]]:
    """Find the cover height and span for a pipe group.

    Returns (cover_height_inches, span_inches, pipe_nodes).
    """
    node_map = {n.id: n for n in problem.nodes}
    surface_nodes = _get_surface_nodes(problem)
    if not surface_nodes:
        return 0.0, 0.0, []

    surface_y = surface_nodes[0].y

    # Find beam elements belonging to this pipe group
    pipe_nodes_ids: set[int] = set()
    for elem in problem.elements:
        if elem.mat == pipe_group and len(elem.nodes) == 2:
            for nid in elem.nodes:
                if nid != 0:
                    pipe_nodes_ids.add(nid)

    if not pipe_nodes_ids:
        # Fall back to all beam elements
        for elem in problem.elements:
            if len(elem.nodes) == 2:
                for nid in elem.nodes:
                    if nid != 0:
                        pipe_nodes_ids.add(nid)

    pipe_nodes = [node_map[nid] for nid in pipe_nodes_ids if nid in node_map]
    if not pipe_nodes:
        return 0.0, 0.0, []

    max_pipe_y = max(n.y for n in pipe_nodes)
    min_pipe_x = min(n.x for n in pipe_nodes)
    max_pipe_x = max(n.x for n in pipe_nodes)

    cover = surface_y - max_pipe_y
    span = max_pipe_x - min_pipe_x

    return cover, span, pipe_nodes


def _determine_key_axle(vehicle: Vehicle) -> int:
    """Determine the key (heaviest) axle index (0-based)."""
    max_weight = 0.0
    key = 0
    for i, axle in enumerate(vehicle.axles):
        if axle.weight > max_weight:
            max_weight = axle.weight
            key = i
    return key


def _compute_axle_positions(
    vehicle: Vehicle, key_axle_idx: int, key_axle_x: float
) -> list[float]:
    """Compute the x-position of each axle given the key axle position."""
    positions = [0.0] * len(vehicle.axles)
    positions[key_axle_idx] = key_axle_x

    # Compute cumulative distances from axle 0
    cumulative = [0.0]
    for i in range(1, len(vehicle.axles)):
        cumulative.append(cumulative[-1] + vehicle.axles[i].spacing)

    key_cumulative = cumulative[key_axle_idx]
    for i in range(len(vehicle.axles)):
        positions[i] = key_axle_x + (cumulative[i] - key_cumulative)

    return positions


def _find_nearest_nodes(
    x: float, surface_nodes: list[Node], method: int = 1
) -> list[tuple[int, float]]:
    """Find the surface node(s) nearest to position x.

    Returns list of (node_id, fraction) pairs.
    method=1: single nearest node (fraction=1.0)
    method=2: two bracketing nodes with proportional fractions
    """
    if not surface_nodes:
        return []

    # Find bracketing nodes
    left_node = None
    right_node = None
    for node in surface_nodes:
        if node.x <= x:
            if left_node is None or node.x > left_node.x:
                left_node = node
        if node.x >= x:
            if right_node is None or node.x < right_node.x:
                right_node = node

    if left_node is None:
        left_node = surface_nodes[0]
    if right_node is None:
        right_node = surface_nodes[-1]

    if left_node.id == right_node.id:
        return [(left_node.id, 1.0)]

    if method == 1:
        # Single nearest node
        if abs(x - left_node.x) <= abs(x - right_node.x):
            return [(left_node.id, 1.0)]
        else:
            return [(right_node.id, 1.0)]
    else:
        # Proportional distribution to two nodes
        dx = right_node.x - left_node.x
        if dx < 1e-10:
            return [(left_node.id, 1.0)]
        frac_right = (x - left_node.x) / dx
        frac_left = 1.0 - frac_right
        result = []
        if frac_left > 1e-10:
            result.append((left_node.id, frac_left))
        if frac_right > 1e-10:
            result.append((right_node.id, frac_right))
        return result


def _compute_line_load(
    axle_weight: float,
    footprint_length: float,
    impact_mult: float,
    multilane_mult: float,
    rsl_factor: float,
) -> float:
    """Compute the line load (lbs/in) for one wheel of an axle.

    line_load = (axle_weight / 2) / footprint_length * modifiers * RSL
    """
    wheel_load = axle_weight / 2.0  # per wheel
    line_load = wheel_load / footprint_length if footprint_length > 0 else wheel_load
    line_load *= impact_mult * multilane_mult * rsl_factor
    return line_load


def add_live_loads(
    cid_path: str | Path,
    config: LiveLoadConfig | None = None,
    output_dir: str | Path | None = None,
    problem_index: int = 0,
) -> Path:
    """Add live loads to a Level-3 mesh surface.

    Parameters
    ----------
    cid_path
        Path to the Level-3 .cid file.
    config
        Live load configuration. Defaults to HL93 design truck with
        AASHTO defaults.
    output_dir
        Directory for the output file.
    problem_index
        Which problem to process (0-based).

    Returns
    -------
    Path to the new ``Live-{name}.cid`` file.
    """
    if config is None:
        config = LiveLoadConfig()

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
            f"Option 3 requires a Level-3 input file, "
            f"got Level-{problem.master.level}"
        )

    # Default vehicle: HL93 design truck
    vehicle = config.vehicle or Vehicle.hs20()
    footprint = vehicle.footprint

    # Find surface nodes and pipe geometry
    surface_nodes = _get_surface_nodes(problem)
    if not surface_nodes:
        raise ValueError("No surface nodes found in the mesh")

    cover_in, span_in, pipe_nodes = _find_cover_and_span(problem, config.pipe_group)
    cover_ft = cover_in / 12.0

    # Determine key axle
    key_axle_idx = config.key_axle if config.key_axle is not None else _determine_key_axle(vehicle)

    # Determine travel path nodes
    if config.start_node is not None:
        start_idx = next(
            (i for i, n in enumerate(surface_nodes) if n.id == config.start_node),
            0,
        )
    else:
        # Default: above left periphery of structure
        if pipe_nodes:
            left_x = min(n.x for n in pipe_nodes)
            start_idx = min(
                range(len(surface_nodes)),
                key=lambda i: abs(surface_nodes[i].x - left_x),
            )
        else:
            start_idx = 0

    if config.end_node is not None:
        end_idx = next(
            (i for i, n in enumerate(surface_nodes) if n.id == config.end_node),
            len(surface_nodes) - 1,
        )
    else:
        if pipe_nodes:
            right_x = max(n.x for n in pipe_nodes)
            end_idx = min(
                range(len(surface_nodes)),
                key=lambda i: abs(surface_nodes[i].x - right_x),
            )
        else:
            end_idx = len(surface_nodes) - 1

    travel_nodes = surface_nodes[start_idx:end_idx + 1]
    if not travel_nodes:
        raise ValueError("No travel path nodes found")

    # Compute load modification multipliers
    impact_mult = 1.0
    if config.impact_factor is not None:
        if isinstance(config.impact_factor, (int, float)):
            impact_mult = 1.0 + float(config.impact_factor)
        elif config.impact_factor == "variable":
            im = compute_impact_factor(cover_ft)
            impact_mult = 1.0 + im

    multilane_mult = 1.0
    if config.multilane_factor is not None:
        multilane_mult = 1.0 + config.multilane_factor

    # Compute RSL factor (constant mode)
    rsl_factor = 1.0
    using_cls = config.spreading_method and config.spreading_method.upper() == "CLS"
    using_rsl = config.spreading_method and config.spreading_method.upper() == "RSL"

    if using_rsl and abs(config.rsl_variant) == 1:
        rsl_factor = compute_rsl_factor(
            cover_depth=cover_in,
            span=span_in,
            footprint_length=footprint.length,
            footprint_width=footprint.width,
            wheel_spacing=footprint.spacing,
            include_span_term=config.include_span_term,
            pavement_thickness=config.pavement_thickness,
            epave_esoil=config.epave_esoil,
            culvert_length=config.culvert_length_ft * 12.0,
            w_min=config.w_min,
            w_critical=config.w_critical,
        )

    # Clear previous live loads if requested
    if config.clear_previous_step is not None:
        problem.boundaries = [
            bc for bc in problem.boundaries
            if bc.step < config.clear_previous_step
        ]

    # Determine starting load step
    if config.start_step is not None:
        current_step = config.start_step
    else:
        existing_steps = [bc.step for bc in problem.boundaries]
        current_step = max(existing_steps, default=0) + 1

    # Add lane pressure if requested
    if config.lane_pressure is not None and config.lane_pressure > 0:
        lane_load = config.lane_pressure  # psi = lbs/in^2
        for node in surface_nodes:
            problem.boundaries.append(BoundaryCondition(
                node=node.id, x_code=0, x_value=0.0,
                y_code=0, y_value=-lane_load,
                step=current_step,
            ))
        current_step += 1

    # Generate live load boundary conditions for vehicle travel
    h_interact = two_wheel_interaction_depth(footprint.length, footprint.spacing)

    for travel_node in travel_nodes:
        key_x = travel_node.x
        axle_positions = _compute_axle_positions(vehicle, key_axle_idx, key_x)

        step_loads: dict[int, float] = {}  # node_id -> total load

        for axle_idx, axle in enumerate(vehicle.axles):
            axle_x = axle_positions[axle_idx]

            # Variable RSL: compute per-node
            local_rsl = rsl_factor
            if using_rsl and abs(config.rsl_variant) == 2:
                # Variable RSL based on depth at this position
                # Approximate depth as cover + some function of position
                local_rsl = compute_rsl_factor(
                    cover_depth=cover_in,
                    span=span_in,
                    footprint_length=footprint.length,
                    footprint_width=footprint.width,
                    wheel_spacing=footprint.spacing,
                    include_span_term=config.include_span_term,
                    pavement_thickness=config.pavement_thickness,
                    epave_esoil=config.epave_esoil,
                )

            if using_cls:
                local_rsl = 1.0  # CLS doesn't reduce surface loads

            line_load = _compute_line_load(
                axle.weight, footprint.length,
                impact_mult, multilane_mult, local_rsl,
            )

            # Apply to node(s)
            if axle_idx == key_axle_idx:
                # Key axle: always at exact node
                node_loads = [(travel_node.id, 1.0)]
            else:
                method = config.non_key_method
                node_loads = _find_nearest_nodes(axle_x, surface_nodes, method)

            for node_id, frac in node_loads:
                step_loads[node_id] = step_loads.get(node_id, 0.0) - line_load * frac

        # Create boundary conditions for this load step
        for node_id, load_val in sorted(step_loads.items()):
            problem.boundaries.append(BoundaryCondition(
                node=node_id, x_code=0, x_value=0.0,
                y_code=0, y_value=load_val,
                step=current_step,
            ))

        current_step += 1

    # Add CLS scaling lines if needed
    if using_cls:
        node_map = {n.id: n for n in problem.nodes}
        surface_y = max(n.y for n in problem.nodes)
        for elem in problem.elements:
            if len(elem.nodes) < 4:
                continue
            live = [n for n in elem.nodes if n != 0 and n in node_map]
            if not live:
                continue
            centroid_y = sum(node_map[n].y for n in live) / len(live)
            depth = surface_y - centroid_y
            if depth > 0:
                factor = compute_cls_thickness_factor(
                    depth, footprint.length, footprint.width, footprint.spacing,
                )
                if factor > 1.0:
                    problem.scaling_lines.append(
                        ScalingLine(raw_line=f"  {elem.id:5d}{factor:10.4f}")
                    )

    # Add LRFD load factors for live load steps
    start_ll_step = current_step - len(travel_nodes)
    if config.lane_pressure is not None and config.lane_pressure > 0:
        start_ll_step -= 1
    for step in range(start_ll_step, current_step):
        problem.load_factors.append(
            LoadFactor(step=step, factor=config.load_factor)
        )

    # Update num_steps in master control
    problem.master.num_steps = max(
        problem.master.num_steps, current_step - 1
    )

    # Document
    fox_beta = ""
    if config.pavement_thickness > 0:
        bw = compute_fox_beta_w(
            config.pavement_thickness, config.epave_esoil, footprint.length
        )
        fox_beta = f", Fox beta_W={bw:.3f}"

    problem.trailing_comments.extend([
        f"* CANDE Tool Box Option 3: Live loads added",
        f"* Vehicle: {vehicle.name}, {len(vehicle.axles)} axles, "
        f"total weight={vehicle.total_weight:.0f} lbs",
        f"* Key axle: {key_axle_idx + 1}, "
        f"travel nodes: {travel_nodes[0].id} to {travel_nodes[-1].id}",
        f"* Impact={impact_mult:.3f}, multilane={multilane_mult:.3f}",
        f"* Spreading: {config.spreading_method or 'none'}"
        f"{fox_beta}",
        f"* LRFD load factor={config.load_factor}",
    ])

    out_dir = Path(output_dir) if output_dir else cid_path.parent
    out_name = f"Live-{cid_path.stem}.cid"
    out_path = out_dir / out_name

    write_cid(cid, out_path)
    return out_path
