import math
from pathlib import Path

import pytest

from block_B.block_b_todo import measure_person_range, select_person
from block_B.fixture_io import load_fixtures

ROOT = Path(__file__).resolve().parents[1] / "fixtures"
BBOX = {"x1": 1, "y1": 1, "x2": 3, "y2": 3, "image_width": 4, "image_height": 4}
DEPTH = [[2, 2, 2, 2], [2, 1.0, 1.2, 2], [2, 1.4, 1.6, 2], [2, 2, 2, 2]]


def test_select_person_ignores_other_labels_and_selects_highest():
    rows, _ = load_fixtures(ROOT)
    result = select_person([*rows[:2], {**rows[0], "confidence": "0.84"}])
    assert result is not None and float(result["confidence"]) == pytest.approx(0.92)


def test_low_confidence_or_missing_person_is_unknown():
    rows, _ = load_fixtures(ROOT)
    assert select_person([rows[2]]) is None
    assert select_person([rows[1]]) is None


@pytest.mark.parametrize("invalid", ["NaN", "1.1", "-0.1", True])
def test_invalid_confidence_rejected(invalid):
    rows, _ = load_fixtures(ROOT)
    with pytest.raises(ValueError):
        select_person([{**rows[0], "confidence": invalid}])


def test_out_of_image_bbox_rejected():
    rows, _ = load_fixtures(ROOT)
    with pytest.raises(ValueError):
        select_person([{**rows[0], "x1": "-1"}])


def test_f001_median_depth():
    assert measure_person_range(DEPTH, BBOX, 1.0, 1.02) == pytest.approx(1.3)


def test_missing_or_invalid_depth_becomes_unknown():
    depth = [[0, "NaN"], ["Infinity", 0.9]]
    roi = {"x1": 0, "y1": 0, "x2": 2, "y2": 2, "image_width": 2, "image_height": 2}
    assert measure_person_range(depth, roi, 1.0, 1.0) is None


def test_depth_stamp_mismatch_returns_unknown():
    assert measure_person_range(DEPTH, BBOX, 1.0, 1.051) is None


def test_depth_stamp_boundary_is_inclusive():
    assert measure_person_range(DEPTH, BBOX, 1.0, 1.05) == pytest.approx(1.3)


@pytest.mark.parametrize("roi", [
    {**BBOX, "x2": 1}, {**BBOX, "x2": 5}, {**BBOX, "image_width": 3}
])
def test_bad_depth_roi_is_rejected(roi):
    with pytest.raises(ValueError):
        measure_person_range(DEPTH, roi, 1.0, 1.0)


def test_ragged_depth_frame_rejected():
    with pytest.raises(ValueError):
        measure_person_range([[1.0, 2.0], [3.0]], {"x1": 0, "y1": 0, "x2": 1, "y2": 1, "image_width": 2, "image_height": 2}, 1.0, 1.0)
