"""PUBLIC RED→GREEN contract: student-independent ROS 2 Jazzy Gazebo/YOLO GUI.

No private Instructor source. This test only checks scene composition, CLI and
public launch contract. Public real Gazebo+YOLO CI is a separate verification.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"block_B/day04/gazebo_yolo"
SCENE=BASE/"prepare_scene.py"
RUNNER=ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh"
MONITOR=BASE/"verify_live.py"
GUIDE=ROOT/"block_B/day04/D04_STUDENT_LAB_GUIDE_KO.md"
RVIZ=BASE/"axia_d04_student.rviz"

def test_student_gazebo_entrypoint_and_no_private_access():
    assert RUNNER.is_file(), "RED: students have image-only Python demo; no Gazebo GUI path"
    script=RUNNER.read_text()
    assert subprocess.run(["bash","-n",str(RUNNER)]).returncode==0
    for word in ("--doctor","--run","--self-check","headless:=False","image_view",
                 "ros_gz_image","yolo_bringup","nav2_bringup","GZ_PARTITION",
                 "AXIA_D04_STUDENT_GUI","DISPLAY"):
        assert word in script,word
    for forbidden in ("gh auth", "axia-robot-safety-instructor", "axia_safety_supervisor",
                      "axia_fault_injector","axia_scenario_verifier","send_goal","cmd_vel pub"):
        assert forbidden not in script,forbidden
    run=subprocess.run(["bash",str(RUNNER),"--self-check"],text=True,capture_output=True,timeout=10)
    assert run.returncode==0,run.stdout+run.stderr
    assert "D04_STUDENT_GAZEBO_STATIC_PASS" in run.stdout
    assert "GAZEBO_NOT_RUN" in run.stdout

def test_official_source_overlay_without_private_p1(tmp_path):
    assert SCENE.is_file(),"RED: official Nav2 Waffle Pi Gazebo model composition missing"
    nav=tmp_path/"gz_waffle.sdf.xacro"
    nav.write_text('<sdf><model name="waffle"><link name="camera_link"><sensor name="depth" type="depth_camera"/></link></model></sdf>')
    pi=tmp_path/"pi.sdf"
    pi.write_text('<sdf><model><link><sensor name="camera" type="camera"><topic>camera/image_raw</topic><camera><image><width>640</width><height>480</height><format>R8G8B8</format></image></camera></sensor></link></model></sdf>')
    world=tmp_path/"tb3_sandbox.sdf.xacro"
    world.write_text('<sdf><world name="default"><plugin filename="gz-sim-sensors-system"><render_engine>ogre2</render_engine></plugin></world></sdf>')
    actor=tmp_path/"walk.dae"
    actor.write_text("public actor fixture")
    model=tmp_path/"yolo26n.onnx"
    model.write_text("public model fixture")
    dest=tmp_path/"scene"
    args=[sys.executable,str(SCENE),"--waffle",str(nav),"--pi",str(pi),"--world",str(world),"--actor",str(actor),"--model",str(model),"--out",str(dest)]
    result=subprocess.run(args,text=True,capture_output=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    bot=ET.parse(dest/"student_waffle_rgb.sdf.xacro")
    assert len(bot.findall(".//sensor"))==2
    assert bot.find(".//sensor[@name='axia_student_rgb']") is not None
    ww=ET.parse(dest/"student_human_world.sdf.xacro")
    actors=ww.findall(".//actor")
    assert len(actors)==1
    assert actors[0].get("name")=="axia_student_person"
    assert actors[0].find(".//trajectory/waypoint") is not None
    conf=(dest/"student_yolo.yaml").read_text()
    assert "/camera/image_raw" in conf and "yolo_ros/DetectionPlugin" in conf
    assert "yolo_ros/DebugPlugin" in conf and "provider: cpu" in conf
    assert "max_fps: 5" in conf
    manifest=json.loads((dest/"scene_manifest.json").read_text())
    assert manifest["sim_only"] is True and manifest["goal_sent"] is False
    assert manifest["visual_only_actor"] is True
    assert manifest["private_instructor_source"] is False

def test_fail_closed_missing_official_source(tmp_path):
    assert SCENE.is_file()
    p=subprocess.run([sys.executable,str(SCENE),"--waffle",str(tmp_path/"missing"),
                      "--pi",str(tmp_path/"missing"),"--world",str(tmp_path/"missing"),
                      "--actor",str(tmp_path/"missing"),"--model",str(tmp_path/"missing"),
                      "--out",str(tmp_path/"out")],capture_output=True,text=True)
    assert p.returncode!=0
    assert not (tmp_path/"out").exists()

def test_real_rviz_saved_view_and_live_verifier():
    assert RVIZ.is_file() and MONITOR.is_file()
    txt=RVIZ.read_text()
    for x in ("rviz_default_plugins/RobotModel","rviz_default_plugins/LaserScan",
              "rviz_default_plugins/TF","/camera/image_raw",
              "/yolo/cam0/debug_image","/odom"):
        assert x in txt,x
    mon=MONITOR.read_text()
    for x in ("DetectionArray","class_name","/camera/image_raw",
              "/yolo/cam0/detections","/scan","D04_STUDENT_PERSON_DETECTED"):
        assert x in mon,x
    for forbidden in ("publish(", "create_publisher(", "send_goal("):
        assert forbidden not in mon

def test_guide_has_gazebo_eyeballs_not_photo_only():
    txt=GUIDE.read_text()
    for s in ("run_student_gazebo_yolo_once.sh","Gazebo GUI",
              "YOLO", "Bounding Box","학생", "ROS_DOMAIN_ID",
              "visual-only", "비공개", "RViz"):
        assert s in txt,s
    assert "Python 단일 이미지" in txt


def test_jazzy_setup_is_sourced_before_ros2_cli_tool_discovery():
    """CI regression: ros:jazzy-ros-base-noble has no ros2 on PATH until setup."""
    script=RUNNER.read_text()
    assert script.index('source "$ROS_SETUP"') < script.index("for tool in ros2 gz xacro colcon")
    assert "D04_STUDENT_ROS_TOOL_MISSING_AFTER_SOURCE" in script
    assert "D04_STUDENT_INSTALL_OFFICIAL_TOOLS_AFTER_ROS_SOURCE" in script
