"""D05 minimal Gazebo live variant contract: RED before scene adapter exists."""
from pathlib import Path
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"block_B/day05/gazebo_live/prepare_scene.py"
RUNNER=ROOT/"block_B/day04/run_student_gazebo_yolo_once.sh"


def test_live_variant_mounts_one_registered_rgbd_on_waffle(tmp_path):
    assert SCRIPT.is_file(), "RED: D05 mounted-camera variant missing"
    nav=tmp_path/"gz_waffle.sdf.xacro"
    nav.write_text('<sdf><model name="waffle"><link name="camera_link"><sensor name="depth" type="depth_camera"/></link></model></sdf>')
    pi=tmp_path/"pi.sdf"
    pi.write_text('<sdf><model><link><sensor name="camera" type="camera"><topic>camera/image_raw</topic><camera><image><width>640</width><height>480</height><format>R8G8B8</format></image></camera></sensor></link></model></sdf>')
    world=tmp_path/"world.sdf.xacro"
    world.write_text('<sdf><world name="default"><plugin filename="gz-sim-sensors-system"><render_engine>ogre2</render_engine></plugin></world></sdf>')
    actor=tmp_path/"walk.dae";actor.write_text("fixture only")
    model=tmp_path/"yolo26n.onnx";model.write_text("fixture only")
    out=tmp_path/"d05"
    command=[sys.executable,str(SCRIPT),"--waffle",str(nav),"--pi",str(pi),"--world",str(world),"--actor",str(actor),"--model",str(model),"--out",str(out)]
    p=subprocess.run(command,text=True,capture_output=True,timeout=10)
    assert p.returncode==0,p.stdout+p.stderr
    tree=ET.parse(out/"student_waffle_rgb.sdf.xacro")
    rgbd=tree.findall(".//model/link[@name='camera_link']/sensor[@type='rgbd_camera']")
    assert len(rgbd)==1, "Only one registered D05 RGB-D on mounted camera_link"
    assert rgbd[0].findtext("topic")=="axia/d05/rgbd"
    assert rgbd[0].findtext("gz_frame_id")=="axia_d05_rgbd_optical"
    assert tree.find(".//model[@name='axia_d05_rgbd_rig']") is None
    world_tree=ET.parse(out/"student_human_world.sdf.xacro")
    waypoints=world_tree.findall(".//actor[@name='axia_student_person']/script/trajectory/waypoint")
    assert len(waypoints)>=3
    poses=[list(map(float,w.findtext("pose").split())) for w in waypoints]
    xs=[pose[0] for pose in poses]
    assert max(xs)-min(xs)>=0.6,"Actor must approach and recede in camera forward direction"
    assert abs(xs[0]-xs[-1])<1e-6,"Loop should return to start"
    assert all(abs(pose[1]+0.5)<1e-6 for pose in poses),"Actor stays in Waffle optical FOV"
    conf=(out/"student_yolo.yaml").read_text()
    assert "rgb_topic: /axia/d05/rgbd/image" in conf
    meta=json.loads((out/"scene_manifest.json").read_text())
    assert meta["camera_topic"]=="/axia/d05/rgbd/image"
    assert meta["depth_topic"]=="/axia/d05/rgbd/depth_image"
    assert meta["goal_sent"] is False and meta["visual_only_actor"] is True


def test_existing_d04_entrypoint_is_opt_in_only():
    txt=RUNNER.read_text()
    assert "AXIA_D05_LIVE" in txt,"RED: D04 runner missing default-off D05 variant"
    assert "GAZEBO_NOT_RUN" in txt
    assert "headless:=False" in txt
    assert "image_view" in txt
    for forbidden in ("send_goal(", "Twist(", "cmd_vel pub", "gh auth"):
        assert forbidden not in txt
