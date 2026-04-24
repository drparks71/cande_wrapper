"""Tests for Option 1: Level-2 half mesh to Level-3 full mesh."""

from pathlib import Path

import pytest

from cande_wrapper.toolbox.cid_model import CidProblem, Element, MasterControl, Node
from cande_wrapper.toolbox.option1_full_mesh import (
    _mirror_nodes,
    _mirror_elements,
    _mirror_boundaries,
)


class TestMirrorNodes:
    def test_centerline_not_duplicated(self):
        nodes = [
            Node(id=1, x=0.0, y=0.0),
            Node(id=2, x=10.0, y=0.0),
            Node(id=3, x=0.0, y=10.0),
        ]
        full, mirror_map, nhalf = _mirror_nodes(nodes)
        assert nhalf == 3
        # Centerline nodes (x=0) should not be mirrored
        assert 1 not in mirror_map
        assert 3 not in mirror_map
        # Only node 2 mirrored
        assert 2 in mirror_map
        assert len(full) == 4  # 3 original + 1 mirror

    def test_mirror_coordinates(self):
        nodes = [
            Node(id=1, x=0.0, y=0.0),
            Node(id=2, x=10.0, y=5.0),
        ]
        full, mirror_map, _ = _mirror_nodes(nodes)
        mirrored = next(n for n in full if n.id == mirror_map[2])
        assert mirrored.x == -10.0
        assert mirrored.y == 5.0

    def test_all_nodes_on_centerline(self):
        nodes = [
            Node(id=1, x=0.0, y=0.0),
            Node(id=2, x=0.0, y=10.0),
        ]
        full, mirror_map, _ = _mirror_nodes(nodes)
        assert len(mirror_map) == 0
        assert len(full) == 2  # no new nodes


class TestMirrorElements:
    def test_mirrors_non_centerline_elements(self):
        mirror_map = {2: 5, 3: 6}
        elements = [
            Element(id=1, nodes=(1, 2, 3, 4), mat=1, step=1),
        ]
        # Node 1 and 4 are on centerline (not in mirror_map)
        new = _mirror_elements(elements, mirror_map, nhalf_elems=1)
        assert len(new) == 1
        assert new[0].id == 2

    def test_centerline_elements_not_duplicated(self):
        mirror_map = {}  # no mirrors = all centerline
        elements = [
            Element(id=1, nodes=(1, 2), mat=1, step=1),
        ]
        new = _mirror_elements(elements, mirror_map, nhalf_elems=1)
        assert len(new) == 0


class TestHalfToFullMesh:
    def test_requires_out_file(self, tmp_path):
        from cande_wrapper.toolbox.option1_full_mesh import half_to_full_mesh

        # Create a dummy .cid file
        cid_file = tmp_path / "test.cid"
        cid_file.write_text(
            "                      A-1!!ANALYS   2 0  1 Test\n"
            "                   A-2.L12!!BASIC         1\n"
            "                B-1.Basic!!    1    1      1000         0        10        10         0\n"
            "                B-2.Basic!!    0\n"
            "                   C-1.L1!!        4       4   2    0\n"
            "                   C-2.L1!!         1      1000      0.25\n"
            "                   C-3.L1!!    1    1      1.0 Test\n"
            "                      D-1!!L   1    1          test\n"
            "            D-2.Isotropic!!       100\n"
            "STOP\n"
        )

        with pytest.raises(FileNotFoundError):
            half_to_full_mesh(cid_file, output_dir=tmp_path)
