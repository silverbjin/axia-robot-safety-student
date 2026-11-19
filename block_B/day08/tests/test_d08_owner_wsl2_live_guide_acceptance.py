"""D08 documentation regression from actual Owner WSL2 Gazebo RGBD YOLO run.

This test checks evidence fidelity and safe copy-paste instructions, not WSLg pixels
or hardware/moving robot safety. No real ROS launch in this L0 test.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "D08_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md"
V2 = ROOT / "D08_STUDENT_DEMO_GUIDE_V2_20261115_KO.md"
RUN = ROOT / "run_d08_student_live_bootstrap.sh"

def test_student_owner_field_success_log_is_recorded_without_safety_promotion():
    doc = LIVE.read_text(encoding="utf-8")
    for marker in (
        "OWNER_WSL2_SENSOR_LIVE_PASS",
        "6a007eafa36957f17dc3e57e1a2e4acf3f3af5bd",
        "registered_rgbd_pairs", "9",
        "rgb_frames", "11", "depth_frames", "13",
        "yolo_frames", "4", "person_count", "2",
        "bbox_area_span", "0.2539007134522838",
        "D05_PUBLIC_SENSOR_ONLY_PASS",
        "D04_STUDENT_EXIT_CODE=0",
        "RVIZ_PANEL_VISUAL_NOT_VERIFIED",
        "PRIVATE_D05_RANGE_NOT_RUN",
        "NO_GOAL", "visual-only",
    ):
        assert marker in doc, marker

def test_no_misleading_live_success_claims():
    doc = LIVE.read_text(encoding="utf-8")
    assert "min_distance_m" in doc
    assert "null" in doc
    assert "valid_samples" in doc
    assert "0" in doc
    assert "not found:" in doc
    assert "local_setup.bash" in doc
    assert "E-Stop" in doc
    assert "Owner WSL2" in doc
    assert "RViz2" in doc

def test_student_execution_is_main_based_nounset_safe_and_no_destructive_reset():
    doc = LIVE.read_text(encoding="utf-8")
    first = re.search(r"(?ms)^\x60\x60\x60bash\n(.*?)\n\x60\x60\x60", doc)
    assert first is not None
    command = first.group(1)
    assert "run_d08_student_live_bootstrap.sh" in command
    assert "axia-robot-safety-student/main/block_B/day08/run_d08_student_live_bootstrap.sh" in command
    assert "AXIA_D08_RELEASE_BRANCH=main" in command
    assert "AXIA_D08_DEMO_DIR=" in command
    assert "source /opt/ros/jazzy/setup.bash" not in command
    assert "rm -rf" not in command and "git reset --hard" not in command
    assert "AXIA_D08_DOMAIN_ID=49" in command
    assert RUN.is_file()
    v2 = V2.read_text(encoding="utf-8")
    assert "D08_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md" in v2
