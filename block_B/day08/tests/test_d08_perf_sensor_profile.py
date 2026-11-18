"""D08 RTF performance candidate. L0 fixture only, never claim Gazebo speedup.

One independent variable: registered RGBD sensor's simulated update_rate
30Hz (original) versus 10Hz (D08-only opt-in). 640x480, all topics,
Actor trajectory, LiDAR, physics and YOLO remain unchanged.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
SCENE=ROOT/"block_B/day05/gazebo_live/prepare_scene.py"
D04=ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh"
D08=ROOT/"block_B/day08/run_d08_student_live_once.sh"

def _fixture(tmp_path):
    nav=tmp_path/"gz_waffle.sdf.xacro"
    nav.write_text('<sdf><model name="waffle"><link name="camera_link"><sensor name="depth" type="depth_camera"/></link></model></sdf>')
    pi=tmp_path/"pi.sdf"
    pi.write_text('<sdf><model><link><sensor name="camera" type="camera"><topic>camera/image_raw</topic><update_rate>30</update_rate><camera><image><width>640</width><height>480</height><format>R8G8B8</format></image></camera></sensor></link></model></sdf>')
    world=tmp_path/"world.sdf.xacro"
    world.write_text('<sdf xmlns:xacro="http://www.ros.org/wiki/xacro"><xacro:arg name="headless" default="true"/><world name="default"><plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/><xacro:unless value="$(arg headless)"><plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/></xacro:unless><plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin></world></sdf>')
    actor=tmp_path/"walk.dae";actor.write_text("fixture")
    model=tmp_path/"yolo.onnx";model.write_text("fixture")
    return ["--waffle",str(nav),"--pi",str(pi),"--world",str(world),
            "--actor",str(actor),"--model",str(model)]

def _build(tmp_path,rate=None):
    out=tmp_path/("rgbd_default" if rate is None else f"rgbd_{rate}")
    cmd=[sys.executable,str(SCENE),*_fixture(tmp_path),"--out",str(out)]
    if rate is not None:
        cmd+=["--d08-rgbd-rate-hz",str(rate)]
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=15)
    return p,out

def test_rgbd_rate_d08_only_with_exact_same_topics_and_actor(tmp_path):
    before,base=_build(tmp_path)
    after,opt=_build(tmp_path,10)
    assert before.returncode==0,before.stderr
    assert after.returncode==0,after.stderr
    def sensor(path):
        root=ET.parse(path/"student_waffle_rgb.sdf.xacro")
        return root.find(".//sensor[@name='axia_d05_registered_rgbd']")
    a,b=sensor(base),sensor(opt)
    assert a.findtext("update_rate")=="30"
    assert b.findtext("update_rate")=="10"
    assert a.findtext("topic")==b.findtext("topic")=="axia/d05/rgbd"
    assert a.findtext("gz_frame_id")==b.findtext("gz_frame_id")
    assert ET.tostring(a.find("camera/image"))==ET.tostring(b.find("camera/image"))
    world_a=ET.parse(base/"student_human_world.sdf.xacro")
    world_b=ET.parse(opt/"student_human_world.sdf.xacro")
    assert ET.tostring(world_a.getroot())==ET.tostring(world_b.getroot())
    assert (base/"student_yolo.yaml").read_text()==(opt/"student_yolo.yaml").read_text()

def test_invalid_rate_fails_closed(tmp_path):
    bad,out=_build(tmp_path,2)
    assert bad.returncode!=0
    assert not (out/"student_waffle_rgb.sdf.xacro").exists()

def test_launcher_only_d08_opt_in_rate_and_backwards_compat():
    d04=D04.read_text()
    d08=D08.read_text()
    assert 'AXIA_D08_RGBD_RATE_HZ' in d08
    assert '--d08-rgbd-rate-hz' in d04
    assert 'AXIA_D08_STAGED_GUI' in d04
    assert 'AXIA_D08_RGBD_RATE_HZ_INVALID' in d04
    assert 'AXIA_D08_RGBD_RATE_PROFILE' in d08
    assert subprocess.run(["bash","-n",str(D04)]).returncode==0
    assert subprocess.run(["bash","-n",str(D08)]).returncode==0
    for forbidden in ("send_goal(", "cmd_vel pub", "FaultInjector"):
        assert forbidden not in d08
