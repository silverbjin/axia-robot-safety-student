#!/usr/bin/env python3
"""D07-H01 ONLY: expose Gazebo SceneBroadcaster in a temporary world Xacro.

Gazebo's official TB3 world conditionally removes SceneBroadcaster when
headless:=True. D07 starts the genuine Nav2 server headless, and connects
its read-only GUI only after stable free-path readiness. Unwrap just that
one official plugin, preserving all other world, Contact, sensors, motion
and safety settings. The installed upstream world is never edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SCENE = "gz::sim::systems::SceneBroadcaster"
FILENAME = "gz-sim-scene-broadcaster-system"
XACRO_NS = "{http://www.ros.org/wiki/xacro}"

# Matched only after structural XML validation; keeps all other text
# and Xacro declarations byte-for-byte as in the original overlay.
WRAPPER = re.compile(
    r'<xacro:unless\s+value=["\']\$\(arg\s+headless\)["\']\s*>\s*'
    r'(?P<plugin><plugin\s+filename=["\']'
    r'gz-sim-scene-broadcaster-system["\']\s+name=["\']'
    r'gz::sim::systems::SceneBroadcaster["\']\s*>'
    r'\s*</plugin>)\s*</xacro:unless>',
    re.DOTALL,
)


def patch_d07_world(source: str) -> str:
    if not isinstance(source, str):
        raise ValueError("D07_SCENE_WORLD_SOURCE_NOT_TEXT")
    root = ET.fromstring(source)
    if root.tag != "sdf":
        raise ValueError("D07_SCENE_WORLD_NOT_SDF")
    worlds = root.findall("world")
    if len(worlds) != 1 or worlds[0].get("name") != "default":
        raise ValueError("D07_SCENE_WORLD_NOT_UNIQUE_DEFAULT")
    world = worlds[0]
    plugin_names = [p.get("name") for p in world.iter("plugin")]
    for mandatory in ("gz::sim::systems::Physics",
                      "gz::sim::systems::UserCommands",
                      "gz::sim::systems::Sensors",
                      "gz::sim::systems::Contact"):
        if mandatory not in plugin_names:
            raise ValueError("D07_SCENE_WORLD_MISSING_" + mandatory.split("::")[-1])
    scene_plugins = [p for p in root.iter("plugin")
                     if p.get("name") == SCENE]
    if len(scene_plugins) != 1 or scene_plugins[0].get("filename") != FILENAME:
        raise ValueError("D07_SCENE_WORLD_DUPLICATE_OR_MISSING_SCENE")
    conditional = [x for x in world.findall(XACRO_NS + "unless")
                   if x.get("value") == "$(arg headless)"]
    if len(conditional) != 1 or list(conditional[0]) != scene_plugins:
        raise ValueError("D07_SCENE_WORLD_UNEXPECTED_HEADLESS_STRUCTURE")
    matches = list(WRAPPER.finditer(source))
    if len(matches) != 1:
        raise ValueError("D07_SCENE_WORLD_HEADLESS_WRAPPER_MISMATCH")
    m = matches[0]
    patched = source[:m.start()] + "    " + m.group("plugin") + source[m.end():]
    new_root = ET.fromstring(patched)
    patched_world = new_root.find("world")
    assert patched_world is not None
    if sum(p.get("name") == SCENE for p in patched_world.findall("plugin")) != 1:
        raise ValueError("D07_SCENE_WORLD_PLUGIN_NOT_UNCONDITIONAL")
    if any(p.get("name") == SCENE for elem in new_root.iter(XACRO_NS + "unless")
           for p in elem.iter("plugin")):
        raise ValueError("D07_SCENE_WORLD_STILL_CONDITIONAL")
    # Headless remains true for staged Nav2 startup; we do not spawn a
    # second Gazebo GUI or enable any moving-goal privilege.
    if '<xacro:arg name="headless" default="true"/>' not in patched:
        raise ValueError("D07_SCENE_WORLD_HEADLESS_ARG_CHANGED")
    return patched


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        original = args.source.read_bytes()
        patched = patch_d07_world(original.decode("utf-8"))
        raw = patched.encode("utf-8")
        manifest = {
            "schema": "axia_d07_h01_scene_broadcaster_world_overlay_v1",
            "scope": "D07_H01_GUI_READONLY_SIM_ONLY",
            "headless_launch_unchanged": True,
            "scene_broadcaster_unconditional": True,
            "scene_broadcaster_count": 1,
            "original_sha256": hashlib.sha256(original).hexdigest(),
            "overlay_sha256": hashlib.sha256(raw).hexdigest(),
            "official_source_mutated": False,
            "goal_sent": False,
            "certified_estop": False,
            "actual_gazebo_scene_proven": False,
            "owner_visual_accepted": False,
        }
        with args.output.open("xb") as f:
            f.write(raw)
        with args.manifest.open("x", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, indent=2)
            f.write("\n")
        print("D07_H01_SCENE_BROADCASTER_WORLD_READY_NO_GOAL "
              f"overlay_sha256={manifest['overlay_sha256']}")
        return 0
    except (OSError, ValueError, ET.ParseError, UnicodeError) as exc:
        print("D07_H01_SCENE_BROADCASTER_OVERLAY_FAIL_CLOSED:"
              + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
