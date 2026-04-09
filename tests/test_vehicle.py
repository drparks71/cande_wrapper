"""Unit tests for Vehicle definitions."""

from __future__ import annotations

import pytest

from cande_wrapper.vehicle import Axle, Vehicle, WheelFootprint


class TestWheelFootprint:
    def test_create_with_defaults(self):
        fp = WheelFootprint()
        assert fp.length == 10.0
        assert fp.width == 20.0
        assert fp.spacing == 72.0

    def test_create_custom(self):
        fp = WheelFootprint(length=12.0, width=24.0, spacing=60.0)
        assert fp.length == 12.0
        assert fp.width == 24.0
        assert fp.spacing == 60.0

    def test_negative_length_raises(self):
        with pytest.raises(ValueError, match="length"):
            WheelFootprint(length=-1.0)

    def test_zero_width_raises(self):
        with pytest.raises(ValueError, match="width"):
            WheelFootprint(width=0.0)

    def test_negative_spacing_raises(self):
        with pytest.raises(ValueError, match="spacing"):
            WheelFootprint(spacing=-5.0)

    def test_repr(self):
        fp = WheelFootprint(length=10.0, width=20.0, spacing=72.0)
        r = repr(fp)
        assert "10.0" in r
        assert "20.0" in r
        assert "72.0" in r

    def test_equality(self):
        a = WheelFootprint(length=10.0, width=20.0, spacing=72.0)
        b = WheelFootprint(length=10.0, width=20.0, spacing=72.0)
        assert a == b

    def test_inequality(self):
        a = WheelFootprint(length=10.0, width=20.0, spacing=72.0)
        b = WheelFootprint(length=12.0, width=20.0, spacing=72.0)
        assert a != b


class TestAxle:
    def test_create(self):
        axle = Axle(weight=16000.0, spacing=168.0)
        assert axle.weight == 16000.0
        assert axle.spacing == 168.0

    def test_first_axle_zero_spacing(self):
        axle = Axle(weight=8000.0, spacing=0.0)
        assert axle.spacing == 0.0

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="weight"):
            Axle(weight=-100.0, spacing=0.0)

    def test_negative_spacing_raises(self):
        with pytest.raises(ValueError, match="spacing"):
            Axle(spacing=-10.0, weight=1000.0)

    def test_repr(self):
        axle = Axle(weight=16000.0, spacing=168.0)
        r = repr(axle)
        assert "16000.0" in r
        assert "168.0" in r

    def test_equality(self):
        a = Axle(weight=16000.0, spacing=168.0)
        b = Axle(weight=16000.0, spacing=168.0)
        assert a == b


class TestVehicle:
    def test_create_minimal(self):
        fp = WheelFootprint()
        axles = [Axle(weight=16000.0, spacing=0.0)]
        v = Vehicle(name="test", footprint=fp, axles=axles)
        assert v.name == "test"
        assert v.footprint is fp
        assert len(v.axles) == 1

    def test_create_multi_axle(self):
        fp = WheelFootprint()
        axles = [
            Axle(weight=8000.0, spacing=0.0),
            Axle(weight=32000.0, spacing=168.0),
            Axle(weight=32000.0, spacing=336.0),
        ]
        v = Vehicle(name="HS-20", footprint=fp, axles=axles)
        assert len(v.axles) == 3

    def test_total_weight(self):
        axles = [
            Axle(weight=8000.0, spacing=0.0),
            Axle(weight=32000.0, spacing=168.0),
            Axle(weight=32000.0, spacing=336.0),
        ]
        v = Vehicle(name="HS-20", footprint=WheelFootprint(), axles=axles)
        assert v.total_weight == 72000.0

    def test_empty_axles_raises(self):
        with pytest.raises(ValueError, match="axle"):
            Vehicle(name="empty", footprint=WheelFootprint(), axles=[])

    def test_repr(self):
        v = Vehicle(
            name="test",
            footprint=WheelFootprint(),
            axles=[Axle(weight=16000.0, spacing=0.0)],
        )
        r = repr(v)
        assert "test" in r

    def test_equality(self):
        args = dict(
            name="test",
            footprint=WheelFootprint(),
            axles=[Axle(weight=16000.0, spacing=0.0)],
        )
        assert Vehicle(**args) == Vehicle(**args)

    def test_inequality_name(self):
        fp = WheelFootprint()
        axles = [Axle(weight=16000.0, spacing=0.0)]
        a = Vehicle(name="a", footprint=fp, axles=axles)
        b = Vehicle(name="b", footprint=fp, axles=axles)
        assert a != b

    def test_axles_are_copied(self):
        """Modifying the original list should not affect the vehicle."""
        axles = [Axle(weight=16000.0, spacing=0.0)]
        v = Vehicle(name="test", footprint=WheelFootprint(), axles=axles)
        axles.append(Axle(weight=32000.0, spacing=100.0))
        assert len(v.axles) == 1

    def test_axles_immutable(self):
        """The axles tuple should not be modifiable."""
        v = Vehicle(
            name="test",
            footprint=WheelFootprint(),
            axles=[Axle(weight=16000.0, spacing=0.0)],
        )
        assert isinstance(v.axles, tuple)


class TestStandardVehicles:
    """Test the built-in standard vehicle factory methods."""

    def test_hs20(self):
        v = Vehicle.hs20()
        assert v.name == "HS-20"
        assert len(v.axles) == 3
        assert v.total_weight == 72000.0
        # HS-20 standard footprint
        assert v.footprint.length == 10.0
        assert v.footprint.width == 20.0
        assert v.footprint.spacing == 72.0

    def test_hs25(self):
        v = Vehicle.hs25()
        assert v.name == "HS-25"
        assert len(v.axles) == 3
        assert v.total_weight == 90000.0

    def test_hs20_axle_weights(self):
        v = Vehicle.hs20()
        weights = [a.weight for a in v.axles]
        assert weights == [8000.0, 32000.0, 32000.0]

    def test_hs20_axle_spacings(self):
        v = Vehicle.hs20()
        spacings = [a.spacing for a in v.axles]
        assert spacings == [0.0, 168.0, 168.0]

    def test_hs25_axle_weights(self):
        v = Vehicle.hs25()
        weights = [a.weight for a in v.axles]
        assert weights == [10000.0, 40000.0, 40000.0]

    def test_cooper_e80(self):
        v = Vehicle.cooper_e80()
        assert v.name == "Cooper E-80"
        assert len(v.axles) == 4

    def test_cooper_e80_total_weight(self):
        v = Vehicle.cooper_e80()
        assert v.total_weight == 160000.0

    def test_tandem(self):
        v = Vehicle.tandem()
        assert v.name == "Tandem"
        assert len(v.axles) == 2
        assert v.total_weight == 50000.0

    def test_tandem_axle_spacings(self):
        v = Vehicle.tandem()
        spacings = [a.spacing for a in v.axles]
        assert spacings == [0.0, 48.0]
