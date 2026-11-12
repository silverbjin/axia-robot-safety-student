"""D04 public CI regression for the EXACT teacher's optional single-image Python demo.

Tests inject a fake Ultralytics API. These are L0 API/data/CLI contracts only,
NOT real YOLO inference, ROS, Gazebo, Nav2 or any safety-stop validation.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "block_B" / "day04" / "yolo_single_image_demo.py"
# Exact Git blob of the original instructor-only NON-SOLUTION demo script.
TEACHER_SOURCE_BLOB = "9eb5fb41ea3836da5bade7fcdb3bce99969fc212"


def load_demo():
    spec = importlib.util.spec_from_file_location("d04_student_copy", DEMO)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_teacher_demo_copy_is_byte_identical_and_contains_no_solutions():
    assert DEMO.is_file(), "RED: instructor YOLO demo is not yet shared with students"
    raw = DEMO.read_bytes()
    git_blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    assert git_blob == TEACHER_SOURCE_BLOB, "Student sample must match shared teacher demo"
    assert b"select_person" not in raw and b"measure_person_range" not in raw
    assert b"cmd_vel" not in raw and b"rclpy" not in raw


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class FakeResult:
    orig_shape = (480, 640)

    class Boxes:
        cls = FakeTensor([0, 56])
        conf = FakeTensor([0.92, 0.97])
        xyxy = FakeTensor([[100.8, 50.5, 250.1, 300.9], [0, 0, 100, 100]])

    boxes = Boxes()


class FakeYOLO:
    names = {0: "person", 56: "chair"}

    def __init__(self, model):
        self.model = model

    def predict(self, **kwargs):
        assert kwargs["device"] == "cpu"
        assert kwargs["save"] is False
        assert kwargs["verbose"] is False
        assert Path(kwargs["source"]).is_file()
        return [FakeResult()]


def test_teacher_demo_identical_script_produces_expected_csv_and_manifest(tmp_path, monkeypatch, capsys):
    fake = types.ModuleType("ultralytics")
    fake.YOLO = FakeYOLO
    monkeypatch.setitem(sys.modules, "ultralytics", fake)
    model, picture = tmp_path / "allowed.pt", tmp_path / "image.jpg"
    model.write_bytes(b"CI mock model: NOT an inference weight")
    picture.write_bytes(b"CI mock image: NOT a photograph")
    out = tmp_path / "out"
    assert load_demo().main(["--model", str(model), "--image", str(picture), "--out", str(out)]) == 0
    with (out / "detections.csv").open(newline="") as stream:
        detections = list(csv.DictReader(stream))
    assert len(detections) == 1
    assert detections[0]["category"] == "person"
    assert detections[0]["frame_id"] == "instructor-local-image"
    assert float(detections[0]["confidence"]) == pytest.approx(0.92)
    assert tuple(int(detections[0][key]) for key in ("x1", "y1", "x2", "y2")) == (100, 50, 250, 300)
    assert (int(detections[0]["image_width"]), int(detections[0]["image_height"])) == (640, 480)
    metadata = json.loads((out / "run_manifest.json").read_text())
    assert metadata["image_sha256"] == hashlib.sha256(picture.read_bytes()).hexdigest()
    assert metadata["model_sha256"] == hashlib.sha256(model.read_bytes()).hexdigest()
    assert metadata["detections"] == 1 and metadata["level"] == "LOCAL_YOLO_CPU_ONLY"
    assert metadata["ros_verified"] is False and metadata["gazebo_verified"] is False
    assert "LOCAL_YOLO_CPU_ONLY: 1 persons;" in capsys.readouterr().out


def test_missing_assets_fail_closed_without_artifacts(tmp_path):
    out = tmp_path / "no-output"
    with pytest.raises(SystemExit) as exc:
        load_demo().main([
            "--model", str(tmp_path / "not-downloaded.pt"),
            "--image", str(tmp_path / "not-downloaded.jpg"),
            "--out", str(out),
        ])
    assert exc.value.code == 2
    assert not out.exists()


def test_existing_output_is_not_overwritten(tmp_path):
    out = tmp_path / "existing"
    out.mkdir()
    (out / "keep.txt").write_text("DO NOT DELETE")
    model, picture = tmp_path / "ready.pt", tmp_path / "ready.jpg"
    model.write_bytes(b"mock")
    picture.write_bytes(b"mock")
    with pytest.raises(SystemExit) as exc:
        load_demo().main([
            "--model", str(model), "--image", str(picture), "--out", str(out)
        ])
    assert exc.value.code == 2
    assert (out / "keep.txt").read_text() == "DO NOT DELETE"


def test_student_guide_explains_actual_model_vs_fixture_and_exact_command():
    guide = (ROOT / "block_B/day04/D04_STUDENT_LAB_GUIDE_KO.md").read_text()
    assert "block_B/day04/yolo_single_image_demo.py" in guide
    assert "yolo26n.pt" in guide
    assert "bus.jpg" in guide
    assert "LOCAL_YOLO_CPU_ONLY" in guide
    assert "SYNTHETIC_COURSE_FIXTURE" in guide
    assert "AGPL-3.0" in guide
    assert "강사 정답" in guide
