"""Vehicle definitions for CANDE live-load analysis.

Provides :class:`WheelFootprint`, :class:`Axle`, and :class:`Vehicle` objects
that describe surface vehicle loads applied above buried structures. The wheel
footprint parameters map directly to the CANDE scaling input (line C-2b.L3):
XLONG (length), ZWIDE (width), and SPACING.

Standard AASHTO vehicles are available as factory class methods on
:class:`Vehicle` (e.g. ``Vehicle.hs20()``).
"""

from __future__ import annotations


class WheelFootprint:
    """Dual-wheel footprint geometry.

    Parameters
    ----------
    length : float
        Wheel contact length in the longitudinal (in-plane) direction,
        in inches. Maps to CANDE's XLONG. Default 10.0 (HS-20 standard).
    width : float
        Wheel contact width in the transverse (out-of-plane) direction,
        in inches. Maps to CANDE's ZWIDE. Default 20.0 (HS-20 standard).
    spacing : float
        Center-to-center spacing between dual wheels on the axle,
        in inches. Maps to CANDE's SPACING. Default 72.0 (HS-20 standard).
    """

    def __init__(
        self,
        length: float = 10.0,
        width: float = 20.0,
        spacing: float = 72.0,
    ):
        if length <= 0:
            raise ValueError(f"length must be positive, got {length}")
        if width <= 0:
            raise ValueError(f"width must be positive, got {width}")
        if spacing <= 0:
            raise ValueError(f"spacing must be positive, got {spacing}")
        self.length = length
        self.width = width
        self.spacing = spacing

    def __repr__(self) -> str:
        return (
            f"WheelFootprint(length={self.length}, width={self.width}, "
            f"spacing={self.spacing})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WheelFootprint):
            return NotImplemented
        return (
            self.length == other.length
            and self.width == other.width
            and self.spacing == other.spacing
        )


class Axle:
    """A single axle with a weight and position.

    Parameters
    ----------
    weight : float
        Total axle weight in pounds.
    spacing : float
        Distance from the previous axle in inches. Use 0.0 for the
        first (leading) axle.
    """

    def __init__(self, weight: float, spacing: float):
        if weight < 0:
            raise ValueError(f"weight must be non-negative, got {weight}")
        if spacing < 0:
            raise ValueError(f"spacing must be non-negative, got {spacing}")
        self.weight = weight
        self.spacing = spacing

    def __repr__(self) -> str:
        return f"Axle(weight={self.weight}, spacing={self.spacing})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Axle):
            return NotImplemented
        return self.weight == other.weight and self.spacing == other.spacing


class Vehicle:
    """A surface vehicle for live-load analysis.

    Parameters
    ----------
    name : str
        Descriptive name (e.g. "HS-20").
    footprint : WheelFootprint
        Dual-wheel contact geometry.
    axles : list[Axle]
        One or more axles, ordered front to rear. The first axle
        should have ``spacing=0.0``.
    """

    def __init__(
        self,
        name: str,
        footprint: WheelFootprint,
        axles: list[Axle],
    ):
        if not axles:
            raise ValueError("Vehicle must have at least one axle")
        self.name = name
        self.footprint = footprint
        self.axles = tuple(axles)

    @property
    def total_weight(self) -> float:
        """Sum of all axle weights in pounds."""
        return sum(a.weight for a in self.axles)

    def __repr__(self) -> str:
        return (
            f"Vehicle(name={self.name!r}, axles={len(self.axles)}, "
            f"total_weight={self.total_weight})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vehicle):
            return NotImplemented
        return (
            self.name == other.name
            and self.footprint == other.footprint
            and self.axles == other.axles
        )

    # -- Standard vehicle factory methods ------------------------------------

    @classmethod
    def hs20(cls) -> Vehicle:
        """AASHTO HS-20 design truck (72 kip total).

        Three axles: 8k steering + 32k drive + 32k rear, spaced at 14 ft.
        """
        return cls(
            name="HS-20",
            footprint=WheelFootprint(),
            axles=[
                Axle(weight=8000.0, spacing=0.0),
                Axle(weight=32000.0, spacing=168.0),
                Axle(weight=32000.0, spacing=168.0),
            ],
        )

    @classmethod
    def hs25(cls) -> Vehicle:
        """AASHTO HS-25 design truck (90 kip total).

        Three axles: 10k steering + 40k drive + 40k rear, spaced at 14 ft.
        """
        return cls(
            name="HS-25",
            footprint=WheelFootprint(),
            axles=[
                Axle(weight=10000.0, spacing=0.0),
                Axle(weight=40000.0, spacing=168.0),
                Axle(weight=40000.0, spacing=168.0),
            ],
        )

    @classmethod
    def cooper_e80(cls) -> Vehicle:
        """Cooper E-80 railroad loading (160 kip over 4 axles).

        Four 40-kip axles spaced at 60 inches.
        """
        return cls(
            name="Cooper E-80",
            footprint=WheelFootprint(length=10.0, width=20.0, spacing=72.0),
            axles=[
                Axle(weight=40000.0, spacing=0.0),
                Axle(weight=40000.0, spacing=60.0),
                Axle(weight=40000.0, spacing=60.0),
                Axle(weight=40000.0, spacing=60.0),
            ],
        )

    @classmethod
    def tandem(cls) -> Vehicle:
        """AASHTO design tandem (50 kip total).

        Two 25-kip axles spaced at 4 ft.
        """
        return cls(
            name="Tandem",
            footprint=WheelFootprint(),
            axles=[
                Axle(weight=25000.0, spacing=0.0),
                Axle(weight=25000.0, spacing=48.0),
            ],
        )
