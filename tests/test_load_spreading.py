"""Tests for load spreading algorithms (source-aligned).

Tests verify the algorithms match the Fortran source code in CTB-2025.
"""

import math

import pytest

from cande_wrapper.toolbox.load_spreading import (
    aam_theta_spread,
    compute_3dse_params,
    compute_cls_thickness_factor,
    compute_impact_factor,
    compute_rsl_constant,
    compute_rsl_variable,
    fox_pave_3d,
    two_wheel_interaction_depth,
)


class TestFoxPave3D:
    """Tests for Fox pavement-soil elasticity solution (FoxPave3D.for)."""

    def test_no_pavement_returns_ones(self):
        bl, bw = fox_pave_3d(0.0, 100.0, 10.0, 20.0)
        assert bl == 1.0
        assert bw == 1.0

    def test_eratio_one_returns_ones(self):
        bl, bw = fox_pave_3d(8.0, 1.0, 10.0, 20.0)
        assert bl == 1.0
        assert bw == 1.0

    def test_returns_two_values(self):
        result = fox_pave_3d(8.0, 100.0, 10.0, 20.0)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_beta_l_ge_one(self):
        bl, bw = fox_pave_3d(8.0, 100.0, 10.0, 20.0)
        assert bl >= 1.0

    def test_beta_w_ge_one(self):
        bl, bw = fox_pave_3d(8.0, 100.0, 10.0, 20.0)
        assert bw >= 1.0

    def test_stiffer_pavement_more_amplification(self):
        bl1, bw1 = fox_pave_3d(8.0, 100.0, 10.0, 20.0)
        bl2, bw2 = fox_pave_3d(8.0, 1000.0, 10.0, 20.0)
        assert bw2 > bw1
        assert bl2 > bl1

    def test_thicker_pavement_more_amplification(self):
        bl1, bw1 = fox_pave_3d(4.0, 100.0, 10.0, 20.0)
        bl2, bw2 = fox_pave_3d(12.0, 100.0, 10.0, 20.0)
        assert bw2 > bw1

    def test_known_matrix_corner_eratio_1(self):
        """When Eratio=1, reduction factor should be ~1.0 (no effect)."""
        bl, bw = fox_pave_3d(8.0, 1.0, 10.0, 20.0)
        assert bl == 1.0
        assert bw == 1.0

    def test_square_footprint_equal_betas(self):
        """Square footprint (L=W) should give BetaL == BetaW."""
        bl, bw = fox_pave_3d(8.0, 100.0, 15.0, 15.0)
        assert abs(bl - bw) < 0.001


class TestAAMThetaSpread:
    """Tests for AAM-θ* load spreading (AA-LiveLoads.for)."""

    def test_zero_depth_returns_zero(self):
        spread = aam_theta_spread(0.0, 1.0, 10.0, 1.0, 20.0)
        assert spread == 0.0

    def test_spread_increases_with_depth(self):
        s1 = aam_theta_spread(12.0, 1.0, 10.0, 1.0, 20.0)
        s2 = aam_theta_spread(36.0, 1.0, 10.0, 1.0, 20.0)
        s3 = aam_theta_spread(72.0, 1.0, 10.0, 1.0, 20.0)
        assert s1 < s2 < s3

    def test_spread_always_positive(self):
        for depth in [1, 10, 100]:
            assert aam_theta_spread(float(depth), 1.0, 10.0, 1.0, 20.0) > 0

    def test_hYstar_formula(self):
        """Verify the characteristic depth formula."""
        beta_l, beta_w = 1.0, 1.0
        wl, ww = 10.0, 20.0
        expected_hystar = 22.0 * math.sqrt(beta_l * wl * beta_w * ww / 200.0)
        # At depth = hYstar, theta = 30 degrees
        spread = aam_theta_spread(expected_hystar, beta_l, wl, beta_w, ww)
        # At hYstar, theta = 30 deg, spread = hYstar * 2 * tan(30°)
        expected_spread = expected_hystar * 2 * math.tan(30.0 * math.pi / 180)
        assert abs(spread - expected_spread) < 0.01

    def test_theta_capped_at_30(self):
        """At very large depth, theta should be capped at 30 degrees."""
        spread_deep = aam_theta_spread(1000.0, 1.0, 10.0, 1.0, 20.0)
        # At theta=30, spread = depth * 2 * tan(30)
        max_spread = 1000.0 * 2 * math.tan(30.0 * math.pi / 180)
        assert abs(spread_deep - max_spread) < 1.0


class TestTwoWheelInteraction:
    """Tests for two-wheel interaction depth."""

    def test_returns_positive_depth(self):
        h = two_wheel_interaction_depth(1.0, 10.0, 1.0, 20.0, 72.0)
        assert h > 0

    def test_wider_spacing_deeper_interaction(self):
        h1 = two_wheel_interaction_depth(1.0, 10.0, 1.0, 20.0, 48.0)
        h2 = two_wheel_interaction_depth(1.0, 10.0, 1.0, 20.0, 72.0)
        assert h2 > h1

    def test_fox_amplification_reduces_depth(self):
        """Wider effective footprint means interaction occurs sooner."""
        h1 = two_wheel_interaction_depth(1.0, 10.0, 1.0, 20.0, 72.0)
        h2 = two_wheel_interaction_depth(1.0, 10.0, 2.0, 20.0, 72.0)
        assert h2 < h1  # larger BetaW means target is smaller


class TestRSLConstant:
    """Tests for RSL constant reduction factor."""

    def test_returns_fraction(self):
        rf = compute_rsl_constant(
            cover=36.0, span=120.0,
            beta_l=1.0, wheel_l=10.0, beta_w=1.0, wheel_w=20.0,
            cdbw=72.0,
        )
        assert 0 < rf <= 1.0

    def test_deeper_cover_lower_factor(self):
        rf1 = compute_rsl_constant(
            cover=12.0, span=120.0,
            beta_l=1.0, wheel_l=10.0, beta_w=1.0, wheel_w=20.0,
            cdbw=72.0,
        )
        rf2 = compute_rsl_constant(
            cover=72.0, span=120.0,
            beta_l=1.0, wheel_l=10.0, beta_w=1.0, wheel_w=20.0,
            cdbw=72.0,
        )
        assert rf2 < rf1

    def test_span_term_increases_depth(self):
        rf_with = compute_rsl_constant(
            cover=36.0, span=120.0,
            beta_l=1.0, wheel_l=10.0, beta_w=1.0, wheel_w=20.0,
            cdbw=72.0, include_span_term=True,
        )
        rf_without = compute_rsl_constant(
            cover=36.0, span=120.0,
            beta_l=1.0, wheel_l=10.0, beta_w=1.0, wheel_w=20.0,
            cdbw=72.0, include_span_term=False,
        )
        # With span term, depth is larger, so reduction factor is lower
        assert rf_with < rf_without


class TestRSLVariable:
    """Tests for RSL variable reduction factor."""

    def test_returns_fraction(self):
        rf = compute_rsl_variable(
            node_depth=36.0, span=120.0,
            beta_l=1.0, wheel_l=10.0, beta_w=1.0, wheel_w=20.0,
            cdbw=72.0,
        )
        assert 0 < rf <= 1.0


class TestCLSThicknessFactor:
    def test_surface_returns_one(self):
        f = compute_cls_thickness_factor(0.0, 1.0, 10.0, 1.0, 20.0)
        assert f == 1.0

    def test_increases_with_depth(self):
        f1 = compute_cls_thickness_factor(12.0, 1.0, 10.0, 1.0, 20.0)
        f2 = compute_cls_thickness_factor(36.0, 1.0, 10.0, 1.0, 20.0)
        assert f2 > f1

    def test_always_ge_one(self):
        for d in [0, 1, 10, 100]:
            assert compute_cls_thickness_factor(float(d), 1.0, 10.0, 1.0, 20.0) >= 1.0


class TestCompute3DSEParams:
    def test_aashto_default(self):
        wmin, wcrit = compute_3dse_params(span=120.0, culvert_length=240.0)
        # Wmin = min(0.5*(96 + 1.44*10), 240) = min(0.5*110.4, 240) = 55.2
        assert abs(wmin - 55.2) < 0.1
        assert abs(wcrit - 55.2) < 0.1

    def test_capped_by_culvert_length(self):
        wmin, wcrit = compute_3dse_params(span=120.0, culvert_length=30.0)
        assert wmin <= 30.0

    def test_zero_length_returns_zeros(self):
        wmin, wcrit = compute_3dse_params(span=120.0, culvert_length=0.0)
        assert wmin == 0.0
        assert wcrit == 0.0

    def test_wcritical_ge_wmin(self):
        wmin, wcrit = compute_3dse_params(span=120.0, culvert_length=240.0,
                                          wmin_user=60.0, wcritical_user=40.0)
        assert wcrit >= wmin


class TestImpactFactor:
    def test_zero_cover(self):
        """At zero cover, IM = 0.33."""
        im = compute_impact_factor(0.0)
        assert abs(im - 0.33) < 0.001

    def test_96_inch_cover_zero(self):
        """At 96 inches (8 feet) cover, IM = 0."""
        im = compute_impact_factor(96.0)
        assert im == 0.0

    def test_36_inch_cover(self):
        """At 36 inches (3 feet), IM = 0.33*(1-3/8)."""
        im = compute_impact_factor(36.0)
        expected = 0.33 * (1 - 3.0 / 8.0)
        assert abs(im - expected) < 0.001

    def test_clamped_positive(self):
        im = compute_impact_factor(240.0)
        assert im == 0.0
