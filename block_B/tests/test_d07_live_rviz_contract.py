"""D07 live Gazebo/RViz2 observation contract; student never owns robot Goal."""
from pathlib import Path
import subprocess

BASE=Path(__file__).resolve().parents[1]
D07=BASE/"day07"
RVIZ=D07/"live/d07_student_nav2_observer.rviz"
RUN=D07/"run_d07_student_gazebo_rviz_once.sh"
BOOT=D07/"run_d07_student_live_bootstrap.sh"
GUIDE=D07/"D07_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md"

def test_d07_rviz_actual_sensor_observation_and_optional_nav2():
    s=RVIZ.read_text(encoding="utf-8")
    for token in ("Fixed Frame: odom", "rviz_default_plugins/LaserScan",
                  "rviz_default_plugins/Odometry", "rviz_default_plugins/TF",
                  "/scan", "/odom", "rviz_default_plugins/Map",
                  "/global_costmap/costmap", "rviz_default_plugins/Path"):
        assert token in s, token
    # Nav2 costmap and Path are NOT active with D08 visual-only Actor.
    for dangerous in ("rviz_default_plugins/GoalTool",
                      "rviz_default_plugins/InitialPose",
                      "rviz_default_plugins/PublishPoint",
                      "rviz_default_plugins/SetGoal",
                      "/cmd_vel", "/navigate_to_pose/_action/send_goal"):
        assert dangerous not in s, dangerous
    assert "H01" in s and "NO_GOAL" in s

def test_d07_launcher_delegates_existing_proven_gazebo_owner_and_rviz():
    s=RUN.read_text(encoding="utf-8")
    for token in ("--self-check", "--doctor", "--run",
                  "AXIA_D04_STUDENT_RVIZ_CONFIG", "AXIA_D04_STUDENT_RVIZ=1",
                  "AXIA_D05_SENSOR_ONLY=1", "AXIA_D04_STUDENT_GUI=1",
                  "AXIA_D07_DOMAIN_ID", "D07_STUDENT_NO_GOAL",
                  "D07_RVIZ2_REQUIRED", "run_student_gazebo_yolo_once.sh"):
        assert token in s, token
    assert "YES-P2-G07-GOAL" not in s
    assert "ros2 topic pub /cmd_vel" not in s
    assert "NavigateToPose.Goal" not in s
    assert subprocess.run(["bash","-n",str(RUN)]).returncode==0
    cp=subprocess.run(["bash",str(RUN),"--self-check"],text=True,capture_output=True)
    assert cp.returncode==0,(cp.stdout,cp.stderr)
    assert "GAZEBO_NOT_RUN" in cp.stdout and "RVIZ_NOT_RUN" in cp.stdout

def test_d07_immutable_source_bootstrap_preserves_existing_student_work():
    s=BOOT.read_text(encoding="utf-8")
    for token in ("AXIA_D07_PUBLIC_SHA",'git -C "$DIR" fetch','git -C "$DIR" checkout',
                  "git status --porcelain", "D07_SOURCE_SHA_MISMATCH",
                  "run_d07_student_gazebo_rviz_once.sh", "--self-check",
                  "--doctor", "--run"):
        assert token in s, token
    for forbidden in ("git reset --hard", "rm -rf \"$HOME\"",
                      "sudo wsl --shutdown", "YES-P2-G07-GOAL"):
        assert forbidden not in s
    assert subprocess.run(["bash","-n",str(BOOT)]).returncode==0

def test_d07_live_guide_labels_visual_only_actor_not_true_h01_planning():
    s=GUIDE.read_text(encoding="utf-8")
    for token in ("Gazebo Harmonic", "RViz2", "Waffle", "main",
                  "visual-only", "H01", "Gate 1", "L2",
                  "Scan", "Costmap", "Path", "NOT_RUN", "BLOCKED",
                  "D07_STUDENT_NO_GOAL", "AXIA_D07_PUBLIC_SHA",
                  "run_d07_student_live_bootstrap.sh",
                  "연구", "터미널"):
        assert token in s,token
    assert "실제 회피 주행 PASS" not in s
