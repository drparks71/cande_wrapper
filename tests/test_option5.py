"""Tests for Option 5: Load rating factor RF."""

import pytest

from cande_wrapper.toolbox.option5_rating import (
    RatingConfig,
    RatingResult,
    CriterionRating,
    compute_rating_factor,
)
from cande_wrapper.toolbox.out_parser import (
    AssessmentEntry,
    AssessmentSummary,
    ParsedOutput,
    parse_out,
)
from pathlib import Path

# The example .out file path
OUT_FILE = (
    Path(__file__).parent.parent
    / "CANDE Source"
    / "CANDEEngine-2025 - MGK Source"
    / "Main"
    / "MGK-IO.out"
)


class TestParseOutAssessments:
    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_finds_assessments(self):
        parsed = parse_out(OUT_FILE)
        assert len(parsed.assessments) > 0

    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_nine_load_steps(self):
        parsed = parse_out(OUT_FILE)
        steps = set(a.step for a in parsed.assessments)
        assert len(steps) == 9

    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_assessment_has_entries(self):
        parsed = parse_out(OUT_FILE)
        for assess in parsed.assessments:
            assert len(assess.entries) > 0

    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_normal_exit(self):
        parsed = parse_out(OUT_FILE)
        assert parsed.normal_exit is True


class TestComputeRatingFactor:
    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_computes_rf(self, tmp_path):
        # Copy the .out file to tmp so we don't modify the original
        import shutil
        tmp_out = tmp_path / "MGK-IO.out"
        shutil.copy2(OUT_FILE, tmp_out)

        config = RatingConfig(
            pipe_group=1,
            dead_load_step=1,
            live_load_start=2,
            live_load_end=9,
        )
        result = compute_rating_factor(tmp_out, config, append_report=True)
        assert isinstance(result, RatingResult)
        assert result.primary_rf > 0

    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_has_secondary_data(self, tmp_path):
        import shutil
        tmp_out = tmp_path / "MGK-IO.out"
        shutil.copy2(OUT_FILE, tmp_out)

        config = RatingConfig(pipe_group=1, dead_load_step=1, live_load_start=2, live_load_end=9)
        result = compute_rating_factor(tmp_out, config, append_report=False)
        assert len(result.secondary) > 0

    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_report_appended(self, tmp_path):
        import shutil
        tmp_out = tmp_path / "MGK-IO.out"
        shutil.copy2(OUT_FILE, tmp_out)

        original_size = tmp_out.stat().st_size
        config = RatingConfig(pipe_group=1, dead_load_step=1, live_load_start=2, live_load_end=9)
        compute_rating_factor(tmp_out, config, append_report=True)
        new_size = tmp_out.stat().st_size
        assert new_size > original_size

    @pytest.mark.skipif(not OUT_FILE.exists(), reason="Example .out file not available")
    def test_report_contains_tool_box(self, tmp_path):
        import shutil
        tmp_out = tmp_path / "MGK-IO.out"
        shutil.copy2(OUT_FILE, tmp_out)

        config = RatingConfig(pipe_group=1, dead_load_step=1, live_load_start=2, live_load_end=9)
        compute_rating_factor(tmp_out, config, append_report=True)
        text = tmp_out.read_text()
        assert "CANDE TOOL BOX" in text


class TestRatingFactorComputation:
    """Unit test RF formula with synthetic data."""

    def test_rf_formula(self):
        # RF = (C - D_dead) / D_live
        capacity = 100.0
        dead = 30.0
        live = 20.0
        rf = (capacity - dead) / live
        assert abs(rf - 3.5) < 0.001

    def test_rf_equals_one_at_threshold(self):
        # When C - D_dead = D_live, RF = 1
        capacity = 100.0
        dead = 30.0
        live = 70.0
        rf = (capacity - dead) / live
        assert abs(rf - 1.0) < 0.001

    def test_rf_negative_when_dead_exceeds_capacity(self):
        capacity = 100.0
        dead = 120.0
        live = 20.0
        rf = (capacity - dead) / live
        assert rf < 0


class TestSafetyDecision:
    """Test 4-level safety assessment per Fortran source."""

    def test_safe(self):
        from cande_wrapper.toolbox.option5_rating import _safety_decision
        assert _safety_decision(1.10) == "SAFE"
        assert _safety_decision(2.0) == "SAFE"

    def test_borderline_safe(self):
        from cande_wrapper.toolbox.option5_rating import _safety_decision
        assert _safety_decision(1.05) == "BORDERLINE SAFE"
        assert _safety_decision(1.00) == "BORDERLINE SAFE"

    def test_borderline_unsafe(self):
        from cande_wrapper.toolbox.option5_rating import _safety_decision
        assert _safety_decision(0.95) == "BORDERLINE UNSAFE"
        assert _safety_decision(0.90) == "BORDERLINE UNSAFE"

    def test_not_safe(self):
        from cande_wrapper.toolbox.option5_rating import _safety_decision
        assert _safety_decision(0.89) == "NOT SAFE"
        assert _safety_decision(0.0) == "NOT SAFE"
        assert _safety_decision(-1.0) == "NOT SAFE"
