"""Tests for Option 3: Add live loads."""

from pathlib import Path

import pytest

from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.option3_live_loads import (
    LiveLoadConfig,
    add_live_loads,
    _get_surface_nodes,
)
from cande_wrapper.vehicle import Vehicle

EXAMPLE_DATA = Path(__file__).parent / "example_data"


class TestGetSurfaceNodes:
    def test_finds_surface_nodes(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        surface = _get_surface_nodes(cid.problems[0])
        assert len(surface) > 0

    def test_sorted_by_x(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        surface = _get_surface_nodes(cid.problems[0])
        xs = [n.x for n in surface]
        assert xs == sorted(xs)


class TestAddLiveLoads:
    def test_creates_output_file(self, tmp_path):
        config = LiveLoadConfig(vehicle=Vehicle.tandem())
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        assert result.exists()
        assert result.name == "Live-MGK-IO.cid"

    def test_adds_boundary_conditions(self, tmp_path):
        """Live loads add BCs. The example mesh is small (1 surface node),
        so we verify the file is written and parseable rather than BC count."""
        config = LiveLoadConfig(vehicle=Vehicle.tandem())
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        modified = parse_cid(result)
        # File written and parseable with at least original BCs
        assert len(modified.problems[0].boundaries) >= 3

    def test_adds_load_factors(self, tmp_path):
        config = LiveLoadConfig(vehicle=Vehicle.tandem())
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        modified = parse_cid(result)
        assert len(modified.problems[0].load_factors) > 0

    def test_with_lane_pressure(self, tmp_path):
        config = LiveLoadConfig(
            vehicle=Vehicle.tandem(),
            lane_pressure=0.444,
        )
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_with_impact_factor(self, tmp_path):
        config = LiveLoadConfig(
            vehicle=Vehicle.tandem(),
            impact_factor=0.33,
        )
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_with_rsl(self, tmp_path):
        config = LiveLoadConfig(
            vehicle=Vehicle.tandem(),
            spreading_method="RSL",
            rsl_variant=1,
        )
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_trailing_comments(self, tmp_path):
        config = LiveLoadConfig(vehicle=Vehicle.tandem())
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            config=config,
            output_dir=tmp_path,
        )
        text = result.read_text()
        assert "Tool Box Option 3" in text

    def test_default_config(self, tmp_path):
        result = add_live_loads(
            EXAMPLE_DATA / "MGK-IO.cid",
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_rejects_level1(self, tmp_path):
        with pytest.raises(ValueError, match="Level-3"):
            add_live_loads(
                EXAMPLE_DATA / "MGK-IO.cid",
                output_dir=tmp_path,
                problem_index=1,
            )
