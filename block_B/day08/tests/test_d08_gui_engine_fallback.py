"""D08 GUI-only Ogre fallback contract (static L0; ROS/Gazebo not run)."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
LAUNCH = ROOT / "block_B/day04/run_student_gazebo_yolo_once.sh"
WRAPPER = ROOT / "block_B/day08/run_d08_student_live_once.sh"


def test_default_ogre2_is_unchanged_and_invalid_engine_is_rejected():
    s = LAUNCH.read_text()
    assert 'D08_GUI_ENGINE="${AXIA_D08_GUI_RENDER_ENGINE:-ogre2}"' in s
    assert 'ogre|ogre2)' in s
    assert 'D08_GUI_RENDER_ENGINE_INVALID' in s
    assert 'if [[ "$D08_GUI_ENGINE" == ogre ]]; then' in s


def test_ogre1_switch_is_only_on_gui_process_never_sensor_server():
    s = LAUNCH.read_text()
    assert 'D08_GUI_ENGINE_ARGS=(--render-engine ogre)' in s
    assert 'start_group gazebo_gui "${D08_RENDER_ENV[@]}" gz sim -g -v 4 "${D08_GUI_ENGINE_ARGS[@]}"' in s
    start = s.index("start_group gazebo_nav2")
    nav2 = s[start:s.index('if [[ "$D05_LIVE" == 1 ]]; then', start)]
    assert "render-engine" not in nav2
    assert "headless:=True" in s
    assert "D08_GAZEBO_GUI_RENDER_ENGINE=" in s
    assert "SERVER_ENGINE_UNCHANGED" in s


def test_ogre_fallback_never_changes_rgbd_or_unsafe_robot_control():
    s = LAUNCH.read_text()
    w = WRAPPER.read_text()
    assert "AXIA_D08_RGBD_RATE_HZ" in w
    assert "AXIA_D05_SENSOR_ONLY=1" in w
    assert "AXIA_D04_STUDENT_IMAGE_VIEW=0" in w
    assert "NO_GOAL NO_CMD_VEL" in w
    bounded = s[s.index("D08_GUI_ENGINE_ARGS=()"):s.index("start_group gazebo_gui")]
    for forbidden in ("ros2 topic pub", "send_goal(", "create_publisher(", "sudo apt", "MESA_GL_VERSION_OVERRIDE"):
        assert forbidden not in bounded


def test_shells_parse_without_ros_or_gazebo():
    for path in (LAUNCH, WRAPPER):
        r = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
        assert r.returncode == 0, r.stderr
