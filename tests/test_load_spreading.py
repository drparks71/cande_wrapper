"""Tests for load spreading algorithms."""

import math

import pytest

from cande_wrapper.toolbox.load_spreading import (
    aam_theta_star,
    compute_3dse_width,
    compute_cls_thickness_factor,
    compute_fox_beta_w,
    compute_impact_factor,
    compute_rsl_factor,
    two_wheel_interaction_depth,
)


class TestAAMThetaStar:
    def test_zero_depth_returns_footprint(self):
        spread = aam_theta_star(0.0, 10.0, 20.0)
        assert spread == 10.0

    def test_spread_increases_with_depth(self):
        s1 = aam_theta_star(12.0, 10.0, 20.0)
        s2 = aam_theta_star(36.0, 10.0, 20.0)
        s3 = aam_theta_star(72.0, 10.0, 20.0)
        assert s1 < s2 < s3

    def test_spread_always_ge_footprint(self):
        for depth in [0, 1, 10, 100]:
            assert aam_theta_star(float(depth), 10.0, 20.0) >= 10.0


class TestTwoWheelInteraction:
    def test_returns_positive_depth(self):
        h = two_wheel_interaction_depth(10.0, 72.0)
        assert h > 0

    def test_wider_spacing_deeper_interaction(self):
        h1 = two_wheel_interaction_depth(10.0, 48.0)
        h2 = two_wheel_interaction_depth(10.0, 72.0)
        assert h2 > h1


class TestRSLFactor:
    def test_returns_fraction(self):
        rf = compute_rsl_factor(
            cover_depth=36.0, span=120.0,
            footprint_length=10.0, footprint_width=20.0,
        )
        assert 0 < rf <= 1.0

    def test_deeper_cover_lower_factor(self):
        rf1 = compute_rsl_factor(
            cover_depth=12.0, span=120.0,
            footprint_length=10.0, footprint_width=20.0,
        )
        rf2 = compute_rsl_factor(
            cover_depth=72.0, span=120.0,
            footprint_length=10.0, footprint_width=20.0,
        )
        assert rf2 < rf1


class TestCLSThicknessFactor:
    def test_surface_returns_one(self):
        f = compute_cls_thickness_factor(0.0, 10.0, 20.0)
        assert f == 1.0

    def test_increases_with_depth(self):
        f1 = compute_cls_thickness_factor(12.0, 10.0, 20.0)
        f2 = compute_cls_thickness_factor(36.0, 10.0, 20.0)
        assert f2 > f1

    def test_always_ge_one(self):
        for d in [0, 1, 10, 100]:
            assert compute_cls_thickness_factor(float(d), 10.0, 20.0) >= 1.0


class TestFoxBetaW:
    def test_no_pavement_returns_one(self):
        assert compute_fox_beta_w(0.0, 100.0, 10.0) == 1.0

    def test_pavement_amplifies(self):
        beta = compute_fox_beta_w(8.0, 100.0, 10.0)
        assert beta > 1.0

    def test_stiffer_pavement_more_amplification(self):
        b1 = compute_fox_beta_w(8.0, 100.0, 10.0)
        b2 = compute_fox_beta_w(8.0, 1000.0, 10.0)
        assert b2 > b1


class TestCompute3DSEWidth:
    def test_aashto_default(self):
        w = compute_3dse_width(span=120.0, culvert_length=240.0)
        # Wmin = 0.5 * (96 + 0.12 * 120) = 0.5 * 110.4 = 55.2
        assert abs(w - 55.2) < 0.1

    def test_capped_by_culvert_length(self):
        w = compute_3dse_width(span=120.0, culvert_length=30.0)
        assert w <= 30.0

    def test_custom_values(self):
        w = compute_3dse_width(span=120.0, culvert_length=240.0, w_min=60.0, w_critical=70.0)
        assert w == 70.0


class TestImpactFactor:
    def test_zero_cover(self):
        im = compute_impact_factor(0.0)
        assert abs(im - 0.33) < 0.001

    def test_8_ft_cover_zero(self):
        im = compute_impact_factor(8.0)
        assert im == 0.0

    def test_3_ft_cover(self):
        im = compute_impact_factor(3.0)
        expected = 0.33 * (1 - 3.0 / 8.0)
        assert abs(im - expected) < 0.001

    def test_clamped_positive(self):
        im = compute_impact_factor(20.0)
        assert im == 0.0
