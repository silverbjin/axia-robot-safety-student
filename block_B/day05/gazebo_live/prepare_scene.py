#!/usr/bin/env python3
"""D05-only variant of the existing D04 official Waffle scene; no new algorithm.

Exactly two changes in the scene output:
  1. Convert D04's camera_link RGB sensor to one registered RGB-D sensor.
  2. Make the existing visual actor approach and recede along camera forward X.
Do not change upstream Nav2/ROBOTIS files or original D04 outputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "day04" / "gazebo_yolo"))
from prepare_scene import compose as compose_d04  # reuse exact D04 overlay


RGB = "/axia/d05/rgbd/image"
DEPTH = "/axia/d05/rgbd/depth_image"
TOPIC = "axia/d05/rgbd"
FRAME = "axia_d05_rgbd_optical"
# Keep the visual actor near the earlier D04 classroom reference (x≈2.8m).
# x=0.6m cropped the person badly in the Owner screenshot.
PATH = [(0, 2.8), (5, 2.0), (10, 2.8)]
# Mounted camera optical axis: slight upward pitch (~10.3°).
# This is a D05 scene-only change; all RGB-D topics and image timing stay unchanged.
CAMERA_UP_PITCH_RAD = -0.18


def compose(waffle: Path, pi: Path, world: Path, actor: Path,
            model: Path, out: Path) -> dict:
    """Produce D05 demo variant only, with original D04 composition as baseline."""
    manifest = compose_d04(waffle, pi, world, actor, model, out)
    bot_path = out / "student_waffle_rgb.sdf.xacro"
    world_path = out / "student_human_world.sdf.xacro"
    bot = ET.parse(bot_path)
    camera_link = bot.find(".//model/link[@name='camera_link']")
    if camera_link is None:
        raise ValueError("D05 camera_link absent")
    rgb = camera_link.find("./sensor[@name='axia_student_rgb'][@type='camera']")
    if rgb is None:
        raise ValueError("D05 original D04 RGB overlay absent")
    if camera_link.find("./sensor[@type='rgbd_camera']") is not None:
        raise ValueError("D05 duplicate mounted RGBD camera")
    rgb.set("name", "axia_d05_registered_rgbd")
    rgb.set("type", "rgbd_camera")
    topic = rgb.find("topic")
    if topic is None:
        raise ValueError("D05 camera sensor topic missing")
    topic.text = TOPIC
    frame = rgb.find("gz_frame_id")
    if frame is None:
        frame = ET.SubElement(rgb, "gz_frame_id")
    frame.text = FRAME
    # D04's copied sensor was level. Tilt only this D05 sensor up so
    # the actor's head is not cut off near the camera.
    pose = rgb.find("pose")
    if pose is None:
        pose = ET.SubElement(rgb, "pose")
    pose.text = f"0 0 0 0 {CAMERA_UP_PITCH_RAD:.2f} 0"
    # Only this sensor is registered: RGB and Depth come from one native camera.
    if tuple(rgb.findtext("camera/image/"+k) for k in ("width","height","format")) != (
            "640", "480", "R8G8B8"):
        raise ValueError("D05 unexpected upstream RGB-D pixel format")
    bot.write(bot_path, encoding="unicode", xml_declaration=True)

    world_tree = ET.parse(world_path)
    waypoints = world_tree.findall(
        ".//actor[@name='axia_student_person']/script/trajectory/waypoint")
    if len(waypoints) != 4:
        raise ValueError("D05 expected original D04 four-waypoint actor")
    trajectory = world_tree.find(
        ".//actor[@name='axia_student_person']/script/trajectory")
    assert trajectory is not None
    for wp in waypoints:
        trajectory.remove(wp)
    for t, x in PATH:
        wp = ET.SubElement(trajectory, "waypoint")
        ET.SubElement(wp, "time").text = str(t)
        # Waffle from D04 launch: x=-0.5, y=-0.5, yaw=0.
        # Stay in forward FOV without adding a collision proxy.
        ET.SubElement(wp, "pose").text = f"{x:.1f} -0.5 0 0 0 3.14159"
    world_tree.write(world_path, encoding="unicode", xml_declaration=True)

    conf = out / "student_yolo.yaml"
    cfg = conf.read_text()
    anchor = "rgb_topic: /camera/image_raw"
    if cfg.count(anchor) != 1:
        raise ValueError("D05 pinned YOLO config anchor changed")
    conf.write_text(cfg.replace(anchor, "rgb_topic: " + RGB), encoding="utf-8")

    manifest.update({
        "variant": "D05_MOUNTED_RGBD_APPROACH_ONLY",
        "camera_topic": RGB, "depth_topic": DEPTH,
        "registered_rgbd_sensor": "axia_d05_registered_rgbd",
        "optical_frame": FRAME,
        "actor_trajectory_x": [x for _, x in PATH],
        "camera_pitch_rad": CAMERA_UP_PITCH_RAD,
        "d05_sensor_actual_execution": False,
        "d05_distance_actual_execution": False,
        "goal_sent": False,
        "certified_estop": False,
    })
    (out / "scene_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    cli = argparse.ArgumentParser()
    for name in ("waffle", "pi", "world", "actor", "model", "out"):
        cli.add_argument("--"+name, required=True, type=Path)
    args = cli.parse_args()
    try:
        result = compose(args.waffle,args.pi,args.world,args.actor,args.model,args.out)
    except (ValueError, OSError, ET.ParseError) as exc:
        cli.exit(2, "D05_LIVE_SCENE_BLOCKED: "+str(exc)+"\n")
    print("D05_LIVE_SCENE_READY: "+json.dumps(result,ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
