"""Regression for ROS 2 Jazzy launch_testing pytest auto-discovery in WSL2.

Public CI reproduces a pytest11 entry point importing yaml from outside the
student's minimal venv. Student fixture tests should isolate auto-plugins,
NOT install all of ROS or modify its package dependencies.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "block_B/day04/run_student_fixture_once.sh"
GUIDE = ROOT / "block_B/day04/D04_STUDENT_LAB_GUIDE_KO.md"
YOLO_RUNNER = ROOT / "block_B/day04/run_teacher_yolo_demo_once.sh"

def injected_ros_pytest11_plugin(tmp_path: Path) -> dict[str, str]:
    # pip-installed ROS launch_testing registers pytest11. Emulate entry-point
    # import failing on yaml without needing Gazebo or private instructor.
    (tmp_path / "bad_ros_launch_testing.py").write_text(
        "raise ModuleNotFoundError(\"No module named 'yaml'\")\n",
        encoding="utf-8",
    )
    info = tmp_path / "d04_broken_launch_testing-0.0.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: d04-broken-launch-testing\nVersion: 0.0.0\n",
        encoding="utf-8",
    )
    (info / "entry_points.txt").write_text(
        "[pytest11]\nros_launch_testing_mock = bad_ros_launch_testing\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    return env

def test_red_public_repro_ros_plugin_breaks_plain_student_pytest(tmp_path):
    env = injected_ros_pytest11_plugin(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "block_B/tests/test_fixture_io.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=15,
    )
    assert proc.returncode != 0
    assert "No module named 'yaml'" in proc.stderr
    # The user's first error is collection/startup, NOT fixture integrity.
    assert "4 passed" not in proc.stdout

def test_green_student_fixture_wrapper_ignores_ros_auto_plugins(tmp_path):
    env = injected_ros_pytest11_plugin(tmp_path)
    assert RUNNER.is_file(), "RED: no ROS-independent student fixture runner"
    proc = subprocess.run(
        ["bash", str(RUNNER), "--fixture"], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "4 passed" in proc.stdout
    assert "D04_FIXTURE_ISOLATED_PASS" in proc.stdout
    assert "No module named 'yaml'" not in proc.stderr

def test_guide_has_drop_in_recovery_for_both_existing_user_checkouts():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1" in guide
    assert "run_student_fixture_once.sh --fixture" in guide
    assert "axia-robot-safety-student-d04" in guide
    assert "axia_d04_student_yolo" in guide
    assert "이미 clone" in guide or "이미 내려받" in guide
    assert "No module named 'yaml'" in guide
    assert "LOCAL_YOLO_CPU_ONLY" in guide

def test_yolo_install_prefers_cpu_wheels_before_ultralytics():
    text = YOLO_RUNNER.read_text(encoding="utf-8")
    cpu = "https://download.pytorch.org/whl/cpu"
    assert cpu in text, "RED: pip installs large CUDA PyTorch dependencies for CPU-only lab"
    assert text.index(cpu) < text.index('"ultralytics==$ULTRALYTICS_VERSION"')
    assert "from ultralytics import YOLO" in text
    assert "AXIA_D04_STUDENT_PYTHON" in text
