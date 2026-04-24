"""Tests for CID file parser."""

from pathlib import Path

import pytest

from cande_wrapper.toolbox.cid_parser import parse_cid

EXAMPLE_DATA = Path(__file__).parent / "example_data"


class TestParseCid:
    """Test parsing of .cid files."""

    def test_parse_mgk_io(self):
        """Parse the MGK-IO.cid example with two problems."""
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        assert len(cid.problems) == 2

    def test_first_problem_level3(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        assert p.master.mode == "ANALYS"
        assert p.master.level == 3

    def test_first_problem_nodes(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        assert len(p.nodes) == 11
        # Node 1 at (0, 0)
        n1 = next(n for n in p.nodes if n.id == 1)
        assert n1.x == 0.0
        assert n1.y == 0.0

    def test_first_problem_elements(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        assert len(p.elements) == 8
        # Element 1 is a beam: nodes (6, 1)
        e1 = p.elements[0]
        assert e1.id == 1
        assert e1.nodes == (6, 1)

    def test_first_problem_boundaries(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        assert len(p.boundaries) == 3
        # BC at node 3 has y_value=-10
        bc3 = next(bc for bc in p.boundaries if bc.node == 3)
        assert bc3.y_value == -10.0

    def test_first_problem_soils(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        assert len(p.soils) == 1
        assert p.soils[0].material_num == 1

    def test_first_problem_pipe_groups(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        assert len(p.pipe_groups) == 2
        assert p.pipe_groups[0].pipe_type == "BASIC"

    def test_second_problem_level1(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[1]
        assert p.master.mode == "DESIGN"
        assert p.master.level == 1
        assert p.pipe_groups[0].pipe_type == "STEEL"

    def test_has_line_tags(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        assert cid.problems[0].has_line_tags is True

    def test_quad_element_nodes(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        # Element 5 should have 4 nodes: (8, 5, 4, 10)
        e5 = next(e for e in p.elements if e.id == 5)
        assert len(e5.nodes) == 4
        assert e5.nodes == (8, 5, 4, 10)

    def test_node_coordinates(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        p = cid.problems[0]
        node_map = {n.id: n for n in p.nodes}
        # Node 5 at (5, 5)
        assert node_map[5].x == 5.0
        assert node_map[5].y == 5.0
        # Node 3 at (5, 10)
        assert node_map[3].x == 5.0
        assert node_map[3].y == 10.0
