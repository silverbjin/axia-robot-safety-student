"""Owner WSL2 AMENT_TRACE_SETUP_FILES regression: exact former copy/paste failure.

This does NOT assert a real WSL2 GUI pass. It asserts shell handoff,
nounset isolation and safe preservation prior to a real Gazebo launch.
"""
import os
from pathlib import Path
import subprocess

DAY = Path(__file__).resolve().parents[1]
LAUNCH = DAY / "run_d08_student_live_once.sh"
BOOT = DAY / "run_d08_student_live_bootstrap.sh"
GUIDE = DAY / "D08_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md"

def _run(script, env=None):
    return subprocess.run(["bash", "-c", script], capture_output=True,
                          text=True, timeout=20, env=env)

def test_reproduce_original_ros_setup_unbound_trace(tmp_path):
    # Deterministic ROS-generated-style setup: missing optional AMENT variable
    # under set -u fails BEFORE any gazebo/rviz starts.
    ros = tmp_path / "setup.bash"
    ros.write_text(': "$AMENT_TRACE_SETUP_FILES"\n', encoding="utf-8")
    env = os.environ.copy()
    env.pop("AMENT_TRACE_SETUP_FILES", None)
    first = _run(f'set -Eeuo pipefail; source "{ros}"', env)
    assert first.returncode != 0
    assert "AMENT_TRACE_SETUP_FILES: unbound variable" in first.stderr
    guarded = _run(f'set -Eeuo pipefail; set +u; source "{ros}"; set -u; echo ROS_SAFE_SETUP', env)
    assert guarded.returncode == 0
    assert "ROS_SAFE_SETUP" in guarded.stdout

def test_release_entrypoint_is_one_command_without_ros_source_in_caller():
    assert BOOT.is_file(), "RED: missing WSL2 one-command owner bootstrap"
    text = BOOT.read_text(encoding="utf-8")
    assert "run_d08_student_live_once.sh" in text
    assert "D08_STUDENT_BOOTSTRAP_STATIC_PASS" in text
    assert "git clone" in text and "merge --ff-only" in text
    assert "source /opt/ros/jazzy/setup.bash" not in text
    assert "--self-check" in text and "--doctor" in text and "--run" in text
    assert subprocess.run(["bash", "-n", str(BOOT)],capture_output=True).returncode == 0
    out = subprocess.run(["bash", str(BOOT), "--self-check"],
                         capture_output=True,text=True,timeout=10)
    assert out.returncode == 0, out.stderr
    assert "D08_STUDENT_BOOTSTRAP_STATIC_PASS" in out.stdout

def test_student_copy_paste_guide_replaces_original_nounset_trap():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "AMENT_TRACE_SETUP_FILES" in guide
    assert "run_d08_student_live_bootstrap.sh" in guide
    # Original single-block command: set -Eeuo pipefail then plain source -> failure.
    import re
    blocks = re.findall(r"(?ms)^\x60\x60\x60bash\n(.*?)\n\x60\x60\x60",guide)
    assert blocks
    first = blocks[0]
    assert "run_d08_student_live_bootstrap.sh" in first
    assert "source /opt/ros/jazzy/setup.bash" not in first
    assert "git reset --hard" not in first
    assert "rm -rf" not in first

def test_inner_ros_setup_turns_off_nounset_only_for_source():
    live = LAUNCH.read_text(encoding="utf-8")
    assert 'set +u\nsource "$ROS_SETUP"\nset -u' in live
