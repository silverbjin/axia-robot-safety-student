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
    # User-reported regression: at x=0.6m the person fills/clips the camera view.
    # Require a small upward pitch without altering camera_link or native RGB-D source.
    camera_pose = [float(x) for x in rgbd[0].findtext("pose").split()]
    assert len(camera_pose)==6
    assert -0.22 <= camera_pose[4] <= -0.12, "RED: D05 camera must look slightly upward for full-body person"
    assert abs(camera_pose[3]) < 1e-8 and abs(camera_pose[5]) < 1e-8

    assert tree.find(".//model[@name='axia_d05_rgbd_rig']") is None
    world_tree=ET.parse(out/"student_human_world.sdf.xacro")
    waypoints=world_tree.findall(".//actor[@name='axia_student_person']/script/trajectory/waypoint")
    assert len(waypoints)>=3
    poses=[list(map(float,w.findtext("pose").split())) for w in waypoints]
    xs=[pose[0] for pose in poses]
    assert max(xs)-min(xs)>=0.6,"Actor must approach and recede in camera forward direction"
    assert abs(xs[0]-xs[-1])<1e-6,"Loop should return to start"
    # Reference classroom D04 human is around world x≈2.8m.
    # New D05 approach should remain in a comparable forward range, not x=0.6.
    assert min(xs) >= 2.0, "RED: actor too close; cropped in YOLO image"
    assert max(xs) <= 3.3, "RED: actor should remain detectable with the same ONNX model"
    assert xs[0] > xs[1] and xs[-1] > xs[1], "Person approaches then recedes"

    assert all(abs(pose[1]+0.5)<1e-6 for pose in poses),"Actor stays in Waffle optical FOV"
    # The known-good D04 classroom scene (public 7c911f4...) used world z=1.0.
    # z=0.0 on this walk.dae sinks the person into the floor in Gazebo.
    assert all(abs(pose[2]-1.0)<1e-6 for pose in poses), (
        "RED: Actor root z=0 sinks the body below floor; restore reference z=1.0"
    )
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


def test_d05_owner_observes_real_distance_before_depth_loss():
    """Owner incident regression: previous GUI hold began AFTER Depth bridge killed.

    The public student sensor-only path stays unchanged. No ROS fake or private
    observer success is claimed by this source-level ordering contract.
    """
    script = RUNNER.read_text(encoding="utf-8")
    moving_pass = script.find("D05_LIVE_MOVING_VALID_PASS")
    show_start = script.find("D05_LIVE_DISTANCE_OBSERVATION_STARTED")
    topic_echo = script.find("ros2 topic echo /axia/d05/person_range_status --field data")
    show_done = script.find("D05_LIVE_DISTANCE_OBSERVATION_DONE")
    depth_kill = script.find('kill -TERM -- "-$DEPTH_PID"')
    loss_pass = script.find("D05_LIVE_VALID_TO_UNKNOWN_PASS")
    assert -1 not in (moving_pass, show_start, topic_echo, show_done, depth_kill, loss_pass), (
        "RED: D05 instructor distance display phase not implemented"
    )
    assert moving_pass < show_start < topic_echo < show_done < depth_kill < loss_pass, (
        "RED: instructor GUI distance observation must precede injected Depth loss"
    )
    assert 'D05_PUBLIC_SENSOR_ONLY_PASS' in script
    assert 'if [[ "$D05_LIVE" == 1 && "$D05_SENSOR_ONLY" != 1 ]]' in script
