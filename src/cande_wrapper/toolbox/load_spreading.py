"""Load spreading algorithms for Option 3: RSL, CLS, Fox solution, AAM-theta*, 3DSE.

References:
    [1] M.G. Katona, "Assessment of AASHTO Load-Spreading Method", TRR 2021.
    [2] M.G. Katona, "Extension of AASHTO Load-Spreading Method", TRR 2022.
    [3] M.G. Katona, CANDE Solution Methods and Formulations Manual, Chap. 8.1, 2022.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# AAM-theta* load spreading model
# ---------------------------------------------------------------------------

def aam_theta_star(depth: float, footprint_length: float, footprint_width: float,
                   wheel_spacing: float = 72.0) -> float:
    """Compute the AAM-theta* longitudinal spread width at a given depth.

    The improved AASHTO Ad Hoc model determines the effective width of
    load at depth by distributing the surface footprint through the soil
    at a variable angle theta*(H).

    Parameters
    ----------
    depth
        Vertical depth below the surface (inches).
    footprint_length
        Longitudinal footprint dimension L0 (inches).
    footprint_width
        Transverse footprint dimension W0 (inches).
    wheel_spacing
        Center-to-center wheel spacing on the axle (inches).

    Returns
    -------
    Effective longitudinal spread width at the given depth (inches).
    """
    if depth <= 0:
        return footprint_length

    # AAM-theta* angle increases with depth
    # theta*(H) varies from ~30 deg at shallow to ~45 deg at deep
    # Using the improved formula from Reference [1]
    # tan(theta*) = 1.15 * (1 - exp(-0.008 * H))  where H is in inches
    tan_theta = 1.15 * (1 - math.exp(-0.008 * depth))
    if tan_theta < math.tan(math.radians(26.57)):
        tan_theta = math.tan(math.radians(26.57))  # minimum ~26.57 deg (tan=0.5)

    spread = footprint_length + 2 * depth * tan_theta
    return spread


def two_wheel_interaction_depth(
    footprint_length: float, wheel_spacing: float
) -> float:
    """Compute the depth at which two wheel loads begin to interact.

    Below this depth, the spread zones from each wheel overlap and the
    loads should be combined.

    Parameters
    ----------
    footprint_length
        Longitudinal footprint dimension L0 (inches).
    wheel_spacing
        Center-to-center wheel spacing on the axle (inches).

    Returns
    -------
    Interaction depth in inches.
    """
    # The interaction depth is where the spread width from one wheel
    # reaches the adjacent wheel: L0 + 2*H*tan(theta) >= spacing
    # Approximate by solving iteratively
    for h in range(1, 2000):
        spread = aam_theta_star(float(h), footprint_length, 0.0, wheel_spacing)
        if spread >= wheel_spacing:
            return float(h)
    return 2000.0  # very deep, practically no interaction


# ---------------------------------------------------------------------------
# RSL — Reduced Surface Load
# ---------------------------------------------------------------------------

def compute_rsl_factor(
    cover_depth: float,
    span: float,
    footprint_length: float,
    footprint_width: float,
    wheel_spacing: float = 72.0,
    include_span_term: bool = True,
    pavement_thickness: float = 0.0,
    epave_esoil: float = 100.0,
    culvert_length: float = 0.0,
    w_min: float | None = None,
    w_critical: float | None = None,
) -> float:
    """Compute the RSL reduction factor for surface loads.

    The reduction factor = (footprint_length) / (effective_spread_width)
    which is < 1, meaning the surface load is reduced to account for
    longitudinal spreading.

    Parameters
    ----------
    cover_depth
        Minimum soil cover over the structure (inches).
    span
        Culvert span (inches).
    footprint_length
        Wheel footprint length L0 (inches).
    footprint_width
        Wheel footprint width W0 (inches).
    wheel_spacing
        Center-to-center wheel spacing (inches).
    include_span_term
        If True, add a portion of the span to the reference depth
        per AASHTO 3.6.1.2.6.
    pavement_thickness
        Pavement thickness for Fox solution (inches). 0 = no pavement.
    epave_esoil
        Ratio of pavement modulus to soil modulus.
    culvert_length
        Culvert length for 3DSE (inches). 0 = no 3DSE.
    w_min
        Minimum 3DSE distribution width (inches). None = AASHTO default.
    w_critical
        Critical 3DSE distribution width (inches). None = AASHTO default.

    Returns
    -------
    Reduction factor (0 to 1).
    """
    # Reference depth for load spreading
    ref_depth = cover_depth
    if include_span_term:
        # AASHTO 3.6.1.2.6: add 0.12 * span term
        ref_depth += 0.12 * span

    # Base spread width from AAM-theta*
    spread_width = aam_theta_star(ref_depth, footprint_length, footprint_width, wheel_spacing)

    # Fox pavement amplification
    if pavement_thickness > 0:
        beta_w = compute_fox_beta_w(pavement_thickness, epave_esoil, footprint_length)
        spread_width = max(spread_width, beta_w * footprint_length)

    # Two-wheel interaction
    h_interact = two_wheel_interaction_depth(footprint_length, wheel_spacing)
    if ref_depth >= h_interact:
        # Both wheels contribute — combined spread
        spread_width = max(spread_width, wheel_spacing + footprint_length)

    # 3DSE effects
    if culvert_length > 0:
        w_3d = compute_3dse_width(span, culvert_length, w_min, w_critical)
        spread_width = max(spread_width, w_3d)

    # Reduction factor
    rf = footprint_length / spread_width if spread_width > footprint_length else 1.0
    return rf


def compute_variable_rsl_factor(
    node_depth: float,
    span: float,
    footprint_length: float,
    footprint_width: float,
    wheel_spacing: float = 72.0,
    include_span_term: bool = True,
    pavement_thickness: float = 0.0,
    epave_esoil: float = 100.0,
) -> float:
    """Compute variable RSL reduction factor based on actual depth at each node."""
    return compute_rsl_factor(
        cover_depth=node_depth,
        span=span,
        footprint_length=footprint_length,
        footprint_width=footprint_width,
        wheel_spacing=wheel_spacing,
        include_span_term=include_span_term,
        pavement_thickness=pavement_thickness,
        epave_esoil=epave_esoil,
    )


# ---------------------------------------------------------------------------
# CLS — Continuous Load Scaling
# ---------------------------------------------------------------------------

def compute_cls_thickness_factor(
    element_depth: float,
    footprint_length: float,
    footprint_width: float,
    wheel_spacing: float = 72.0,
) -> float:
    """Compute the CLS thickness amplification factor for a single element.

    In CLS, each element's out-of-plane thickness is scaled by the ratio
    of the effective spread width to the footprint length at that element's
    depth. This automatically accounts for longitudinal load spreading.

    Parameters
    ----------
    element_depth
        Depth of the element centroid below the surface (inches).
    footprint_length
        Wheel footprint length L0 (inches).
    footprint_width
        Wheel footprint width W0 (inches).
    wheel_spacing
        Axle wheel spacing (inches).

    Returns
    -------
    Thickness amplification factor (>= 1.0).
    """
    spread = aam_theta_star(element_depth, footprint_length, footprint_width, wheel_spacing)
    factor = spread / footprint_length if footprint_length > 0 else 1.0
    return max(factor, 1.0)


# ---------------------------------------------------------------------------
# Fox two-layer elasticity solution
# ---------------------------------------------------------------------------

def compute_fox_beta_w(
    pavement_thickness: float,
    epave_esoil: float,
    footprint_length: float,
) -> float:
    """Compute the Fox amplification factor beta_W for pavement effects.

    The Fox two-layer elasticity solution determines how much wider the
    effective footprint becomes at the pavement-soil interface due to the
    stiff pavement spreading loads.

    Parameters
    ----------
    pavement_thickness
        Pavement thickness (inches).
    epave_esoil
        Ratio of pavement Young's modulus to soil Young's modulus.
    footprint_length
        Wheel footprint length L0 (inches).

    Returns
    -------
    Amplification factor beta_W >= 1.0.
    """
    if pavement_thickness <= 0 or epave_esoil <= 1:
        return 1.0

    # Simplified Fox solution approximation
    # beta_W = 1 + C * (t_pave / L0) * (Ep/Es)^(1/3)
    # where C is a coefficient ~0.6-0.8
    ratio = pavement_thickness / footprint_length if footprint_length > 0 else 0.0
    beta = 1.0 + 0.7 * ratio * epave_esoil ** (1.0 / 3.0)
    return max(beta, 1.0)


# ---------------------------------------------------------------------------
# 3D Stiffness Effects (3DSE)
# ---------------------------------------------------------------------------

def compute_3dse_width(
    span: float,
    culvert_length: float,
    w_min: float | None = None,
    w_critical: float | None = None,
) -> float:
    """Compute the 3D stiffness effect distribution width.

    Per AASHTO LRFD 4.6.2.10, for reinforced concrete boxes and arches.

    Parameters
    ----------
    span
        Culvert span (inches).
    culvert_length
        Culvert length (inches).
    w_min
        Minimum distribution width (inches). None = AASHTO default.
    w_critical
        Critical distribution width (inches). None = AASHTO default.

    Returns
    -------
    Effective 3DSE distribution width (inches).
    """
    if w_min is None:
        # AASHTO: Wmin = 0.5 * (96 + 0.12 * Span), but <= culvert_length
        w_min = 0.5 * (96.0 + 0.12 * span)
        w_min = min(w_min, culvert_length)

    if w_critical is None:
        w_critical = w_min

    return max(w_min, w_critical)


# ---------------------------------------------------------------------------
# Impact factor
# ---------------------------------------------------------------------------

def compute_impact_factor(cover_height_ft: float) -> float:
    """Compute the AASHTO dynamic impact factor.

    IM = 0.33 * (1 - H/8) where H is cover in feet.
    The factor is clamped to [0, 0.33].

    Parameters
    ----------
    cover_height_ft
        Minimum cover height in feet.

    Returns
    -------
    Impact factor as a fraction (e.g. 0.33 = 33% increase).
    """
    im = 0.33 * (1.0 - cover_height_ft / 8.0)
    return max(0.0, min(0.33, im))
