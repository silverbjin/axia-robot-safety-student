#!/usr/bin/env python3
"""D08 GUI-only RViz model source adapter; no modification to ROS/Nav2/URDF.

Owner logs show package://nav2_minimal_tb3_sim/models/{waffle_base,tire,
lds,r200}.dae resource failures (Nav2 upstream issue #19). Reuse installed
OFFICIAL meshes, but render from one ephemeral fixed URDF file in RViz only.
Robot physics, sensor frames, robot_state_publisher and /robot_description
remain exactly as upstream. No Goal, cmd_vel or controller involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

PREFIX = "package://nav2_minimal_tb3_sim/models/"
FIXED = PREFIX + "turtlebot3_model/meshes/"
FILENAME = re.compile(r"^[A-Za-z0-9_]+\.dae$")


def build_view(prefix: Path, urdf: Path, rviz: Path, out: Path) -> dict:
    if not prefix.is_dir() or not urdf.is_file() or not rviz.is_file():
        raise ValueError("D08_RVIZ_OFFICIAL_SOURCE_MISSING")
    if not out.is_dir() or out.is_symlink():
        raise ValueError("D08_RVIZ_OUTPUT_MUST_BE_PRECREATED_PRIVATE_DIR")
    original = urdf.read_text(encoding="utf-8")
    template = rviz.read_text(encoding="utf-8")
    root = ET.fromstring(original)
    if root.tag != "robot" or "turtlebot3_waffle" not in urdf.name:
        raise ValueError("D08_RVIZ_EXPECTED_OFFICIAL_WAFFLE_URDF")
    descriptions = re.findall(r'filename="(package://nav2_minimal_tb3_sim/models/[^"]+\.dae)"',original)
    if not descriptions:
        raise ValueError("D08_RVIZ_NO_OFFICIAL_MESHES_IN_URDF")
    updated = original
    count = 0
    for location in sorted(set(descriptions)):
        rel = location[len(PREFIX):]
        name = Path(rel).name
        if not FILENAME.fullmatch(name):
            raise ValueError("D08_RVIZ_UNEXPECTED_OFFICIAL_MESH_NAME")
        intended = FIXED + name
        # Check actual installed files: no copied mesh assets or fabricated geometry.
        asset = prefix / "share/nav2_minimal_tb3_sim/models/turtlebot3_model/meshes" / name
        if not asset.is_file():
            raise ValueError("D08_RVIZ_MESH_FILE_MISSING_" + name)
        if location != intended:
            updated = updated.replace(location, intended)
            count += 1
    ET.fromstring(updated)
    topic = "      Description Source: Topic\n"
    if template.count(topic) != 1:
        raise ValueError("D08_RVIZ_TEMPLATE_MODEL_TOPIC_CONTRACT_CHANGED")
    start = template.find("      Description Topic:\n", template.index(topic))
    end = template.find("      Links:\n",start)
    if start < 0 or end < 0:
        raise ValueError("D08_RVIZ_TEMPLATE_TOPIC_FIELD_CONTRACT_CHANGED")
    urdf_out = out / "d08_waffle_view.urdf"
    rviz_out = out / "d08_render_view.rviz"
    if urdf_out.exists() or rviz_out.exists():
        raise ValueError("D08_RVIZ_OUTPUT_EXISTS_NO_OVERWRITE")
    view = template.replace(topic,"      Description Source: File\n",1)
    start = view.index("      Description Topic:\n")
    end = view.index("      Links:\n",start)
    view = view[:start] + "      Description File: " + json.dumps(str(urdf_out.resolve())) + "\n" + view[end:]
    urdf_out.write_text(updated,encoding="utf-8")
    rviz_out.write_text(view,encoding="utf-8")
    report = {
        "scope": "D08_READONLY_RVIZ_VISUAL_MESH_ONLY",
        "fixed_meshes": count,
        "official_mesh_count": len(set(descriptions)),
        "urdf_sha256": hashlib.sha256(updated.encode()).hexdigest(),
        "rviz_sha256": hashlib.sha256(view.encode()).hexdigest(),
        "source_modified": False,
        "goal_sent": False,
        "cmd_vel_published": False,
        "owner_visual_verified": False,
    }
    (out/"mesh_view_manifest.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("prefix","urdf","rviz","out"):
        ap.add_argument("--"+name,required=True,type=Path)
    a=ap.parse_args()
    try:
        result=build_view(a.prefix,a.urdf,a.rviz,a.out)
        print("D08_RVIZ_OFFICIAL_MESH_VIEW_READY " + json.dumps(result,sort_keys=True),flush=True)
        return 0
    except (OSError,ValueError,UnicodeError,ET.ParseError) as exc:
        print("D08_RVIZ_OFFICIAL_MESH_VIEW_BLOCKED:"+str(exc),
              file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
