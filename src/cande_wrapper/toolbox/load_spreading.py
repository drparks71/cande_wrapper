"""Load spreading algorithms for Option 3: Fox solution, AAM-theta*, RSL, CLS, 3DSE.

All algorithms match the Fortran source code in CTB-2025-MGK-Source exactly.

References:
    FoxPave3D.for — Fox two-layer pavement elasticity solution
    AA-LiveLoads.for — AAM-theta* load spreading, RSL, CLS, 3DSE
    GenerateLiveBC.for — Live load boundary condition generation
"""

from __future__ import annotations

import math

# Degrees-to-radians conversion factor (matches Fortran DATA convert/0.017453/)
_DEG2RAD = math.pi / 180.0


# ---------------------------------------------------------------------------
# Fox two-layer pavement–soil elasticity solution
# ---------------------------------------------------------------------------

# Fox reduction factor matrix: 5 rows (thickness/radius ratios) × 4 cols (modulus ratios)
# From FoxPave3D.for lines 34–39
_FOX_TROW = [0.2, 0.5, 1.0, 2.0, 5.0]
_FOX_ECOL = [1.0, 10.0, 100.0, 1000.0]
_FOX_RF = [
    # Ecol=1    Ecol=10   Ecol=100  Ecol=1000
    [1.00, 1.00, 0.75, 0.32],  # Trow=0.2
    [0.91, 0.63, 0.24, 0.06],  # Trow=0.5
    [0.65, 0.28, 0.08, 0.02],  # Trow=1.0
    [0.29, 0.09, 0.02, 0.01],  # Trow=2.0
    [0.06, 0.02, 0.01, 0.01],  # Trow=5.0
]


def fox_pave_3d(
    pthick: float,
    eratio: float,
    wheel_l: float,
    wheel_w: float,
) -> tuple[float, float]:
    """Fox pavement–soil elasticity solution for footprint amplification.

    Exact port of Fortran subroutine FoxPave3D.

    Parameters
    ----------
    pthick : float
        Pavement thickness (inches).
    eratio : float
        Young's modulus ratio Epave/Esoil.
    wheel_l : float
        Wheel footprint length L0 in travel direction (inches).
    wheel_w : float
        Wheel footprint width W0 in axle direction (inches).

    Returns
    -------
    (beta_l, beta_w) : tuple[float, float]
        Amplification factors for wheel length and width at the
        pavement–soil interface.
    """
    if pthick <= 0 or eratio <= 1.0:
        return 1.0, 1.0

    # Effective radius and thickness ratio
    radius = math.sqrt(wheel_l * wheel_w / math.pi)
    tratio = max(0.2, min(5.0, pthick / radius))
    eratio = max(1.0, min(1000.0, eratio))

    # Find bracketing rows for tratio
    nr_a = 0
    nr_b = 1
    for n in range(4):
        if _FOX_TROW[n] <= tratio <= _FOX_TROW[n + 1]:
            nr_a = n
            nr_b = n + 1

    # Find bracketing columns for eratio
    nc_a = 0
    nc_b = 1
    for n in range(3):
        if _FOX_ECOL[n] <= eratio <= _FOX_ECOL[n + 1]:
            nc_a = n
            nc_b = n + 1

    # Gather 4 bracketing reduction factors
    rf_aa = _FOX_RF[nr_a][nc_a]
    rf_ab = _FOX_RF[nr_a][nc_b]
    rf_ba = _FOX_RF[nr_b][nc_a]
    rf_bb = _FOX_RF[nr_b][nc_b]

    # Double bilinear interpolation
    dt = (tratio - _FOX_TROW[nr_a]) / (_FOX_TROW[nr_b] - _FOX_TROW[nr_a])
    rf_xa = rf_aa + (rf_ba - rf_aa) * dt
    rf_xb = rf_ab + (rf_bb - rf_ab) * dt
    de = (eratio - _FOX_ECOL[nc_a]) / (_FOX_ECOL[nc_b] - _FOX_ECOL[nc_a])
    rf_xx = rf_xa + (rf_xb - rf_xa) * de

    # Compute BetaL
    alpha = wheel_w / wheel_l
    disc = (1 + alpha) ** 2 + 4 * alpha * (1.0 / rf_xx - 1.0)
    beta_l = max(1.0, 0.5 * (1 - alpha + math.sqrt(disc)))

    # Compute BetaW
    alpha = wheel_l / wheel_w
    disc = (1 + alpha) ** 2 + 4 * alpha * (1.0 / rf_xx - 1.0)
    beta_w = max(1.0, 0.5 * (1 - alpha + math.sqrt(disc)))

    return beta_l, beta_w


# ---------------------------------------------------------------------------
# AAM-θ* load spreading (matches Fortran exactly)
# ---------------------------------------------------------------------------

def aam_theta_spread(
    depth: float,
    beta_l: float,
    wheel_l: float,
    beta_w: float,
    wheel_w: float,
) -> float:
    """Compute the AAM-θ* full spreading distance at a given depth.

    Matches the Fortran formulas from AA-LiveLoads.for:
        hYstar = 22.0 * sqrt(BetaL*WheelL*BetaW*WheelW / 200)
        Theta = min((YD / hYstar) * 30.0, 30.0)
        Spread = YD * 2 * tan(Theta * convert)

    Parameters
    ----------
    depth : float
        Vertical depth below surface (inches). Must be > 0.
    beta_l, beta_w : float
        Fox pavement amplification factors (1.0 if no pavement).
    wheel_l, wheel_w : float
        Wheel footprint dimensions (inches).

    Returns
    -------
    Full spreading distance (inches). This is the spread from BOTH sides
    of the load, NOT the total footprint width.
    """
    if depth <= 0:
        return 0.0

    h_ystar = 22.0 * math.sqrt(beta_l * wheel_l * beta_w * wheel_w / 200.0)
    if h_ystar <= 0:
        return 0.0

    theta = min((depth / h_ystar) * 30.0, 30.0)  # degrees
    spread = depth * 2.0 * math.tan(theta * _DEG2RAD)
    return spread


def two_wheel_interaction_depth(
    beta_l: float,
    wheel_l: float,
    beta_w: float,
    wheel_w: float,
    cdbw: float,
) -> float:
    """Find depth where two-wheel loads begin to interact.

    Searches for YD such that Spread >= CDBW - BetaW*WheelW.
    Matches Fortran AA-LiveLoads.for lines 356–367.

    Parameters
    ----------
    beta_l, beta_w : float
        Fox pavement amplification factors.
    wheel_l, wheel_w : float
        Wheel footprint dimensions (inches).
    cdbw : float
        Centerline distance between wheels (inches).

    Returns
    -------
    Interaction depth in inches (up to 1000).
    """
    target = cdbw - beta_w * wheel_w
    if target <= 0:
        return 0.0

    for yd in range(1, 1001):
        spread = aam_theta_spread(float(yd), beta_l, wheel_l, beta_w, wheel_w)
        if spread >= target:
            return float(yd)
    return 1000.0


def _find_transition_depth(
    beta_l: float,
    wheel_l: float,
    beta_w: float,
    wheel_w: float,
    wcritical: float,
) -> float:
    """Find the 3DSE transition depth.

    Searches for YD such that Spread >= Wcritical - BetaW*WheelW.
    Matches Fortran AA-LiveLoads.for lines 392–403.
    """
    target = wcritical - beta_w * wheel_w
    if target <= 0:
        return 1.0

    for yd in range(1, 1001):
        spread = aam_theta_spread(float(yd), beta_l, wheel_l, beta_w, wheel_w)
        if spread >= target:
            return float(yd)
    return 1000.0


# ---------------------------------------------------------------------------
# RSL — Reduced Surface Load
# ---------------------------------------------------------------------------

def compute_rsl_constant(
    cover: float,
    span: float,
    beta_l: float,
    wheel_l: float,
    beta_w: float,
    wheel_w: float,
    cdbw: float,
    include_span_term: bool = True,
    wmin: float = 0.0,
    wcritical: float = 0.0,
    htransition: float = 1.0,
) -> float:
    """Compute the RSL constant reduction factor.

    Matches Fortran AA-LiveLoads.for lines 418–443 exactly.

    Parameters
    ----------
    cover : float
        Height of soil cover over structure crown (inches).
    span : float
        Horizontal span of structure (inches).
    beta_l, beta_w : float
        Fox pavement amplification factors.
    wheel_l, wheel_w : float
        Wheel footprint dimensions (inches).
    cdbw : float
        Centerline distance between wheels (inches).
    include_span_term : bool
        If True, use current AASHTO (SpanTerm = 0.0522*SPAN).
        If False, use legacy (SpanTerm = 0).
    wmin, wcritical : float
        3DSE distribution widths (inches). 0 = no 3DSE.
    htransition : float
        3DSE transition depth (inches).

    Returns
    -------
    Reduction factor (0 to 1).
    """
    span_term = 0.0522 * span if include_span_term else 0.0
    ydepth = cover + span_term

    # AAM-θ* spread width
    h_ystar = 22.0 * math.sqrt(beta_l * wheel_l * beta_w * wheel_w / 200.0)
    if h_ystar <= 0:
        return 1.0
    theta = min((ydepth / h_ystar) * 30.0, 30.0)
    wtheta = beta_w * wheel_w + ydepth * 2.0 * math.tan(theta * _DEG2RAD)

    # 3DSE width
    w3dse = wmin + (ydepth / htransition) * (wcritical - wmin) if htransition > 0 else 0.0

    # Two-wheel interaction depth
    hinteract = two_wheel_interaction_depth(beta_l, wheel_l, beta_w, wheel_w, cdbw)

    # Determine controlling reduction factor
    if w3dse > wtheta:
        # 3DSE controls
        reduction = wheel_w / w3dse if w3dse > 0 else 1.0
    elif ydepth > hinteract:
        # Two-wheel interaction controls
        reduction = 2.0 * wheel_w / (wtheta + cdbw) if (wtheta + cdbw) > 0 else 1.0
    else:
        # Single-wheel AAM-θ* controls
        reduction = wheel_w / wtheta if wtheta > 0 else 1.0

    return min(1.0, reduction)


def compute_rsl_variable(
    node_depth: float,
    span: float,
    beta_l: float,
    wheel_l: float,
    beta_w: float,
    wheel_w: float,
    cdbw: float,
    include_span_term: bool = True,
    wmin: float = 0.0,
    wcritical: float = 0.0,
    htransition: float = 1.0,
) -> float:
    """Compute the RSL variable reduction factor for a single node.

    Matches Fortran AA-LiveLoads.for lines 449–468. Same algorithm as
    constant RSL but uses the node's actual depth instead of cover.

    Parameters
    ----------
    node_depth : float
        Variable cover height below this surface node (inches).
    (other params same as compute_rsl_constant)

    Returns
    -------
    Reduction factor (0 to 1).
    """
    span_term = 0.0522 * span if include_span_term else 0.0
    ydepth = node_depth + span_term

    h_ystar = 22.0 * math.sqrt(beta_l * wheel_l * beta_w * wheel_w / 200.0)
    if h_ystar <= 0:
        return 1.0
    theta = min((ydepth / h_ystar) * 30.0, 30.0)
    wtheta = beta_w * wheel_w + ydepth * 2.0 * math.tan(theta * _DEG2RAD)

    w3dse = wmin + (ydepth / htransition) * (wcritical - wmin) if htransition > 0 else 0.0

    hinteract = two_wheel_interaction_depth(beta_l, wheel_l, beta_w, wheel_w, cdbw)

    if w3dse > wtheta:
        reduction = wheel_w / w3dse if w3dse > 0 else 1.0
    elif ydepth > hinteract:
        reduction = 2.0 * wheel_w / (wtheta + cdbw) if (wtheta + cdbw) > 0 else 1.0
    else:
        reduction = wheel_w / wtheta if wtheta > 0 else 1.0

    return min(1.0, reduction)


# ---------------------------------------------------------------------------
# CLS — Continuous Load Scaling
# ---------------------------------------------------------------------------

def compute_cls_thickness_factor(
    element_depth: float,
    beta_l: float,
    wheel_l: float,
    beta_w: float,
    wheel_w: float,
) -> float:
    """Compute CLS element thickness amplification factor.

    For CLS (Iscale=1), each element's out-of-plane thickness is scaled
    by the ratio of effective spread width to the wheel width at that
    element's depth. Full-service loads are applied without surface
    reduction (REDUCT = 1.0 for CLS).

    Parameters
    ----------
    element_depth : float
        Depth of element centroid below surface (inches).
    beta_l, beta_w : float
        Fox pavement amplification factors.
    wheel_l, wheel_w : float
        Wheel footprint dimensions (inches).

    Returns
    -------
    Thickness amplification factor (>= 1.0).
    """
    spread = aam_theta_spread(element_depth, beta_l, wheel_l, beta_w, wheel_w)
    # Total effective width = BetaW*WheelW + Spread
    effective_w = beta_w * wheel_w + spread
    factor = effective_w / wheel_w if wheel_w > 0 else 1.0
    return max(factor, 1.0)


# ---------------------------------------------------------------------------
# 3D Stiffness Effects (3DSE)
# ---------------------------------------------------------------------------

def compute_3dse_params(
    span: float,
    culvert_length: float,
    wmin_user: float | None = None,
    wcritical_user: float | None = None,
) -> tuple[float, float]:
    """Compute 3DSE distribution width parameters.

    Matches Fortran AA-LiveLoads.for lines 379–413.

    Parameters
    ----------
    span : float
        Culvert span (inches).
    culvert_length : float
        Culvert length (inches).
    wmin_user : float or None
        User-specified Wmin. None = AASHTO default.
    wcritical_user : float or None
        User-specified Wcritical. None = AASHTO default.

    Returns
    -------
    (wmin, wcritical) : tuple[float, float]
    """
    if culvert_length <= 0:
        return 0.0, 0.0

    # AASHTO default: Wmin = min(0.5*(96 + 1.44*S_ft), culvert_length)
    span_ft = span / 12.0
    wmin_default = min(0.5 * (96.0 + 1.44 * span_ft), culvert_length)

    wmin = wmin_user if wmin_user is not None and wmin_user > 0 else wmin_default
    wcritical = wcritical_user if wcritical_user is not None and wcritical_user > 0 else wmin_default

    if wcritical < wmin:
        wcritical = wmin

    return wmin, wcritical


# ---------------------------------------------------------------------------
# Impact factor
# ---------------------------------------------------------------------------

def compute_impact_factor(cover_height_inches: float) -> float:
    """Compute the AASHTO dynamic impact factor.

    Matches Fortran: AashtoIM = 0.33*(1.0 - (HTCOVER/12.0)/8.0)

    Parameters
    ----------
    cover_height_inches : float
        Minimum cover height in inches.

    Returns
    -------
    Impact factor as a fraction (e.g., 0.33 = 33% increase). Clamped to [0, 0.33].
    """
    cover_ft = cover_height_inches / 12.0
    im = 0.33 * (1.0 - cover_ft / 8.0)
    return max(0.0, min(0.33, im))
