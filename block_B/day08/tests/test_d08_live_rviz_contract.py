"""D08 live Gazebo + RViz read-only GUI TDD contract.

L0 only: does not prove actual Gazebo, RViz or WSLg execution.
"""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
D08=ROOT/"block_B/day08"
LAUNCH=D08/"run_d08_student_live_once.sh"
RVIZ=D08/"live/d08_student_rgbd_monitor.rviz"
GUIDE=D08/"D08_GAZEBO_RVIZ_LIVE_GUIDE_20261115_KO.md"
UPSTREAM=ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh"

def test_live_wrapper_and_rviz_source_exist():
    assert LAUNCH.is_file()
    assert RVIZ.is_file()
    assert GUIDE.is_file()

def test_readonly_wrapper_reuses_proven_d04_d05_and_sets_correct_rviz():
    script=LAUNCH.read_text(encoding="utf-8")
    assert subprocess.run(["bash","-n",str(LAUNCH)],capture_output=True).returncode==0
    for text in ("--self-check","--doctor","--run","AXIA_D05_LIVE=1",
                 "AXIA_D05_SENSOR_ONLY=1","AXIA_D04_STUDENT_RVIZ=1",
                 "AXIA_D04_STUDENT_RVIZ_CONFIG","AXIA_D04_STUDENT_DOMAIN_ID",
                 "run_student_gazebo_yolo_once.sh"):
        assert text in script,text
    assert UPSTREAM.is_file()
    assert "AXIA_D04_STUDENT_RVIZ_CONFIG" in UPSTREAM.read_text()
    for forbidden in ("send_goal", "cmd_vel pub", "create_publisher(", "axia-robot-safety-instructor",
                      "axia_safety_supervisor", "FaultInjector", "YES-P2-G07-GOAL"):
        assert forbidden not in script

def test_rviz_displays_actual_d05_topics_not_d04_camera_fallback():
    config=RVIZ.read_text(encoding="utf-8")
    for value in ("rviz_default_plugins/LaserScan","rviz_default_plugins/RobotModel",
                  "rviz_default_plugins/TF","rviz_default_plugins/Odometry",
                  "/scan","/odom","/robot_description",
                  "/axia/d05/rgbd/image","/axia/d05/rgbd/depth_image",
                  "/yolo/cam0/debug_image","Fixed Frame: odom"):
        assert value in config,value
    assert "/camera/image_raw" not in config
    # No interactive 2D Pose Estimate or 2D Nav Goal tools.
    assert "SetInitialPose" not in config
    assert "SetGoal" not in config
    assert "PublishPoint" not in config

def test_self_check_does_not_require_ros_or_gazebo():
    p=subprocess.run(["bash",str(LAUNCH),"--self-check"],
                     capture_output=True,text=True,timeout=20)
    assert p.returncode==0,p.stdout+p.stderr
    assert "D08_LIVE_RVIZ_STATIC_PASS" in p.stdout
    assert "GAZEBO_NOT_RUN" in p.stdout
    assert "RVIZ_NOT_RUN" in p.stdout

def test_guide_has_real_vs_synthetic_monitoring_and_future_work():
    text=GUIDE.read_text(encoding="utf-8")
    for marker in ("AXIA_D08_DOMAIN_ID","/axia/d05/rgbd/image",
                   "/axia/d05/rgbd/depth_image","/yolo/cam0/detections",
                   "RViz2","Collision Monitor","visual-only","NO_GOAL",
                   "PYTHON_ONLY","ros2 bag record","D08_STUDENT_LIVE",
                   "NOT_VERIFIED","150ms","Ctrl+C"):
        assert marker in text,marker
