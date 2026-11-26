#!/usr/bin/env python3
"""D07 GUI-only read-only Gazebo Harmonic server-world discovery gate.

Gazebo Sim 8 SERVER publishes /world/<world>/clock and /world/<world>/stats.
The server's /world/<world>/scene/info is a SERVICE, not a required topic.
Do NOT claim GUI connection, a rendered scene, Goal or safety acceptance.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

WORLD_TOPIC = re.compile(r"^/world/([A-Za-z0-9_-]+)/(clock|stats)$")
PASS = "D07_H01_GUI_SERVER_WORLD_DISCOVERED_NOT_GUI_RENDER_PROOF"
HOLD = "D07_H01_GUI_TRANSPORT_NO_WORLD_DISCOVERED"


def assess_world_topics(raw: str) -> dict:
    result = {
        "status": HOLD,
        "world": None,
        "first_invalid_boundary": "GZ_WORLD_SERVER_TOPICS_UNVERIFIED",
        "gui_connected_proven": False,
        "scene_rendered_proven": False,
        "motion_admitted": False,
        "goal_sent": False,
        "certified_estop": False,
    }
    if not isinstance(raw, str) or len(raw) > 1_000_000:
        return result
    seen: dict[str, set[str]] = {}
    for line in raw.splitlines():
        match = WORLD_TOPIC.fullmatch(line.strip())
        if match:
            world, kind = match.groups()
            seen.setdefault(world, set()).add(kind)
    complete = sorted(w for w, types in seen.items()
                      if {"clock", "stats"}.issubset(types))
    if complete:
        result.update({
            "status": PASS,
            "world": complete[0],
            "first_invalid_boundary": None,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = assess_world_topics(
            args.topics_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        print(f"D07_H01_GUI_TRANSPORT_TOPIC_FILE_UNAVAILABLE "
              f"reason={type(error).__name__}", file=sys.stderr, flush=True)
        return 2
    if result["status"] != PASS:
        print(HOLD + " reason=NO_SAME_WORLD_CLOCK_AND_STATS_TOPICS",
              file=sys.stderr, flush=True)
        return 2
    print(PASS + " world=" + result["world"] +
          " server_discovered_only=true gui_connection_proven=false",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
