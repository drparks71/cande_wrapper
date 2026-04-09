"""Unit tests for pipe type definitions."""

from __future__ import annotations

import pytest

from cande_wrapper.pipes import (
    CorrugatedSteel,
    SmoothSteelCasing,
    CorrugatedHDPE,
    SmoothHDPE,
    PrecastConcrete,
    DuctileIron,
    CorrugatedAluminum,
    CorrugatedPVC,
)


class TestCorrugatedSteel:
    def test_defaults(self):
        p = CorrugatedSteel()
        assert p.cande_type == "STEEL"
        assert p.youngs_modulus == 29_000_000
        assert p.poisson_ratio == 0.3
        assert p.yield_stress == 33_000

    def test_custom_yield(self):
        p = CorrugatedSteel(yield_stress=50_000)
        assert p.yield_stress == 50_000

    def test_repr(self):
        p = CorrugatedSteel()
        assert "CorrugatedSteel" in repr(p)
        assert "33000" in repr(p)

    def test_structural_plate(self):
        """Structural plate uses higher yield and 6x2 corrugation."""
        p = CorrugatedSteel.structural_plate()
        assert p.yield_stress == 33_000
        assert p.name == "Structural Plate"


class TestSmoothSteelCasing:
    def test_defaults(self):
        p = SmoothSteelCasing(diameter=24.0, wall_thickness=0.25)
        assert p.cande_type == "BASIC"
        assert p.youngs_modulus == 29_000_000
        assert p.diameter == 24.0
        assert p.wall_thickness == 0.25

    def test_section_properties(self):
        p = SmoothSteelCasing(diameter=24.0, wall_thickness=0.25)
        # Area per unit length = thickness
        assert p.area_per_length == pytest.approx(0.25)
        # Moment of inertia per unit length = t^3 / 12
        assert p.inertia_per_length == pytest.approx(0.25**3 / 12)

    def test_repr(self):
        p = SmoothSteelCasing(diameter=24.0, wall_thickness=0.25)
        assert "SmoothSteelCasing" in repr(p)
        assert "24.0" in repr(p)

    def test_api_5l_grade_b(self):
        p = SmoothSteelCasing.api_5l_grade_b(diameter=36.0, wall_thickness=0.375)
        assert p.yield_stress == 35_000
        assert p.diameter == 36.0

    def test_negative_diameter_raises(self):
        with pytest.raises(ValueError, match="diameter"):
            SmoothSteelCasing(diameter=-1.0, wall_thickness=0.25)

    def test_negative_thickness_raises(self):
        with pytest.raises(ValueError, match="wall_thickness"):
            SmoothSteelCasing(diameter=24.0, wall_thickness=-0.1)


class TestCorrugatedHDPE:
    def test_defaults(self):
        p = CorrugatedHDPE()
        assert p.cande_type == "PLASTIC"
        assert p.material == "HDPE"
        assert p.short_term_modulus == 110_000
        assert p.long_term_modulus == 22_000
        assert p.poisson_ratio == 0.33

    def test_wall_type(self):
        p = CorrugatedHDPE()
        assert p.wall_type == "GENERAL"

    def test_repr(self):
        p = CorrugatedHDPE()
        assert "CorrugatedHDPE" in repr(p)


class TestSmoothHDPE:
    def test_defaults(self):
        p = SmoothHDPE(diameter=12.0, wall_thickness=0.5)
        assert p.cande_type == "PLASTIC"
        assert p.material == "HDPE"
        assert p.wall_type == "SMOOTH"
        assert p.diameter == 12.0

    def test_section_properties(self):
        p = SmoothHDPE(diameter=12.0, wall_thickness=0.5)
        assert p.area_per_length == pytest.approx(0.5)
        assert p.inertia_per_length == pytest.approx(0.5**3 / 12)


class TestPrecastConcrete:
    def test_defaults(self):
        p = PrecastConcrete(diameter=48.0, wall_thickness=5.0)
        assert p.cande_type == "CONCRETE"
        assert p.compressive_strength == 4000
        assert p.diameter == 48.0
        assert p.wall_thickness == 5.0

    def test_rebar_defaults(self):
        p = PrecastConcrete(diameter=48.0, wall_thickness=5.0)
        assert p.rebar_yield == 60_000
        assert p.rebar_modulus == 29_000_000

    def test_custom_strength(self):
        p = PrecastConcrete(diameter=48.0, wall_thickness=5.0, compressive_strength=6000)
        assert p.compressive_strength == 6000

    def test_repr(self):
        p = PrecastConcrete(diameter=48.0, wall_thickness=5.0)
        assert "PrecastConcrete" in repr(p)
        assert "48.0" in repr(p)

    def test_negative_thickness_raises(self):
        with pytest.raises(ValueError, match="wall_thickness"):
            PrecastConcrete(diameter=48.0, wall_thickness=0.0)

    def test_astm_c76_class_iii(self):
        p = PrecastConcrete.astm_c76_class_iii(diameter=48.0)
        assert p.compressive_strength == 4000
        assert p.wall_thickness > 0


class TestDuctileIron:
    def test_defaults(self):
        p = DuctileIron(diameter=24.0, wall_thickness=0.33)
        assert p.cande_type == "BASIC"
        assert p.youngs_modulus == 24_000_000
        assert p.yield_stress == 42_000
        assert p.poisson_ratio == 0.28

    def test_section_properties(self):
        p = DuctileIron(diameter=24.0, wall_thickness=0.33)
        assert p.area_per_length == pytest.approx(0.33)
        assert p.inertia_per_length == pytest.approx(0.33**3 / 12)

    def test_repr(self):
        p = DuctileIron(diameter=24.0, wall_thickness=0.33)
        assert "DuctileIron" in repr(p)

    def test_awwa_c151(self):
        """AWWA C151 standard ductile iron pipe."""
        p = DuctileIron.awwa_c151(diameter=24.0, pressure_class=350)
        assert p.diameter == 24.0
        assert p.wall_thickness > 0


class TestCorrugatedAluminum:
    def test_defaults(self):
        p = CorrugatedAluminum()
        assert p.cande_type == "ALUMINUM"
        assert p.youngs_modulus == 10_000_000
        assert p.poisson_ratio == 0.33

    def test_repr(self):
        assert "CorrugatedAluminum" in repr(CorrugatedAluminum())


class TestCorrugatedPVC:
    def test_defaults(self):
        p = CorrugatedPVC()
        assert p.cande_type == "PLASTIC"
        assert p.material == "PVC"
        assert p.short_term_modulus == 440_000
        assert p.long_term_modulus == 140_000

    def test_wall_type(self):
        p = CorrugatedPVC()
        assert p.wall_type == "GENERAL"
