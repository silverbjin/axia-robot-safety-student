#!/usr/bin/env python3
"""Copy the known D08 read-only RViz profile, adding D10 Marker display only.

Never overwrite the official D08 profile or generated mesh view; no node, goal,
TF publisher, safety controller, or Gazebo sensor setting is changed.
"""
from __future__ import annotations
import argparse
from pathlib import Path

MARKER_TOPIC = "/axia/education/d10_if_marker"
MARKER_DISPLAY = """    - Class: rviz_default_plugins/Marker
      Name: D10 SYNTHETIC IF (NO CONTROL)
      Enabled: true
      Namespaces:
        All Enabled: true
      Topic:
        Depth: 10
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /axia/education/d10_if_marker
      Value: true
"""
ANCHOR = "  Enabled: true\n  Global Options:\n"

def build_profile(d08_profile: str) -> str:
    if d08_profile.count(ANCHOR) != 1:
        raise ValueError("D10_RVIZ_BASE_STRUCTURE_CHANGED")
    for topic in ("/scan", "/odom", "/axia/d05/rgbd/image",
                  "/axia/d05/rgbd/depth_image", "/yolo/cam0/debug_image"):
        if topic not in d08_profile:
            raise ValueError(f"D10_RVIZ_MISSING_BASE_TOPIC:{topic}")
    if "rviz_default_plugins/TF" not in d08_profile:
        raise ValueError("D10_RVIZ_MISSING_TF_DISPLAY")
    if "D10 SYNTHETIC IF" in d08_profile:
        raise ValueError("D10_RVIZ_ALREADY_OVERLAY")
    return d08_profile.replace(ANCHOR, MARKER_DISPLAY + ANCHOR, 1)

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if not args.source.is_file() or not args.out.parent.is_dir() or args.out.exists():
        p.error("source must be present; output parent existing and output not overwritten")
    original = args.source.read_text(encoding="utf-8")
    result = build_profile(original)
    args.out.write_text(result, encoding="utf-8")
    print(f"D10_RVIZ_OVERLAY_STATIC_READY path={args.out} base_unchanged=true "
          f"marker={MARKER_TOPIC} no_goal=true no_control=true")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
