"""Tests for Option 2: Add pavement and/or elastic wearing course."""

from pathlib import Path

import pytest

from cande_wrapper.toolbox.cid_parser import parse_cid
from cande_wrapper.toolbox.option2_pavement import (
    PavementConfig,
    WearingCourseConfig,
    add_pavement,
    _find_surface_elements,
)

EXAMPLE_DATA = Path(__file__).parent / "example_data"


class TestFindSurfaceElements:
    def test_finds_surface(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        surface = _find_surface_elements(cid.problems[0])
        # The example mesh has surface elements at y=10 (max)
        assert len(surface) > 0

    def test_only_quad_elements(self):
        cid = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        surface = _find_surface_elements(cid.problems[0])
        for elem in surface:
            assert len(elem.nodes) >= 4


class TestAddPavement:
    def test_creates_output_file(self, tmp_path):
        result = add_pavement(
            EXAMPLE_DATA / "MGK-IO.cid",
            pavement=PavementConfig(),
            output_dir=tmp_path,
        )
        assert result.exists()
        assert result.name == "Pave-MGK-IO.cid"

    def test_adds_pipe_group(self, tmp_path):
        result = add_pavement(
            EXAMPLE_DATA / "MGK-IO.cid",
            pavement=PavementConfig(),
            output_dir=tmp_path,
        )
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        modified = parse_cid(result)
        assert len(modified.problems[0].pipe_groups) == len(original.problems[0].pipe_groups) + 1

    def test_adds_beam_elements(self, tmp_path):
        result = add_pavement(
            EXAMPLE_DATA / "MGK-IO.cid",
            pavement=PavementConfig(),
            output_dir=tmp_path,
        )
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        modified = parse_cid(result)
        assert len(modified.problems[0].elements) > len(original.problems[0].elements)

    def test_wearing_course_adds_soil(self, tmp_path):
        result = add_pavement(
            EXAMPLE_DATA / "MGK-IO.cid",
            wearing_course=WearingCourseConfig(),
            output_dir=tmp_path,
        )
        original = parse_cid(EXAMPLE_DATA / "MGK-IO.cid")
        modified = parse_cid(result)
        assert len(modified.problems[0].soils) > len(original.problems[0].soils)

    def test_both_options(self, tmp_path):
        result = add_pavement(
            EXAMPLE_DATA / "MGK-IO.cid",
            pavement=PavementConfig(),
            wearing_course=WearingCourseConfig(),
            output_dir=tmp_path,
        )
        assert result.exists()

    def test_rejects_no_options(self, tmp_path):
        with pytest.raises(ValueError, match="Must specify"):
            add_pavement(
                EXAMPLE_DATA / "MGK-IO.cid",
                output_dir=tmp_path,
            )

    def test_rejects_level1(self, tmp_path):
        with pytest.raises(ValueError, match="Level-3"):
            add_pavement(
                EXAMPLE_DATA / "MGK-IO.cid",
                pavement=PavementConfig(),
                output_dir=tmp_path,
                problem_index=1,
            )

    def test_trailing_comment(self, tmp_path):
        result = add_pavement(
            EXAMPLE_DATA / "MGK-IO.cid",
            pavement=PavementConfig(),
            output_dir=tmp_path,
        )
        text = result.read_text()
        assert "Tool Box Option 2" in text
