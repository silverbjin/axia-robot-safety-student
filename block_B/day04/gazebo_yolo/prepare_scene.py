#!/usr/bin/env python3
"""Student-only D04 scene adapter for official Nav2 Waffle & ROBOTIS Pi RGB.

Reads installed upstream SDF files; writes NEW temporary overlay world and
camera SDF plus upstream yolo_ros plugin params. No P1 or instructor source.
No ROS imports, command publishers, Goals, Faults, or stop claims.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ET.register_namespace("xacro", "http://www.ros.org/wiki/xacro")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compose(waffle: Path, pi: Path, world: Path, actor: Path,
            model: Path, out: Path) -> dict:
    for file in (waffle, pi, world, actor, model):
        if not file.is_file() or file.is_symlink():
            raise ValueError(f"Official input missing or symlinked: {file}")
    if actor.suffix != ".dae" or model.suffix != ".onnx":
        raise ValueError("Expected a preverified .dae actor and .onnx model")
    if out.exists():
        raise ValueError(f"Existing output must be preserved: {out}")

    robot_xml = ET.parse(waffle)
    pi_xml = ET.parse(pi)
    world_xml = ET.parse(world)
    camera_link = robot_xml.find(".//model/link[@name='camera_link']")
    camera = pi_xml.find(".//sensor[@name='camera'][@type='camera']")
    if camera_link is None or camera is None:
        raise ValueError("Official Nav2 Waffle/ROBOTIS Pi camera schema changed")
    if camera.findtext("topic") != "camera/image_raw":
        raise ValueError("Unsupported upstream Waffle Pi camera topic")
    if tuple(camera.findtext("camera/image/" + k)
             for k in ("width", "height", "format")) != ("640", "480", "R8G8B8"):
        raise ValueError("Official camera resolution/encoding changed")
    if robot_xml.find(".//sensor[@name='axia_student_rgb']") is not None:
        raise ValueError("Camera overlay already applied")
    camera_copy = deepcopy(camera)
    camera_copy.set("name", "axia_student_rgb")
    pose = camera_copy.find("pose")
    if pose is None:
        pose = ET.SubElement(camera_copy, "pose")
    pose.text = "0 0 0 0 0 0"
    camera_link.append(camera_copy)

    root = world_xml.find(".//world")
    render = world_xml.find(".//plugin[@filename='gz-sim-sensors-system']/render_engine")
    if root is None or render is None:
        raise ValueError("Official Gazebo world sensors plugin not found")
    if root.find("./actor[@name='axia_student_person']") is not None:
        raise ValueError("Duplicate student actor")

    human = ET.SubElement(root, "actor", name="axia_student_person")
    skin = ET.SubElement(human, "skin")
    ET.SubElement(skin, "filename").text = str(actor.resolve())
    ET.SubElement(skin, "scale").text = "1.0"
    animation = ET.SubElement(human, "animation", name="walk")
    ET.SubElement(animation, "filename").text = str(actor.resolve())
    ET.SubElement(animation, "interpolate_x").text = "true"
    script = ET.SubElement(human, "script")
    ET.SubElement(script, "loop").text = "true"
    ET.SubElement(script, "auto_start").text = "true"
    traj = ET.SubElement(script, "trajectory", id="0", type="walk", tension="1.0")
    # 6-second visual-only loop in front of the camera. No collision proxy.
    for t, y in ((0, -0.5), (2, -0.7), (4, -0.3), (6, -0.5)):
        wp = ET.SubElement(traj, "waypoint")
        ET.SubElement(wp, "time").text = str(t)
        ET.SubElement(wp, "pose").text = f"0.8 {y} 0 0 0 3.14159"

    absolute_model = str(model.resolve())
    if any(char in absolute_model for char in ('"', "\n", "\r", "\\", "\0")):
        raise ValueError("Unsupported ONNX path")
    yaml_text = f"""/yolo/yolo_node:
  ros__parameters:
    use_sim_time: true
    plugins: ["detection", "debug"]
    cameras: ["cam0"]
    cam0:
      rgb_topic: /camera/image_raw
      image_reliability: 2
    detection:
      plugin: yolo_ros/DetectionPlugin
      cameras: ["cam0"]
      model_path: "{absolute_model}"
      model_repo: ""
      model_filename: ""
      model_type: auto
      provider: cpu
      threshold: 0.15
      iou: 0.45
      n_threads: 2
      max_fps: 5
    debug:
      plugin: yolo_ros/DebugPlugin
      cameras: ["cam0"]
"""
    out.mkdir(parents=True)
    robot_xml.write(out / "student_waffle_rgb.sdf.xacro", encoding="unicode", xml_declaration=True)
    world_xml.write(out / "student_human_world.sdf.xacro", encoding="unicode", xml_declaration=True)
    (out / "student_yolo.yaml").write_text(yaml_text, encoding="utf-8")
    evidence = {
        "source": "PUBLIC_OFFICIAL_NAV2_WAFFLE_ROBOTIS_PI_AND_YOLO_ROS",
        "official_waffle_sha256": sha(waffle),
        "official_pi_sha256": sha(pi),
        "official_world_sha256": sha(world),
        "actor_sha256": sha(actor),
        "model_sha256": sha(model),
        "camera_topic": "/camera/image_raw",
        "detector_topic": "/yolo/cam0/detections",
        "debug_topic": "/yolo/cam0/debug_image",
        "sim_only": True, "visual_only_actor": True,
        "goal_sent": False, "private_instructor_source": False,
        "certified_estop": False, "live_verified": False,
    }
    (out / "scene_manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def main():
    cli = argparse.ArgumentParser()
    for name in ("waffle", "pi", "world", "actor", "model", "out"):
        cli.add_argument("--" + name, type=Path, required=True)
    a = cli.parse_args()
    try:
        report = compose(a.waffle, a.pi, a.world, a.actor, a.model, a.out)
    except (ValueError, OSError, ET.ParseError) as error:
        cli.exit(2, "D04_STUDENT_SCENE_BLOCKED: " + str(error) + "\n")
    print("D04_STUDENT_SCENE_READY: " + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
