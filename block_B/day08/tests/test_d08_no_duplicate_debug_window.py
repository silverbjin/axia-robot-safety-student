"""D08 RViz-only YOLO visualization regression from actual Owner RTF 0.0079.

L0 contract; does not assert RTF recovery or GUI performance.
"""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
D08=ROOT/"block_B/day08/run_d08_student_live_once.sh"
D04=ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh"
CI=ROOT/".github/workflows/d08-student-gazebo-rviz-l2.yml"
RVIZ=ROOT/"block_B/day08/live/d08_student_rgbd_monitor.rviz"

def test_d08_disables_redundant_standalone_yolo_debug_window():
    content=D08.read_text(encoding="utf-8")
    assert "export AXIA_D04_STUDENT_IMAGE_VIEW=0" in content
    assert 'export AXIA_D04_STUDENT_RVIZ=1' in content
    assert "/yolo/cam0/debug_image" in RVIZ.read_text(encoding="utf-8")

def test_d04_default_remains_compatible_but_skip_is_real():
    script=D04.read_text(encoding="utf-8")
    assert 'AXIA_D04_STUDENT_IMAGE_VIEW:-1' in script
    assert "D04_STUDENT_IMAGE_VIEW_INVALID" in script
    assert 'if [[ "$SHOW_IMAGE_VIEW" == 1 ]]; then' in script
    assert "start_group image_view ros2 run image_view image_view" in script
    assert "D08_DEBUG_IMAGE_WINDOW_SKIPPED RVIZ_YOLO_DEBUG_IMAGE_ENABLED" in script
    assert subprocess.run(["bash","-n",str(D04)],capture_output=True).returncode==0
    assert subprocess.run(["bash","-n",str(D08)],capture_output=True).returncode==0

def test_l2_checks_2_windows_and_fails_if_redundant_image_view_started():
    ci=CI.read_text(encoding="utf-8")
    assert "D08_GAZEBO_RVIZ_TWO_WINDOWS_PASS" in ci
    assert "D08_IMAGE_VIEW_PROCESS_FORBIDDEN" in ci
    assert "D08_DEBUG_IMAGE_WINDOW_SKIPPED" in ci
    assert "D05_PUBLIC_SENSOR_ONLY_PASS" in ci
    assert "D08_RVIZ_MESH_RESOURCE_ERRORS_NONE_PASS" in ci
    assert "D08_GZ_SCENE_BROADCASTER_POSE_GATE_PASS" in ci
    assert "D08_RTF_PERFORMANCE_NOT_VERIFIED" in ci
