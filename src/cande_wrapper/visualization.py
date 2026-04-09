"""Visualization tools for CANDE FEA results using Plotly.

Parses CANDE XML output files (MeshGeom, MeshResults, BeamResults) and
produces interactive Plotly figures for mesh geometry, deformed shapes,
beam forces, soil stresses, and load history.

Requires the ``plotly`` package::

    pip install cande-wrapper[viz]
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# XML Parsers
# ---------------------------------------------------------------------------

def parse_mesh_geom(xml_path: str | Path) -> dict:
    """Parse a CANDE ``*_MeshGeom.xml`` file.

    Returns
    -------
    dict
        Keys: ``heading``, ``nodes`` (list of dicts with id/x/y),
        ``elements`` (list of dicts with id/nodes/mat/type),
        ``boundaries`` (list of dicts).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ctrl = root.find("Control")
    heading_el = ctrl.find("Heading")
    heading = heading_el.text.strip() if heading_el is not None and heading_el.text else ""

    nodes = []
    for nc in root.iter("nodeCoord"):
        nodes.append({
            "id": int(nc.findtext("nodeNumber")),
            "x": float(nc.findtext("nodeXCoord")),
            "y": float(nc.findtext("nodeYCoord")),
        })

    elements = []
    for ec in root.iter("elemConn"):
        elements.append({
            "id": int(ec.findtext("elemNumber")),
            "n1": int(ec.findtext("elemNode1")),
            "n2": int(ec.findtext("elemNode2")),
            "n3": int(ec.findtext("elemNode3")),
            "n4": int(ec.findtext("elemNode4")),
            "mat": int(ec.findtext("elemMatNum")),
            "incr": int(ec.findtext("elemConstrIncr")),
            "type": ec.findtext("elemType").strip(),
        })

    boundaries = []
    for b in root.iter("boundary"):
        boundaries.append({
            "id": int(b.findtext("boundNumber")),
            "node": int(b.findtext("boundNode")),
            "incr": int(b.findtext("boundConstrIncr")),
            "x_code": int(b.findtext("boundXCode")),
            "y_code": int(b.findtext("boundYCode")),
            "x_force": float(b.findtext("boundXForce")),
            "y_force": float(b.findtext("boundYForce")),
            "rot_angle": float(b.findtext("boundRotAngle")),
        })

    return {
        "heading": heading,
        "nodes": nodes,
        "elements": elements,
        "boundaries": boundaries,
    }


def parse_mesh_results(xml_path: str | Path) -> dict:
    """Parse a CANDE ``*_MeshResults.xml`` file.

    Returns
    -------
    dict
        Keys: ``heading``, ``steps`` (list of dicts, each with
        ``step``, ``node_displacements``, ``element_results``).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ctrl = root.find("Control")
    heading_el = ctrl.find("Heading")
    heading = heading_el.text.strip() if heading_el is not None and heading_el.text else ""

    steps = []
    for dd in root.iter("displacementData"):
        step_num = int(dd.findtext("dispConstIncr"))

        node_disps = []
        for nd in dd.iter("nodeDisp"):
            node_disps.append({
                "id": int(nd.findtext("nodeDispNumber")),
                "dx": float(nd.findtext("nodeXDisp")),
                "dy": float(nd.findtext("nodeYDisp")),
            })

        elem_results = []
        for ed in dd.iter("elemDisp"):
            elem_results.append({
                "id": int(ed.findtext("elemDispNumber")),
                "type": ed.findtext("elemDispType").strip(),
                "st1": float(ed.findtext("st1")),
                "st2": float(ed.findtext("st2")),
                "st3": float(ed.findtext("st3")),
                "st4": float(ed.findtext("st4")),
                "st5": float(ed.findtext("st5")),
                "st6": float(ed.findtext("st6")),
            })

        steps.append({
            "step": step_num,
            "node_displacements": node_disps,
            "element_results": elem_results,
        })

    return {"heading": heading, "steps": steps}


def parse_beam_results(xml_path: str | Path) -> dict:
    """Parse a CANDE ``*_BeamResults.xml`` file.

    Returns
    -------
    dict
        Keys: ``heading``, ``beam_groups`` (list of group info dicts),
        ``steps`` (list of dicts, each with ``step`` and ``results`` list).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ctrl = root.find("Control")
    heading_el = ctrl.find("Heading")
    heading = heading_el.text.strip() if heading_el is not None and heading_el.text else ""

    beam_groups = []
    for bg in root.iter("beamGroup"):
        beam_groups.append({
            "pipe_code": int(bg.findtext("pipeCode")),
            "num_elements": int(bg.findtext("numBeamElem")),
            "start_elem": int(bg.findtext("startBeamElem")),
            "end_elem": int(bg.findtext("endBeamElem")),
            "start_node": int(bg.findtext("startNode")),
            "end_node": int(bg.findtext("endNode")),
        })

    steps = []
    for br in root.iter("beamResults"):
        step_num = int(br.findtext("constIncrement"))
        results = []
        for rd in br.iter("resultsData"):
            r = {
                "result_id": int(rd.findtext("resultId")),
                "node": int(rd.findtext("nodeNumber")),
                "element": int(rd.findtext("elementNumber")),
                "group": int(rd.findtext("beamGroupNumber")),
                "pipe_type": int(rd.findtext("pipeType")),
                "x": float(rd.findtext("xCoord")),
                "y": float(rd.findtext("yCoord")),
                "dx": float(rd.findtext("xDisp")),
                "dy": float(rd.findtext("yDisp")),
                "moment": float(rd.findtext("bendingMoment")),
                "thrust": float(rd.findtext("thrustForce")),
                "shear": float(rd.findtext("shearForce")),
                "normal_pressure": float(rd.findtext("normalPressure")),
                "tang_pressure": float(rd.findtext("tangPressure")),
            }
            # Result10-18 (pipe-type dependent)
            for k in range(10, 19):
                tag = f"result{k}"
                el = rd.find(tag)
                r[tag] = float(el.text) if el is not None else 0.0
            r["moment_incr"] = float(rd.findtext("momentIncrement"))
            r["thrust_incr"] = float(rd.findtext("thrustIncrement"))
            results.append(r)
        steps.append({"step": step_num, "results": results})

    return {"heading": heading, "beam_groups": beam_groups, "steps": steps}


# ---------------------------------------------------------------------------
# Plotly visualization functions
# ---------------------------------------------------------------------------

def _require_plotly():
    try:
        import plotly.graph_objects as go
        import plotly.subplots as sp
        return go, sp
    except ImportError:
        raise ImportError(
            "plotly is required for visualization. "
            "Install with: pip install cande-wrapper[viz]"
        )


def plot_mesh(
    geom: dict,
    results: Optional[dict] = None,
    step: int = -1,
    deformed: bool = False,
    scale: float = 1.0,
    show_nodes: bool = True,
    show_boundaries: bool = True,
) -> "plotly.graph_objects.Figure":
    """Plot the FEA mesh from parsed MeshGeom data.

    Parameters
    ----------
    geom : dict
        Output from :func:`parse_mesh_geom`.
    results : dict, optional
        Output from :func:`parse_mesh_results`. Required if ``deformed=True``.
    step : int
        Load step index (default -1 = last step).
    deformed : bool
        If True, show deformed shape using displacements from ``results``.
    scale : float
        Displacement magnification factor for deformed shape.
    show_nodes : bool
        Show node markers.
    show_boundaries : bool
        Show boundary condition markers.
    """
    go, _ = _require_plotly()

    node_map = {n["id"]: n for n in geom["nodes"]}

    # Apply displacements if deformed
    if deformed and results:
        step_data = results["steps"][step]
        disp_map = {d["id"]: d for d in step_data["node_displacements"]}
        for nid, n in node_map.items():
            if nid in disp_map:
                n = dict(n)
                n["x"] += disp_map[nid]["dx"] * scale
                n["y"] += disp_map[nid]["dy"] * scale
                node_map[nid] = n

    fig = go.Figure()

    # Element type colors
    type_colors = {
        "BEAM": "red",
        "QUAD": "steelblue",
        "TRIA": "seagreen",
        "INTF": "gray",
    }

    # Draw elements
    for elem in geom["elements"]:
        etype = elem["type"]
        color = type_colors.get(etype, "black")
        n_ids = [elem["n1"], elem["n2"]]

        if etype == "BEAM":
            n_ids = [elem["n1"], elem["n2"]]
        elif etype in ("QUAD", "TRIA"):
            n_ids = [elem["n1"], elem["n2"], elem["n3"]]
            if etype == "QUAD" and elem["n4"] != elem["n3"]:
                n_ids.append(elem["n4"])
            n_ids.append(n_ids[0])  # close polygon

        xs = [node_map[nid]["x"] for nid in n_ids]
        ys = [node_map[nid]["y"] for nid in n_ids]

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line=dict(color=color, width=2 if etype == "BEAM" else 1),
            hovertext=f"Elem {elem['id']} ({etype}) Mat={elem['mat']}",
            hoverinfo="text",
            showlegend=False,
        ))

    # Add legend entries for element types present
    types_present = {e["type"] for e in geom["elements"]}
    for etype in sorted(types_present):
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            line=dict(color=type_colors.get(etype, "black"), width=2),
            name=etype,
        ))

    # Draw nodes
    if show_nodes:
        nx = [n["x"] for n in node_map.values()]
        ny = [n["y"] for n in node_map.values()]
        labels = [f"Node {n['id']}" for n in node_map.values()]
        fig.add_trace(go.Scatter(
            x=nx, y=ny, mode="markers",
            marker=dict(size=4, color="black"),
            text=labels, hoverinfo="text",
            name="Nodes",
        ))

    # Draw boundary conditions
    if show_boundaries and geom["boundaries"]:
        bx, by, bt = [], [], []
        for bc in geom["boundaries"]:
            n = node_map.get(bc["node"])
            if n:
                bx.append(n["x"])
                by.append(n["y"])
                dirs = []
                if bc["x_code"] == 1:
                    dirs.append("X-fixed")
                if bc["y_code"] == 1:
                    dirs.append("Y-fixed")
                bt.append(f"BC Node {bc['node']}: {', '.join(dirs) if dirs else 'Load'}")
        fig.add_trace(go.Scatter(
            x=bx, y=by, mode="markers",
            marker=dict(size=8, color="orange", symbol="triangle-up"),
            text=bt, hoverinfo="text",
            name="Boundaries",
        ))

    title = geom.get("heading", "CANDE Mesh")
    if deformed:
        title += f" (deformed x{scale})"
    fig.update_layout(
        title=title,
        xaxis=dict(title="X (in)", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y (in)"),
        template="plotly_white",
        hovermode="closest",
    )
    return fig


def plot_beam_results(
    beam_data: dict,
    step: int = -1,
    quantity: str = "thrust",
) -> "plotly.graph_objects.Figure":
    """Plot a single beam quantity around the pipe circumference.

    Parameters
    ----------
    beam_data : dict
        Output from :func:`parse_beam_results`.
    step : int
        Load step index (default -1 = last).
    quantity : str
        One of: ``moment``, ``thrust``, ``shear``, ``normal_pressure``,
        ``tang_pressure``, ``result10``-``result18``.
    """
    go, _ = _require_plotly()

    step_data = beam_data["steps"][step]
    results = step_data["results"]

    node_ids = [r["node"] for r in results]
    values = [r[quantity] for r in results]

    labels = {
        "moment": "Bending Moment (lb-in/in)",
        "thrust": "Thrust Force (lb/in)",
        "shear": "Shear Force (lb/in)",
        "normal_pressure": "Normal Pressure (psi)",
        "tang_pressure": "Tangential Pressure (psi)",
        "result10": "Max Fiber Stress (psi)",
        "result11": "Thrust Stress (psi)",
        "result12": "Shear Stress (psi)",
        "result13": "Fraction Yielded",
    }
    ylabel = labels.get(quantity, quantity)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(values))), y=values,
        mode="lines+markers",
        marker=dict(size=4),
        text=[f"Node {nid}: {v:.2f}" for nid, v in zip(node_ids, values)],
        hoverinfo="text",
        name=quantity,
    ))

    fig.update_layout(
        title=f"{ylabel} — Step {step_data['step']}",
        xaxis_title="Node Position (around pipe)",
        yaxis_title=ylabel,
        template="plotly_white",
    )
    return fig


def plot_beam_forces(
    beam_data: dict,
    step: int = -1,
) -> "plotly.graph_objects.Figure":
    """Plot moment, thrust, and shear on stacked subplots.

    Parameters
    ----------
    beam_data : dict
        Output from :func:`parse_beam_results`.
    step : int
        Load step index (default -1 = last).
    """
    go, sp = _require_plotly()

    step_data = beam_data["steps"][step]
    results = step_data["results"]
    x = list(range(len(results)))
    node_ids = [r["node"] for r in results]

    fig = sp.make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=("Bending Moment", "Thrust Force", "Shear Force"),
        vertical_spacing=0.08,
    )

    for row, (key, color) in enumerate([
        ("moment", "royalblue"),
        ("thrust", "firebrick"),
        ("shear", "forestgreen"),
    ], start=1):
        values = [r[key] for r in results]
        fig.add_trace(go.Scatter(
            x=x, y=values, mode="lines+markers",
            marker=dict(size=3, color=color),
            line=dict(color=color),
            text=[f"Node {nid}: {v:.2f}" for nid, v in zip(node_ids, values)],
            hoverinfo="text",
            showlegend=False,
        ), row=row, col=1)

    units = ["(lb-in/in)", "(lb/in)", "(lb/in)"]
    for i, u in enumerate(units, 1):
        fig.update_yaxes(title_text=u, row=i, col=1)
    fig.update_xaxes(title_text="Node Position (around pipe)", row=3, col=1)

    fig.update_layout(
        title=f"Beam Forces — Step {step_data['step']}",
        height=700,
        template="plotly_white",
    )
    return fig


def plot_displacement(
    geom: dict,
    results: dict,
    step: int = -1,
) -> "plotly.graph_objects.Figure":
    """Plot displacement magnitude as colored markers on the mesh.

    Parameters
    ----------
    geom : dict
        Output from :func:`parse_mesh_geom`.
    results : dict
        Output from :func:`parse_mesh_results`.
    step : int
        Load step index (default -1 = last).
    """
    go, _ = _require_plotly()

    step_data = results["steps"][step]
    node_map = {n["id"]: n for n in geom["nodes"]}

    xs, ys, mags, texts = [], [], [], []
    for d in step_data["node_displacements"]:
        n = node_map.get(d["id"])
        if n:
            mag = (d["dx"] ** 2 + d["dy"] ** 2) ** 0.5
            xs.append(n["x"])
            ys.append(n["y"])
            mags.append(mag)
            texts.append(
                f"Node {d['id']}<br>"
                f"dx={d['dx']:.6f}<br>"
                f"dy={d['dy']:.6f}<br>"
                f"|d|={mag:.6f}"
            )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(
            size=10,
            color=mags,
            colorscale="Viridis",
            colorbar=dict(title="Displacement (in)"),
        ),
        text=texts, hoverinfo="text",
    ))

    fig.update_layout(
        title=f"Displacement Magnitude — Step {step_data['step']}",
        xaxis=dict(title="X (in)", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y (in)"),
        template="plotly_white",
    )
    return fig


def plot_soil_stress(
    geom: dict,
    results: dict,
    step: int = -1,
    component: str = "vertical",
) -> "plotly.graph_objects.Figure":
    """Plot soil stress contours from QUAD/TRIA elements.

    Parameters
    ----------
    geom : dict
        Output from :func:`parse_mesh_geom`.
    results : dict
        Output from :func:`parse_mesh_results`.
    step : int
        Load step index (default -1 = last).
    component : str
        One of: ``vertical`` (st4), ``horizontal`` (st5), ``shear`` (st6),
        ``vertical_strain`` (st1), ``horizontal_strain`` (st2), ``shear_strain`` (st3).
    """
    go, _ = _require_plotly()

    comp_map = {
        "vertical": ("st4", "Vertical Stress (psi)"),
        "horizontal": ("st5", "Horizontal Stress (psi)"),
        "shear": ("st6", "Shear Stress (psi)"),
        "vertical_strain": ("st1", "Vertical Strain"),
        "horizontal_strain": ("st2", "Horizontal Strain"),
        "shear_strain": ("st3", "Shear Strain"),
    }
    st_key, label = comp_map.get(component, ("st4", component))

    step_data = results["steps"][step]
    node_map = {n["id"]: n for n in geom["nodes"]}

    # Filter to soil elements (QUAD and TRIA)
    soil_elems = [e for e in geom["elements"] if e["type"] in ("QUAD", "TRIA")]
    result_map = {r["id"]: r for r in step_data["element_results"]
                  if r["type"] in ("QUAD", "TRIA")}

    # Compute element centroids and stress values
    cx, cy, vals, texts = [], [], [], []
    for elem in soil_elems:
        r = result_map.get(elem["id"])
        if not r:
            continue
        n_ids = [elem["n1"], elem["n2"], elem["n3"]]
        if elem["type"] == "QUAD" and elem["n4"] != elem["n3"]:
            n_ids.append(elem["n4"])
        coords = [node_map[nid] for nid in n_ids if nid in node_map]
        if not coords:
            continue
        centroid_x = sum(c["x"] for c in coords) / len(coords)
        centroid_y = sum(c["y"] for c in coords) / len(coords)
        val = r[st_key]
        cx.append(centroid_x)
        cy.append(centroid_y)
        vals.append(val)
        texts.append(f"Elem {elem['id']}<br>{label}: {val:.4f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cx, y=cy, mode="markers",
        marker=dict(
            size=12,
            color=vals,
            colorscale="RdBu_r",
            colorbar=dict(title=label),
            symbol="square",
        ),
        text=texts, hoverinfo="text",
    ))

    fig.update_layout(
        title=f"{label} — Step {step_data['step']}",
        xaxis=dict(title="X (in)", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y (in)"),
        template="plotly_white",
    )
    return fig


def plot_load_history(
    beam_data: dict,
    node: Optional[int] = None,
    quantity: str = "thrust",
) -> "plotly.graph_objects.Figure":
    """Plot a beam quantity vs. load step.

    Parameters
    ----------
    beam_data : dict
        Output from :func:`parse_beam_results`.
    node : int, optional
        Specific node number to plot. If None, plots the envelope
        (max absolute value across all nodes per step).
    quantity : str
        One of: ``moment``, ``thrust``, ``shear``, ``normal_pressure``.
    """
    go, _ = _require_plotly()

    labels = {
        "moment": "Bending Moment (lb-in/in)",
        "thrust": "Thrust Force (lb/in)",
        "shear": "Shear Force (lb/in)",
        "normal_pressure": "Normal Pressure (psi)",
    }
    ylabel = labels.get(quantity, quantity)

    fig = go.Figure()

    if node is not None:
        steps_x, values_y = [], []
        for step_data in beam_data["steps"]:
            for r in step_data["results"]:
                if r["node"] == node:
                    steps_x.append(step_data["step"])
                    values_y.append(r[quantity])
                    break
        fig.add_trace(go.Scatter(
            x=steps_x, y=values_y,
            mode="lines+markers",
            name=f"Node {node}",
        ))
    else:
        # Plot envelope (max and min across all nodes)
        steps_x = []
        max_vals, min_vals = [], []
        for step_data in beam_data["steps"]:
            vals = [r[quantity] for r in step_data["results"]]
            if vals:
                steps_x.append(step_data["step"])
                max_vals.append(max(vals))
                min_vals.append(min(vals))

        fig.add_trace(go.Scatter(
            x=steps_x, y=max_vals,
            mode="lines+markers", name="Max",
            line=dict(color="firebrick"),
        ))
        fig.add_trace(go.Scatter(
            x=steps_x, y=min_vals,
            mode="lines+markers", name="Min",
            line=dict(color="steelblue"),
        ))

    fig.update_layout(
        title=f"{ylabel} vs. Load Step"
              + (f" — Node {node}" if node else " — Envelope"),
        xaxis_title="Load Step",
        yaxis_title=ylabel,
        template="plotly_white",
    )
    return fig


def plot_deformed_mesh(
    geom: dict,
    results: dict,
    step: int = -1,
    scale: float = 10.0,
) -> "plotly.graph_objects.Figure":
    """Plot original and deformed mesh overlaid.

    Parameters
    ----------
    geom : dict
        Output from :func:`parse_mesh_geom`.
    results : dict
        Output from :func:`parse_mesh_results`.
    step : int
        Load step index (default -1 = last).
    scale : float
        Displacement magnification factor.
    """
    go, _ = _require_plotly()

    step_data = results["steps"][step]
    node_map = {n["id"]: n for n in geom["nodes"]}
    disp_map = {d["id"]: d for d in step_data["node_displacements"]}

    fig = go.Figure()

    type_colors = {"BEAM": "red", "QUAD": "steelblue", "TRIA": "seagreen", "INTF": "gray"}
    type_colors_def = {"BEAM": "darkred", "QUAD": "navy", "TRIA": "darkgreen", "INTF": "dimgray"}

    for pass_name, use_deformed, opacity, dash in [
        ("Original", False, 0.3, "dot"),
        ("Deformed", True, 1.0, "solid"),
    ]:
        for elem in geom["elements"]:
            etype = elem["type"]
            if use_deformed:
                color = type_colors_def.get(etype, "black")
            else:
                color = type_colors.get(etype, "black")

            n_ids = [elem["n1"], elem["n2"]]
            if etype in ("QUAD", "TRIA"):
                n_ids = [elem["n1"], elem["n2"], elem["n3"]]
                if etype == "QUAD" and elem["n4"] != elem["n3"]:
                    n_ids.append(elem["n4"])
                n_ids.append(n_ids[0])

            xs, ys = [], []
            for nid in n_ids:
                n = node_map.get(nid, {"x": 0, "y": 0})
                x, y = n["x"], n["y"]
                if use_deformed and nid in disp_map:
                    x += disp_map[nid]["dx"] * scale
                    y += disp_map[nid]["dy"] * scale
                xs.append(x)
                ys.append(y)

            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                line=dict(color=color, width=2 if etype == "BEAM" else 1,
                          dash=dash),
                opacity=opacity,
                showlegend=False,
                hoverinfo="skip" if not use_deformed else "text",
                hovertext=f"Elem {elem['id']} ({etype})" if use_deformed else None,
            ))

    # Legend entries
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color="gray", dash="dot"), name="Original",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color="black"), name=f"Deformed (x{scale})",
    ))

    fig.update_layout(
        title=f"Deformed Shape — Step {step_data['step']} (scale x{scale})",
        xaxis=dict(title="X (in)", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y (in)"),
        template="plotly_white",
        hovermode="closest",
    )
    return fig
