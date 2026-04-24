"""Option 5: Compute load rating factor RF from CANDE output files.

Reads assessment summaries and structural response data from a .out file,
computes RF = (C - D_dead) / D_live for each design criterion, and
identifies the controlling (minimum) rating factor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cande_wrapper.toolbox.out_parser import AssessmentSummary, parse_out


@dataclass
class RatingConfig:
    """Configuration for load rating analysis."""

    pipe_group: int = 1
    dead_load_step: int | None = None  # None = auto-detect
    live_load_start: int | None = None  # None = auto-detect
    live_load_end: int | None = None  # None = auto-detect


@dataclass
class CriterionRating:
    """Rating factor result for a single design criterion."""

    criterion: str
    rf: float
    node: int
    step: int
    dead_demand: float
    live_demand: float
    capacity: float


@dataclass
class NodeRating:
    """Rating factor at a specific node for a specific criterion."""

    node: int
    step: int
    rf: float
    dead_demand: float
    live_demand: float
    capacity: float


@dataclass
class RatingResult:
    """Complete load rating analysis results."""

    # Primary: overall controlling
    primary_rf: float = 0.0
    primary_criterion: str = ""
    primary_node: int = 0
    primary_step: int = 0
    is_safe: bool = False

    # Secondary: per criterion
    secondary: list[CriterionRating] = field(default_factory=list)

    # Tertiary: per criterion per node
    tertiary: dict[str, list[NodeRating]] = field(default_factory=dict)


def _find_dead_load_step(assessments: list[AssessmentSummary], group: int) -> int:
    """Auto-detect the dead load step as the highest step before live loads begin."""
    steps = sorted(set(a.step for a in assessments if a.group == group))
    if not steps:
        raise ValueError(f"No assessment data found for pipe group {group}")
    # Heuristic: dead load steps are typically the first few with lower demand
    return steps[0]


def _format_rating_report(
    result: RatingResult, config: RatingConfig, pipe_type: str, filename: str,
) -> str:
    """Format the rating report for appending to the .out file."""
    lines = [
        "",
        "* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *",
        "                -- CANDE TOOL BOX --",
        f"                LOAD RATING REPORT, PIPE-GROUP = {config.pipe_group}",
        "* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *",
        f"LOAD RATING SUMMARY FOR PIPE-GROUP = {config.pipe_group}, PIPE TYPE = {pipe_type.upper()}",
        f"CANDE FILE NAME: {filename}",
        "",
        "USER-DEFINED KEY LOAD STEPS FOR LOAD RATING ANALYSIS:",
        f"* Load step used for dead/earth load RF reference = {config.dead_load_step}",
        f"* Load step beginning live-load search range = {config.live_load_start}",
        f"* Load step terminating live-load search range = {config.live_load_end}",
        "",
        "BOTTOM LINE FINDINGS FOR LOAD RATING OF CULVERT",
        f"* Controlling design criterion = {result.primary_criterion}",
        f"* Controlling load-rating factor RF = {result.primary_rf:.2f}",
        f"* Controlling local-node number = {result.primary_node}",
        f"* Controlling live-load step number = {result.primary_step}",
        f"* Safety assessment of culvert = {'SAFE' if result.is_safe else 'NOT SAFE'}",
        "",
        "LOWEST RATING FACTORS PER DESIGN CRITERION AT CONTROLLING LOAD STEP AND NODE:",
        f"{'DESIGN-CRITERION':30s} {'LOAD':>5s} {'LOCAL':>6s} {'DEAD-LOAD':>12s} "
        f"{'LIVE-LOAD':>12s} {'EFFECTIVE':>12s} {'*RATING':>8s}",
        f"{'(Strength)':30s} {'STEP':>5s} {'NODE':>6s} {'DEMAND':>12s} "
        f"{'DEMAND':>12s} {'CAPACITY':>12s} {'FACTOR':>8s}",
    ]

    for cr in result.secondary:
        lines.append(
            f"*{cr.criterion:29s} {cr.step:5d} {cr.node:6d} "
            f"{cr.dead_demand:12.2f} {cr.live_demand:12.2f} "
            f"{cr.capacity:12.2f} {cr.rf:8.2f}"
        )

    lines.extend([
        "",
        "DEFINITIONS AND RELATIONS FOR EACH CRITERION \"n\":",
        "* Rating Factor(n) = (Capacity(n) - Dead(n))/Live(n)",
        "* Total Demand(n) = Dead(n) + Live(n) at specified node",
        "* Dead(n) = Dead load demand for criterion n (factored)",
        "* Live(n) = Live load demand for criterion n (factored)",
        "* Capacity(n) = Capacity for criterion n (factored)",
        "",
    ])

    return "\n".join(lines)


def compute_rating_factor(
    out_path: str | Path,
    config: RatingConfig | None = None,
    append_report: bool = True,
) -> RatingResult:
    """Compute load rating factors from a CANDE output file.

    Parameters
    ----------
    out_path
        Path to the .out file.
    config
        Rating configuration. Defaults to auto-detection.
    append_report
        If True, append the rating report to the .out file.

    Returns
    -------
    RatingResult with primary, secondary, and tertiary data.
    """
    if config is None:
        config = RatingConfig()

    out_path = Path(out_path)
    parsed = parse_out(out_path)

    if not parsed.assessments:
        raise ValueError("No assessment summaries found in the output file")

    # Filter assessments for the target pipe group
    group_assessments = [
        a for a in parsed.assessments if a.group == config.pipe_group
    ]
    if not group_assessments:
        raise ValueError(
            f"No assessment data for pipe group {config.pipe_group}"
        )

    pipe_type = group_assessments[0].pipe_type
    available_steps = sorted(set(a.step for a in group_assessments))

    # Auto-detect load steps
    if config.dead_load_step is None:
        # Use heuristic: find the step where element IX(6) is highest,
        # or just use the first step
        config.dead_load_step = available_steps[0]

    if config.live_load_start is None:
        config.live_load_start = config.dead_load_step + 1

    if config.live_load_end is None:
        config.live_load_end = available_steps[-1]

    # Get dead-load assessment
    dead_assessments = [
        a for a in group_assessments if a.step == config.dead_load_step
    ]
    if not dead_assessments:
        raise ValueError(
            f"No assessment data at dead load step {config.dead_load_step}"
        )
    dead_assessment = dead_assessments[0]

    # Check dead loads don't exceed capacity
    for entry in dead_assessment.entries:
        if entry.ratio > 1.0:
            result = RatingResult(
                primary_rf=-1.0,
                primary_criterion=entry.criterion,
                primary_node=entry.node,
                primary_step=config.dead_load_step,
                is_safe=False,
            )
            if append_report:
                report = _format_rating_report(
                    result, config, pipe_type, out_path.name
                )
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(report)
            return result

    # Build dead-load demand by criterion
    dead_demands: dict[str, tuple[float, int]] = {}
    for entry in dead_assessment.entries:
        dead_demands[entry.criterion] = (entry.demand, entry.node)

    # Collect all criteria
    all_criteria = list(dead_demands.keys())

    # Search through live load steps for each criterion
    tertiary: dict[str, list[NodeRating]] = {c: [] for c in all_criteria}
    secondary: list[CriterionRating] = []

    for criterion in all_criteria:
        dead_demand, _ = dead_demands.get(criterion, (0.0, 0))
        dead_capacity = 0.0

        # Find capacity from dead load assessment
        for entry in dead_assessment.entries:
            if entry.criterion == criterion:
                dead_capacity = entry.capacity
                break

        best_rf = float("inf")
        best_node = 0
        best_step = 0
        best_live = 0.0

        for step in range(config.live_load_start, config.live_load_end + 1):
            step_assessments = [
                a for a in group_assessments if a.step == step
            ]
            for assess in step_assessments:
                for entry in assess.entries:
                    if entry.criterion != criterion:
                        continue
                    # RF = (C - D_dead) / D_live
                    # D_live = D_total - D_dead
                    total_demand = entry.demand
                    live_demand = total_demand - dead_demand
                    capacity = entry.capacity

                    if live_demand > 0:
                        rf = (capacity - dead_demand) / live_demand
                    elif live_demand == 0:
                        rf = float("inf")
                    else:
                        rf = float("inf")

                    tertiary[criterion].append(NodeRating(
                        node=entry.node, step=step, rf=rf,
                        dead_demand=dead_demand,
                        live_demand=live_demand,
                        capacity=capacity,
                    ))

                    if rf < best_rf:
                        best_rf = rf
                        best_node = entry.node
                        best_step = step
                        best_live = live_demand

        if best_rf == float("inf"):
            best_rf = 9999.0

        secondary.append(CriterionRating(
            criterion=criterion,
            rf=best_rf,
            node=best_node,
            step=best_step,
            dead_demand=dead_demand,
            live_demand=best_live,
            capacity=dead_capacity,
        ))

    # Primary: overall controlling
    if secondary:
        controlling = min(secondary, key=lambda c: c.rf)
        primary_rf = controlling.rf
        primary_criterion = controlling.criterion
        primary_node = controlling.node
        primary_step = controlling.step
    else:
        primary_rf = 0.0
        primary_criterion = ""
        primary_node = 0
        primary_step = 0

    result = RatingResult(
        primary_rf=primary_rf,
        primary_criterion=primary_criterion,
        primary_node=primary_node,
        primary_step=primary_step,
        is_safe=primary_rf >= 1.0,
        secondary=secondary,
        tertiary=tertiary,
    )

    if append_report:
        report = _format_rating_report(result, config, pipe_type, out_path.name)
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(report)

    return result
