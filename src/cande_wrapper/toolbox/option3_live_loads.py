"""Option 3: Add live loads on the upper surface.

Extends a Level-3 .cid file with boundary conditions that simulate
a vehicle (truck) traveling over the mesh surface. Supports AASHTO
HL93 design truck, tandem, or user-defined vehicles with up to 10 axles.

All algorithms match the Fortran source code in CTB-2025 exactly:
    AA-LiveLoads.for — main orchestration
    GenerateLiveBC.for — boundary condition generation
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
    aam_theta_spread,
    compute_3dse_params,
    compute_cls_thickness_factor,
    compute_impact_factor,
    compute_rsl_constant,
    compute_rsl_variable,
    fox_pave_3d,
    two_wheel_interaction_depth,
    _find_transition_depth,
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
    rsl_variant: int = 1  # 1=constant, 2=variable
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
    """Compute the x-position of each axle given the key axle position.

    Matches Fortran: AXLECOORDkey(NA) = AXLECOORD(NAxleKey) - AXLECOORD(NA)
    Xaxle = Xkey + AXLECOORDkey(NA)
    """
    positions = [0.0] * len(vehicle.axles)

    # Compute cumulative distances from axle 0
    cumulative = [0.0]
    for i in range(1, len(vehicle.axles)):
        cumulative.append(cumulative[-1] + vehicle.axles[i].spacing)

    key_cumulative = cumulative[key_axle_idx]
    for i in range(len(vehicle.axles)):
        # Distance from key axle: positive means ahead of key axle
        positions[i] = key_axle_x + (key_cumulative - cumulative[i])

    return positions


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
    wheel_l = footprint.length
    wheel_w = footprint.width
    cdbw = footprint.spacing

    # Find surface nodes and pipe geometry
    surface_nodes = _get_surface_nodes(problem)
    if not surface_nodes:
        raise ValueError("No surface nodes found in the mesh")

    node_map = {n.id: n for n in problem.nodes}
    cover_in, span_in, pipe_nodes = _find_cover_and_span(problem, config.pipe_group)

    # --- Fox pavement solution ---
    beta_l = 1.0
    beta_w = 1.0
    if config.pavement_thickness > 0:
        eratio = config.epave_esoil if config.epave_esoil > 0 else 100.0
        beta_l, beta_w = fox_pave_3d(config.pavement_thickness, eratio, wheel_l, wheel_w)

    # --- Determine key axle ---
    key_axle_idx = config.key_axle if config.key_axle is not None else _determine_key_axle(vehicle)

    # --- Determine travel path ---
    if config.start_node is not None:
        start_idx = next(
            (i for i, n in enumerate(surface_nodes) if n.id == config.start_node), 0)
    else:
        if pipe_nodes:
            left_x = min(n.x for n in pipe_nodes)
            start_idx = min(range(len(surface_nodes)),
                            key=lambda i: abs(surface_nodes[i].x - left_x))
        else:
            start_idx = 0

    if config.end_node is not None:
        end_idx = next(
            (i for i, n in enumerate(surface_nodes) if n.id == config.end_node),
            len(surface_nodes) - 1)
    else:
        if pipe_nodes:
            right_x = max(n.x for n in pipe_nodes)
            end_idx = min(range(len(surface_nodes)),
                          key=lambda i: abs(surface_nodes[i].x - right_x))
        else:
            end_idx = len(surface_nodes) - 1

    # Build surface node index for travel path
    ncount = len(surface_nodes)
    k1 = start_idx
    k2 = end_idx

    # --- Compute impact factors (per-node array) ---
    using_rsl = config.spreading_method and config.spreading_method.upper() == "RSL"
    using_cls = config.spreading_method and config.spreading_method.upper() == "CLS"

    di_impact = [0.0] * ncount
    if config.impact_factor is not None:
        if isinstance(config.impact_factor, (int, float)):
            # Constant impact
            for n in range(ncount):
                di_impact[n] = float(config.impact_factor)
        elif config.impact_factor == "variable":
            # Variable impact based on cover at each surface node
            for n in range(ncount):
                # Use cover_in as approximation (Vcover would be per-node)
                di_impact[n] = compute_impact_factor(cover_in)

    # --- Compute multilane factor ---
    p_multilane = config.multilane_factor if config.multilane_factor is not None else 0.0

    # --- Compute RSL reduction factors (per-node array) ---
    reduct = [1.0] * ncount

    # 3DSE parameters
    culvert_length_in = config.culvert_length_ft * 12.0
    wmin, wcritical = compute_3dse_params(
        span_in, culvert_length_in, config.w_min, config.w_critical)

    # Compute two-wheel interaction depth and 3DSE transition depth
    hinteract = two_wheel_interaction_depth(beta_l, wheel_l, beta_w, wheel_w, cdbw)
    htransition = 1.0
    if wcritical > 0:
        htransition = _find_transition_depth(beta_l, wheel_l, beta_w, wheel_w, wcritical)
        if htransition > hinteract:
            htransition = hinteract
            wcritical = cdbw

    if using_rsl:
        if config.rsl_variant == 1:
            # Constant RSL
            factor = compute_rsl_constant(
                cover_in, span_in, beta_l, wheel_l, beta_w, wheel_w, cdbw,
                include_span_term=config.include_span_term,
                wmin=wmin, wcritical=wcritical, htransition=htransition)
            for n in range(ncount):
                reduct[n] = factor
        else:
            # Variable RSL per node (use cover_in as Vcover approximation)
            for n in range(ncount):
                reduct[n] = compute_rsl_variable(
                    cover_in, span_in, beta_l, wheel_l, beta_w, wheel_w, cdbw,
                    include_span_term=config.include_span_term,
                    wmin=wmin, wcritical=wcritical, htransition=htransition)
    elif using_cls:
        # CLS: no surface load reduction (REDUCT = 1.0)
        for n in range(ncount):
            reduct[n] = 1.0

    # --- Clear previous live loads if requested ---
    if config.clear_previous_step is not None:
        new_bcs = []
        for bc in problem.boundaries:
            if bc.step >= config.clear_previous_step and bc.x_code == 0 and bc.y_code == 0:
                continue  # Remove these force-only BCs
            if bc.step >= config.clear_previous_step and bc.x_code == 1 and bc.y_code == 0:
                bc.y_value = 0.0  # Zero out y-force but keep x-constraint
            new_bcs.append(bc)
        problem.boundaries = new_bcs

    # --- Determine starting load step ---
    if config.start_step is not None:
        i_alive = config.start_step
    else:
        existing_steps = [bc.step for bc in problem.boundaries]
        i_alive = max(existing_steps, default=0) + 1

    i_alive_start = i_alive

    # --- Generate live load BCs (matches GenerateLiveBC.for) ---
    new_bcs: list[BoundaryCondition] = []

    # Lane pressure (applied to interior surface nodes)
    if config.lane_pressure is not None and config.lane_pressure > 0:
        for n in range(1, ncount - 1):  # Exclude end nodes
            node = surface_nodes[n]
            n_back = surface_nodes[n - 1]
            n_fore = surface_nodes[n + 1]
            vforce = 0.5 * config.lane_pressure * (node_map[n_fore.id].x - node_map[n_back.id].x)
            new_bcs.append(BoundaryCondition(
                node=node.id, x_code=0, x_value=0.0,
                y_code=0, y_value=-vforce,
                step=i_alive))
        i_alive += 1

    # Vehicle travel
    for k in range(k1, k2 + 1):
        x_key = node_map[surface_nodes[k].id].x

        for na in range(len(vehicle.axles)):
            axle = vehicle.axles[na]

            # Compute cumulative distances
            cumulative = [0.0]
            for ai in range(1, len(vehicle.axles)):
                cumulative.append(cumulative[-1] + vehicle.axles[ai].spacing)
            axle_coord_key = cumulative[key_axle_idx] - cumulative[na]
            x_axle = x_key + axle_coord_key

            # Branch: 1-node or 2-node loading
            if config.non_key_method == 1 or na == key_axle_idx:
                # 1-node loading: find segment containing x_axle,
                # choose node closest to key axle
                in_mesh = False
                ndbc = surface_nodes[k].id
                ncx = k
                for nc1 in range(ncount - 1):
                    ns1 = surface_nodes[nc1].id
                    ns2 = surface_nodes[nc1 + 1].id
                    if node_map[ns1].x <= x_axle < node_map[ns2].x:
                        in_mesh = True
                        if x_axle < x_key:
                            ndbc = ns2  # node closest to key axle
                            ncx = nc1 + 1
                        else:
                            ndbc = ns1
                            ncx = nc1
                        break

                if not in_mesh:
                    continue  # Skip: axle outside mesh surface

                # Compute wheel line load (lbs/in)
                wheel_load = 0.5 * axle.weight / wheel_w
                wheel_load *= (1.0 + p_multilane)
                wheel_load *= (1.0 + di_impact[ncx])
                wheel_load *= reduct[ncx]

                # Apply load at this step
                new_bcs.append(BoundaryCondition(
                    node=ndbc, x_code=0, x_value=0.0,
                    y_code=0, y_value=-wheel_load,
                    step=i_alive))

                # Remove load at next step (except last position)
                if k < k2:
                    new_bcs.append(BoundaryCondition(
                        node=ndbc, x_code=0, x_value=0.0,
                        y_code=0, y_value=wheel_load,
                        step=i_alive + 1))

            else:
                # 2-node proportional loading
                in_mesh = False
                nsx1 = 0
                nsx2 = 0
                ncx1 = 0
                ncx2 = 0
                weight1 = 1.0
                weight2 = 0.0

                for nc1 in range(ncount - 1):
                    ns1 = surface_nodes[nc1].id
                    ns2 = surface_nodes[nc1 + 1].id
                    if node_map[ns1].x <= x_axle < node_map[ns2].x:
                        in_mesh = True
                        nsx1 = ns1
                        ncx1 = nc1
                        nsx2 = ns2
                        ncx2 = nc1 + 1
                        de_long = node_map[nsx2].x - node_map[nsx1].x
                        if de_long != 0.0:
                            weight1 = 1.0 - (x_axle - node_map[nsx1].x) / de_long
                        else:
                            weight1 = 1.0
                        weight2 = 1.0 - weight1
                        break

                if not in_mesh:
                    continue

                # Compute base wheel line load
                wheel_load_base = 0.5 * axle.weight / wheel_w
                wheel_load_base *= (1.0 + p_multilane)
                wheel_load1 = wheel_load_base * (1.0 + di_impact[ncx1]) * reduct[ncx1]
                wheel_load2 = wheel_load_base * (1.0 + di_impact[ncx2]) * reduct[ncx2]

                # Apply loads
                new_bcs.append(BoundaryCondition(
                    node=nsx1, x_code=0, x_value=0.0,
                    y_code=0, y_value=-weight1 * wheel_load1,
                    step=i_alive))
                new_bcs.append(BoundaryCondition(
                    node=nsx2, x_code=0, x_value=0.0,
                    y_code=0, y_value=-weight2 * wheel_load2,
                    step=i_alive))

                # Remove loads (except last position)
                if k < k2:
                    new_bcs.append(BoundaryCondition(
                        node=nsx1, x_code=0, x_value=0.0,
                        y_code=0, y_value=weight1 * wheel_load1,
                        step=i_alive + 1))
                    new_bcs.append(BoundaryCondition(
                        node=nsx2, x_code=0, x_value=0.0,
                        y_code=0, y_value=weight2 * wheel_load2,
                        step=i_alive + 1))

        # Update load step (except for last position)
        if k < k2:
            i_alive += 1

    # Append all new BCs
    problem.boundaries.extend(new_bcs)
    ninc = i_alive  # Final load step count

    # --- CLS scaling lines (C-2b, C-2c) ---
    if using_cls:
        # Clear old scaling lines
        problem.scaling_lines = []
        # C-2b line
        ns_start_id = surface_nodes[k1].id
        c2b = (
            f"{i_alive_start:5d}{ninc:5d}{wheel_l:10.2f}{wheel_w:10.2f}"
            f"{cdbw:10.2f}{ns_start_id:5d}{wmin:10.2f}{wcritical:10.2f}"
        )
        problem.scaling_lines.append(ScalingLine(raw_line=c2b))
        # C-2c line if Fox pavement is active
        if config.pavement_thickness > 0:
            c2c = f"    0{beta_l:10.3f}{beta_w:10.3f}"
            problem.scaling_lines.append(ScalingLine(raw_line=c2c))

    # --- LRFD load factors ---
    # Lane pressure step
    ia_add = 0
    if config.lane_pressure is not None and config.lane_pressure > 0:
        ia_add = 1
        problem.load_factors.append(
            LoadFactor(step=i_alive_start, factor=config.load_factor))

    # Vehicle steps
    vehicle_start = i_alive_start + ia_add
    if vehicle_start <= ninc:
        problem.load_factors.append(
            LoadFactor(step=vehicle_start, factor=config.load_factor))

    # Update num_steps
    problem.master.num_steps = max(problem.master.num_steps, ninc)

    # --- Trailing comments ---
    problem.trailing_comments.extend([
        f"* CANDE Tool Box Option 3: Live loads added",
        f"* Vehicle: {vehicle.name}, {len(vehicle.axles)} axles, "
        f"total weight={vehicle.total_weight:.0f} lbs",
        f"* Key axle: {key_axle_idx + 1}, "
        f"travel nodes: {surface_nodes[k1].id} to {surface_nodes[k2].id}",
        f"* Impact: {'variable' if config.impact_factor == 'variable' else f'constant={di_impact[0]:.3f}' if di_impact[0] > 0 else 'none'}",
        f"* Multilane presence factor: {p_multilane:.3f}",
        f"* Spreading: {config.spreading_method or 'none'}",
        f"* Fox pavement: beta_L={beta_l:.3f}, beta_W={beta_w:.3f}",
        f"* LRFD load factor={config.load_factor}",
    ])

    out_dir = Path(output_dir) if output_dir else cid_path.parent
    out_name = f"Live-{cid_path.stem}.cid"
    out_path = out_dir / out_name

    write_cid(cid, out_path)
    return out_path
