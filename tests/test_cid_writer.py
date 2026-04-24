"""Tests for CID file writer and round-trip parsing."""

from pathlib import Path

import pytest

from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.cid_writer import write_cid

EXAMPLE_DATA = Path(__file__).parent / "example_data"


class TestWriteCid:
    """Test writing CID files."""

    def test_round_trip_preserves_node_count(self, tmp_path):
        """Parse -> write -> parse should preserve node count."""
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        reparsed = parse_cid(out_path)
        assert len(reparsed.problems) == len(original.problems)
        assert len(reparsed.problems[0].nodes) == len(original.problems[0].nodes)

    def test_round_trip_preserves_elements(self, tmp_path):
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        reparsed = parse_cid(out_path)
        assert len(reparsed.problems[0].elements) == len(original.problems[0].elements)

    def test_round_trip_preserves_boundaries(self, tmp_path):
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        reparsed = parse_cid(out_path)
        assert len(reparsed.problems[0].boundaries) == len(original.problems[0].boundaries)

    def test_round_trip_node_coordinates(self, tmp_path):
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        reparsed = parse_cid(out_path)

        orig_map = {n.id: n for n in original.problems[0].nodes}
        new_map = {n.id: n for n in reparsed.problems[0].nodes}
        for nid in orig_map:
            assert nid in new_map
            assert abs(orig_map[nid].x - new_map[nid].x) < 0.01
            assert abs(orig_map[nid].y - new_map[nid].y) < 0.01

    def test_round_trip_element_connectivity(self, tmp_path):
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        reparsed = parse_cid(out_path)

        for orig_e, new_e in zip(
            original.problems[0].elements, reparsed.problems[0].elements
        ):
            assert orig_e.nodes == new_e.nodes

    def test_output_has_stop_lines(self, tmp_path):
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        text = out_path.read_text()
        assert text.count("STOP") == 2

    def test_round_trip_bc_values(self, tmp_path):
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        out_path = tmp_path / "roundtrip.cid"
        write_cid(original, out_path)
        reparsed = parse_cid(out_path)

        for orig_bc, new_bc in zip(
            original.problems[0].boundaries, reparsed.problems[0].boundaries
        ):
            assert orig_bc.node == new_bc.node
            assert abs(orig_bc.y_value - new_bc.y_value) < 0.01
