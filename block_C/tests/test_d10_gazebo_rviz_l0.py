"""D10 Gazebo/RViz2 synthetic education overlay pure L0 contract.

No ROS runtime, Gazebo GUI, robot goal, sensor/Guard TTL or Safety proof.
"""
from pathlib import Path
import importlib.util
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "day10/live"
D08 = ROOT.parent / "block_B/day08/run_d08_student_live_once.sh"

def _load(name):
    p = LIVE / name
    spec = importlib.util.spec_from_file_location(p.stem, p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _valid():
    return {
        "trace_id": "TST_A_00",
        "event_id": "D10_ISOLATION_FOREST:TST_A_00:5",
        "source_timestamp_ns": "5900000000",
        "model_id": "D10_ISOLATION_FOREST",
        "control_authority": "False",
        "certified_estop": "False",
        "risk_score": "0.10201593",
        "threshold": "0.10199750",
    }

def test_d10_warning_is_marked_synthetic_not_an_estop():
    m = _load("d10_if_rviz_marker.py")
    actual = m.format_education_status(
        "EDUCATION ONLY / NON-CERTIFIED: WARNING",
        "SYNTHETIC_NO_HARDWARE", _valid().items()
    )
    assert actual and actual[1] == "red"
    assert "TST_A_00 W5 t=5.9s | WARNING" in actual[0]
    assert "NO ROBOT CONTROL" in actual[0]
    assert "NOT AN E-STOP" in actual[0]

def test_d10_rejects_hardware_or_control_authority_disguise():
    m = _load("d10_if_rviz_marker.py")
    q = _valid()
    q["control_authority"] = "True"
    assert m.format_education_status("EDUCATION ONLY / NON-CERTIFIED: WARNING",
                                     "SYNTHETIC_NO_HARDWARE", q.items()) is None
    q = _valid()
    assert m.format_education_status("EDUCATION ONLY / NON-CERTIFIED: WARNING",
                                     "robot", q.items()) is None
    assert m.format_education_status("WARNING", "SYNTHETIC_NO_HARDWARE",
                                     q.items()) is None
    q["model_id"] = "CPU_TORCH_AE"
    assert m.format_education_status("EDUCATION ONLY / NON-CERTIFIED: WARNING",
                                     "SYNTHETIC_NO_HARDWARE", q.items()) is None

def test_d10_quality_has_no_anomaly_score():
    m = _load("d10_if_rviz_marker.py")
    q = _valid()
    q["risk_score"] = ""
    q["threshold"] = ""
    v = m.format_education_status("EDUCATION ONLY / NON-CERTIFIED: INSUFFICIENT_DATA",
                                  "SYNTHETIC_NO_HARDWARE", q.items())
    assert v is not None and v[1] == "gray"
    assert "NO SCORE / QUALITY INVALID" in v[0]
    q["risk_score"] = "0.12"
    assert m.format_education_status("EDUCATION ONLY / NON-CERTIFIED: INSUFFICIENT_DATA",
                                     "SYNTHETIC_NO_HARDWARE", q.items()) is None

def test_d10_rviz_overlay_preserves_d08_view_and_adds_one_marker():
    m = _load("build_d10_rviz_overlay.py")
    source = (ROOT.parent / "block_B/day08/live/d08_student_rgbd_monitor.rviz").read_text()
    out = m.build_profile(source)
    assert out.count("rviz_default_plugins/Marker") == 1
    assert m.MARKER_TOPIC in out
    assert source not in ("", out)
    assert "/scan" in out and "/odom" in out and "RobotModel" in out
    assert "Description Source: Topic" in out
    assert source.count("D10 SYNTHETIC IF") == 0

def test_d10_bash_selfcheck_and_existing_d08_default_retained():
    outer = LIVE / "d10_gazebo_rviz_once.sh"
    assert subprocess.run(["bash", "-n", str(outer)], capture_output=True).returncode == 0
    assert subprocess.run(["bash", "-n", str(D08)], capture_output=True).returncode == 0
    v = subprocess.run(["bash", str(outer), "--self-check"], capture_output=True, text=True)
    assert v.returncode == 0, v.stderr
    assert "NO_ROS_NO_GAZEBO_NO_CONTROL" in v.stdout
    d08 = D08.read_text()
    assert "AXIA_D08_MONITOR_RVIZ:-$HERE/live/d08_student_rgbd_monitor.rviz" in d08

def test_d10_scripts_never_write_motion_or_safety_control():
    src = "\n".join(p.read_text() for p in LIVE.glob("*") if p.suffix in (".py", ".sh"))
    assert "create_publisher(Twist" not in src
    assert "send_goal_async(" not in src
    assert "set_parameters_atomically(" not in src
    assert "collision_monitor" not in src.lower()
