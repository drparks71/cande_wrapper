"""Pipe type definitions for CANDE analysis.

Each class represents a common pipe material and cross-section type,
storing the material properties and section geometry that map to
CANDE's B-section input lines.

CANDE natively supports: STEEL, ALUMINUM, CONCRETE, PLASTIC, and BASIC
pipe types. Smooth-wall steel, ductile iron, and other non-corrugated
pipes are modeled using the BASIC type with user-specified section
properties.
"""

from __future__ import annotations

import math


class CorrugatedSteel:
    """Corrugated steel pipe (CANDE STEEL type).

    Standard corrugation profiles per AASHTO: 1.5x0.25", 2-2/3x0.5",
    3x1", 5x1", and 6x2" structural plate.

    Parameters
    ----------
    youngs_modulus : float
        Young's modulus in psi. Default 29,000,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.3.
    yield_stress : float
        Yield stress in psi. Default 33,000 for standard corrugations,
        up to 50,000 for higher-strength steel.
    name : str
        Descriptive name.
    """

    cande_type = "STEEL"

    def __init__(
        self,
        youngs_modulus: float = 29_000_000,
        poisson_ratio: float = 0.3,
        yield_stress: float = 33_000,
        name: str = "Corrugated Steel",
    ):
        self.youngs_modulus = youngs_modulus
        self.poisson_ratio = poisson_ratio
        self.yield_stress = yield_stress
        self.name = name

    @classmethod
    def structural_plate(cls) -> CorrugatedSteel:
        """6x2" structural plate (Fy=33,000 psi per ASTM A761)."""
        return cls(yield_stress=33_000, name="Structural Plate")

    def __repr__(self) -> str:
        return (
            f"CorrugatedSteel(Fy={self.yield_stress}, "
            f"E={self.youngs_modulus})"
        )


class CorrugatedAluminum:
    """Corrugated aluminum pipe (CANDE ALUMINUM type).

    Standard corrugation profiles: 1.5x0.25", 2-2/3x0.5", 3x1",
    6x1", 9x2.5".

    Parameters
    ----------
    youngs_modulus : float
        Young's modulus in psi. Default 10,000,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.33.
    yield_stress : float
        Yield stress in psi. Default 24,000 (Alloy 5052).
    name : str
        Descriptive name.
    """

    cande_type = "ALUMINUM"

    def __init__(
        self,
        youngs_modulus: float = 10_000_000,
        poisson_ratio: float = 0.33,
        yield_stress: float = 24_000,
        name: str = "Corrugated Aluminum",
    ):
        self.youngs_modulus = youngs_modulus
        self.poisson_ratio = poisson_ratio
        self.yield_stress = yield_stress
        self.name = name

    def __repr__(self) -> str:
        return (
            f"CorrugatedAluminum(Fy={self.yield_stress}, "
            f"E={self.youngs_modulus})"
        )


class SmoothSteelCasing:
    """Smooth-wall steel casing pipe (CANDE BASIC type).

    Used for steel encasement of utilities, jack-and-bore casings,
    and smooth-wall steel pipe. Since CANDE's STEEL type is for
    corrugated profiles, smooth steel is modeled with BASIC.

    Parameters
    ----------
    diameter : float
        Inside diameter in inches.
    wall_thickness : float
        Wall thickness in inches.
    youngs_modulus : float
        Young's modulus in psi. Default 29,000,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.3.
    yield_stress : float
        Yield stress in psi. Default 36,000 (ASTM A53 Grade B).
    name : str
        Descriptive name.
    """

    cande_type = "BASIC"

    def __init__(
        self,
        diameter: float,
        wall_thickness: float,
        youngs_modulus: float = 29_000_000,
        poisson_ratio: float = 0.3,
        yield_stress: float = 36_000,
        name: str = "Smooth Steel Casing",
    ):
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        if wall_thickness <= 0:
            raise ValueError(
                f"wall_thickness must be positive, got {wall_thickness}"
            )
        self.diameter = diameter
        self.wall_thickness = wall_thickness
        self.youngs_modulus = youngs_modulus
        self.poisson_ratio = poisson_ratio
        self.yield_stress = yield_stress
        self.name = name

    @property
    def area_per_length(self) -> float:
        """Cross-sectional area per unit length (in^2/in)."""
        return self.wall_thickness

    @property
    def inertia_per_length(self) -> float:
        """Moment of inertia per unit length (in^4/in)."""
        return self.wall_thickness ** 3 / 12

    @classmethod
    def api_5l_grade_b(
        cls, diameter: float, wall_thickness: float
    ) -> SmoothSteelCasing:
        """API 5L Grade B line pipe (Fy=35,000 psi)."""
        return cls(
            diameter=diameter,
            wall_thickness=wall_thickness,
            yield_stress=35_000,
            name="API 5L Grade B",
        )

    def __repr__(self) -> str:
        return (
            f"SmoothSteelCasing(D={self.diameter}, "
            f"t={self.wall_thickness}, Fy={self.yield_stress})"
        )


class CorrugatedHDPE:
    """Corrugated HDPE pipe (CANDE PLASTIC type, GENERAL wall).

    High-density polyethylene with corrugated wall profile.
    Properties follow AASHTO LRFD Section 12.12.

    Parameters
    ----------
    short_term_modulus : float
        Short-term Young's modulus in psi. Default 110,000.
    long_term_modulus : float
        Long-term (50-year) Young's modulus in psi. Default 22,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.33.
    name : str
        Descriptive name.
    """

    cande_type = "PLASTIC"
    material = "HDPE"
    wall_type = "GENERAL"

    def __init__(
        self,
        short_term_modulus: float = 110_000,
        long_term_modulus: float = 22_000,
        poisson_ratio: float = 0.33,
        name: str = "Corrugated HDPE",
    ):
        self.short_term_modulus = short_term_modulus
        self.long_term_modulus = long_term_modulus
        self.poisson_ratio = poisson_ratio
        self.name = name

    def __repr__(self) -> str:
        return (
            f"CorrugatedHDPE(E_short={self.short_term_modulus}, "
            f"E_long={self.long_term_modulus})"
        )


class CorrugatedPVC:
    """Corrugated PVC pipe (CANDE PLASTIC type, GENERAL wall).

    Polyvinyl chloride with corrugated wall profile.

    Parameters
    ----------
    short_term_modulus : float
        Short-term Young's modulus in psi. Default 440,000.
    long_term_modulus : float
        Long-term (50-year) Young's modulus in psi. Default 140,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.33.
    name : str
        Descriptive name.
    """

    cande_type = "PLASTIC"
    material = "PVC"
    wall_type = "GENERAL"

    def __init__(
        self,
        short_term_modulus: float = 440_000,
        long_term_modulus: float = 140_000,
        poisson_ratio: float = 0.33,
        name: str = "Corrugated PVC",
    ):
        self.short_term_modulus = short_term_modulus
        self.long_term_modulus = long_term_modulus
        self.poisson_ratio = poisson_ratio
        self.name = name

    def __repr__(self) -> str:
        return (
            f"CorrugatedPVC(E_short={self.short_term_modulus}, "
            f"E_long={self.long_term_modulus})"
        )


class SmoothHDPE:
    """Smooth-wall HDPE pipe (CANDE PLASTIC type, SMOOTH wall).

    Parameters
    ----------
    diameter : float
        Inside diameter in inches.
    wall_thickness : float
        Wall thickness in inches.
    short_term_modulus : float
        Short-term Young's modulus in psi. Default 110,000.
    long_term_modulus : float
        Long-term (50-year) Young's modulus in psi. Default 22,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.33.
    name : str
        Descriptive name.
    """

    cande_type = "PLASTIC"
    material = "HDPE"
    wall_type = "SMOOTH"

    def __init__(
        self,
        diameter: float,
        wall_thickness: float,
        short_term_modulus: float = 110_000,
        long_term_modulus: float = 22_000,
        poisson_ratio: float = 0.33,
        name: str = "Smooth HDPE",
    ):
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        if wall_thickness <= 0:
            raise ValueError(
                f"wall_thickness must be positive, got {wall_thickness}"
            )
        self.diameter = diameter
        self.wall_thickness = wall_thickness
        self.short_term_modulus = short_term_modulus
        self.long_term_modulus = long_term_modulus
        self.poisson_ratio = poisson_ratio
        self.name = name

    @property
    def area_per_length(self) -> float:
        """Cross-sectional area per unit length (in^2/in)."""
        return self.wall_thickness

    @property
    def inertia_per_length(self) -> float:
        """Moment of inertia per unit length (in^4/in)."""
        return self.wall_thickness ** 3 / 12

    def __repr__(self) -> str:
        return (
            f"SmoothHDPE(D={self.diameter}, t={self.wall_thickness})"
        )


class PrecastConcrete:
    """Precast reinforced concrete pipe (CANDE CONCRETE type).

    Circular reinforced concrete pipe per ASTM C76.

    Parameters
    ----------
    diameter : float
        Inside diameter in inches.
    wall_thickness : float
        Wall thickness in inches.
    compressive_strength : float
        Concrete compressive strength f'c in psi. Default 4,000.
    poisson_ratio : float
        Concrete Poisson's ratio. Default 0.17.
    density : float
        Concrete density in lb/ft^3. Default 150.
    rebar_yield : float
        Reinforcing steel yield stress in psi. Default 60,000.
    rebar_modulus : float
        Reinforcing steel Young's modulus in psi. Default 29,000,000.
    inner_steel_area : float
        Inner cage steel area per unit length (in^2/in). Default 0.0.
    outer_steel_area : float
        Outer cage steel area per unit length (in^2/in). Default 0.0.
    inner_cover : float
        Cover depth to inner steel centroid (in). Default 1.0.
    outer_cover : float
        Cover depth to outer steel centroid (in). Default 1.0.
    name : str
        Descriptive name.
    """

    cande_type = "CONCRETE"

    def __init__(
        self,
        diameter: float,
        wall_thickness: float,
        compressive_strength: float = 4000,
        poisson_ratio: float = 0.17,
        density: float = 150.0,
        rebar_yield: float = 60_000,
        rebar_modulus: float = 29_000_000,
        inner_steel_area: float = 0.0,
        outer_steel_area: float = 0.0,
        inner_cover: float = 1.0,
        outer_cover: float = 1.0,
        name: str = "Precast Concrete",
    ):
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        if wall_thickness <= 0:
            raise ValueError(
                f"wall_thickness must be positive, got {wall_thickness}"
            )
        self.diameter = diameter
        self.wall_thickness = wall_thickness
        self.compressive_strength = compressive_strength
        self.poisson_ratio = poisson_ratio
        self.density = density
        self.rebar_yield = rebar_yield
        self.rebar_modulus = rebar_modulus
        self.inner_steel_area = inner_steel_area
        self.outer_steel_area = outer_steel_area
        self.inner_cover = inner_cover
        self.outer_cover = outer_cover
        self.name = name

    @property
    def elastic_modulus(self) -> float:
        """ACI concrete elastic modulus: 33 * density^1.5 * sqrt(f'c)."""
        return 33.0 * self.density ** 1.5 * math.sqrt(self.compressive_strength)

    @classmethod
    def astm_c76_class_iii(cls, diameter: float) -> PrecastConcrete:
        """ASTM C76 Class III reinforced concrete pipe.

        Wall thickness based on ASTM C76 Table 1 minimum wall B.
        """
        # ASTM C76 minimum Wall B thickness (approximate, inches)
        if diameter <= 12:
            t = 1.75
        elif diameter <= 24:
            t = 2.5
        elif diameter <= 36:
            t = 3.5
        elif diameter <= 48:
            t = 4.5
        elif diameter <= 60:
            t = 5.75
        elif diameter <= 72:
            t = 6.75
        elif diameter <= 96:
            t = 8.0
        else:
            t = 9.5
        return cls(
            diameter=diameter,
            wall_thickness=t,
            compressive_strength=4000,
            name="ASTM C76 Class III",
        )

    def __repr__(self) -> str:
        return (
            f"PrecastConcrete(D={self.diameter}, t={self.wall_thickness}, "
            f"f'c={self.compressive_strength})"
        )


class DuctileIron:
    """Ductile iron pipe (CANDE BASIC type).

    Ductile iron is not a native CANDE pipe type but is commonly used
    for water/sewer infrastructure. Modeled using BASIC type with
    appropriate material properties per AWWA C150/C151.

    Parameters
    ----------
    diameter : float
        Nominal inside diameter in inches.
    wall_thickness : float
        Wall thickness in inches.
    youngs_modulus : float
        Young's modulus in psi. Default 24,000,000.
    poisson_ratio : float
        Poisson's ratio. Default 0.28.
    yield_stress : float
        Minimum yield stress in psi. Default 42,000 (ASTM A536).
    name : str
        Descriptive name.
    """

    cande_type = "BASIC"

    def __init__(
        self,
        diameter: float,
        wall_thickness: float,
        youngs_modulus: float = 24_000_000,
        poisson_ratio: float = 0.28,
        yield_stress: float = 42_000,
        name: str = "Ductile Iron",
    ):
        if diameter <= 0:
            raise ValueError(f"diameter must be positive, got {diameter}")
        if wall_thickness <= 0:
            raise ValueError(
                f"wall_thickness must be positive, got {wall_thickness}"
            )
        self.diameter = diameter
        self.wall_thickness = wall_thickness
        self.youngs_modulus = youngs_modulus
        self.poisson_ratio = poisson_ratio
        self.yield_stress = yield_stress
        self.name = name

    @property
    def area_per_length(self) -> float:
        """Cross-sectional area per unit length (in^2/in)."""
        return self.wall_thickness

    @property
    def inertia_per_length(self) -> float:
        """Moment of inertia per unit length (in^4/in)."""
        return self.wall_thickness ** 3 / 12

    @classmethod
    def awwa_c151(
        cls, diameter: float, pressure_class: int = 350
    ) -> DuctileIron:
        """AWWA C151 ductile iron pipe.

        Wall thickness per AWWA C150 Table 50.5 (approximate).

        Parameters
        ----------
        diameter : float
            Nominal diameter in inches.
        pressure_class : int
            Pressure class (150, 200, 250, 300, 350). Default 350.
        """
        # Approximate net wall thickness (inches) from AWWA C150
        # based on pressure class 350 for common sizes
        if diameter <= 4:
            t = 0.26
        elif diameter <= 6:
            t = 0.25
        elif diameter <= 8:
            t = 0.27
        elif diameter <= 10:
            t = 0.29
        elif diameter <= 12:
            t = 0.31
        elif diameter <= 16:
            t = 0.34
        elif diameter <= 20:
            t = 0.37
        elif diameter <= 24:
            t = 0.40
        elif diameter <= 30:
            t = 0.45
        elif diameter <= 36:
            t = 0.51
        elif diameter <= 42:
            t = 0.57
        elif diameter <= 48:
            t = 0.63
        else:
            t = 0.69
        return cls(
            diameter=diameter,
            wall_thickness=t,
            name=f"AWWA C151 PC{pressure_class}",
        )

    def __repr__(self) -> str:
        return (
            f"DuctileIron(D={self.diameter}, t={self.wall_thickness}, "
            f"Fy={self.yield_stress})"
        )
