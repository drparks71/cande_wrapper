"""Tests for Option 4: Minimize bandwidth."""

from pathlib import Path

import pytest

from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.option4_bandwidth import (
    _compute_bandwidth,
    _geometric_renumber,
    minimize_bandwidth,
)

EXAMPLE_DATA = Path(__file__).parent / "example_data"


class TestComputeBandwidth:
    def test_example_bandwidth(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        bw = _compute_bandwidth(cid.problems[0])
        assert bw > 0

    def test_bandwidth_with_nonoptimal_nodes(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        bw = _compute_bandwidth(cid.problems[0])
        # The example says "Non optimum node numbers" so bandwidth should be > 2
        assert bw > 2


class TestGeometricRenumber:
    def test_produces_mapping(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        mapping = _geometric_renumber(cid.problems[0])
        assert len(mapping) == len(cid.problems[0].nodes)

    def test_sequential_ids(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        mapping = _geometric_renumber(cid.problems[0])
        new_ids = sorted(mapping.values())
        assert new_ids == list(range(1, len(mapping) + 1))

    def test_lower_left_gets_node_1(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        problem = cid.problems[0]
        mapping = _geometric_renumber(problem)
        # Node at (0, 0) should be node 1
        node_at_origin = next(n for n in problem.nodes if n.x == 0 and n.y == 0)
        assert mapping[node_at_origin.id] == 1


class TestMinimizeBandwidth:
    def test_creates_output_file(self, tmp_path):
        result = minimize_bandwidth(
            EXAMPLE_DATA / "MGK-IO.cid",
            output_dir=tmp_path,
        )
        assert result.exists()
        assert result.name == "Bmin-MGK-IO.cid"

    def test_bandwidth_reduced(self, tmp_path):
        result = minimize_bandwidth(
            EXAMPLE_DATA / "MGK-IO.cid",
            output_dir=tmp_path,
        )
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        optimized = parse_cid(result)
        old_bw = _compute_bandwidth(original.problems[0])
        new_bw = _compute_bandwidth(optimized.problems[0])
        assert new_bw <= old_bw

    def test_preserves_node_count(self, tmp_path):
        result = minimize_bandwidth(
            EXAMPLE_DATA / "MGK-IO.cid",
            output_dir=tmp_path,
        )
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        optimized = parse_cid(result)
        assert len(optimized.problems[0].nodes) == len(original.problems[0].nodes)

    def test_preserves_element_count(self, tmp_path):
        result = minimize_bandwidth(
            EXAMPLE_DATA / "MGK-IO.cid",
            output_dir=tmp_path,
        )
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        optimized = parse_cid(result)
        assert len(optimized.problems[0].elements) == len(original.problems[0].elements)

    def test_rejects_level1(self, tmp_path):
        with pytest.raises(ValueError, match="Level-3"):
            minimize_bandwidth(
                EXAMPLE_DATA / "MGK-IO.cid",
                output_dir=tmp_path,
                problem_index=1,  # Level-1 problem
            )

    def test_trailing_comment_added(self, tmp_path):
        result = minimize_bandwidth(
            EXAMPLE_DATA / "MGK-IO.cid",
            output_dir=tmp_path,
        )
        text = result.read_text()
        assert "Tool Box Option 4" in text
