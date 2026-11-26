#!/usr/bin/env python3
"""P2 G07 educational open-lane proposal, never Nav2 costmap/Goal acceptance.

Use the official Jazzy tb3_sandbox occupancy map READ-ONLY. No world model,
Nav2 planner, safety polygon or P1 map is changed. The actual moving-Goal
behavior and collision-free claim require separate Owner WSL2 L3 observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

DEMO_START = (-2.0, -0.5)
DEMO_GOAL = (-1.7, 0.7)  # 1.237 m versus P1's 0.4 m Goal
MIN_RAW_CLEARANCE_M = 0.45  # NOT inflated Nav2 footprint clearance
LATERAL_DEVIATION_LIMIT_M = 0.45
_DEMO_LENGTH_M = math.dist(DEMO_START, DEMO_GOAL)


def _pgm(pgm: bytes):
    """P5 8-bit grayscale parser: exact header and byte count, no dependencies."""
    if type(pgm) is not bytes or len(pgm) < 20 or len(pgm) > 8_000_000:
        raise ValueError("INVALID_MAP_BYTES")
    tokens = []
    index = 0
    while len(tokens) < 4:
        while index < len(pgm) and pgm[index] in (9, 10, 13, 32):
            index += 1
        if index < len(pgm) and pgm[index] == 35:  # # comment
            end = pgm.find(b"\n", index)
            if end < 0:
                raise ValueError("MAP_COMMENT_NOT_TERMINATED")
            index = end + 1
            continue
        start = index
        while index < len(pgm) and pgm[index] not in (9, 10, 13, 32, 35):
            index += 1
        if index == start:
            raise ValueError("MAP_HEADER_MISSING")
        tokens.append(pgm[start:index])
    if tokens[0] != b"P5" or tokens[3] != b"255":
        raise ValueError("UNSUPPORTED_MAP_FORMAT")
    try:
        width, height = (int(tokens[1]), int(tokens[2]))
    except ValueError as exc:
        raise ValueError("MAP_DIMENSIONS_INVALID") from exc
    if not (20 <= width <= 2048 and 20 <= height <= 2048):
        raise ValueError("MAP_DIMENSIONS_UNSUPPORTED")
    if index >= len(pgm) or pgm[index] not in (9, 10, 13, 32):
        raise ValueError("MAP_HEADER_DELIMITER_MISSING")
    index += 1
    if pgm[index - 1] == 13 and index < len(pgm) and pgm[index] == 10:
        index += 1
    image = pgm[index:]
    if len(image) != width * height:
        raise ValueError("MAP_IMAGE_SIZE_MISMATCH")
    return width, height, image


def within_demo_corridor(pose_xy):
    """Admit robot center only near the surveyed straight-map candidate."""
    if (not isinstance(pose_xy, (tuple, list)) or len(pose_xy) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for v in pose_xy)):
        return False
    x, y = pose_xy
    vx = DEMO_GOAL[0] - DEMO_START[0]
    vy = DEMO_GOAL[1] - DEMO_START[1]
    dx, dy = x - DEMO_START[0], y - DEMO_START[1]
    along = (dx * vx + dy * vy) / (_DEMO_LENGTH_M ** 2)
    cross = abs(dx * vy - dy * vx) / _DEMO_LENGTH_M
    return (-0.12 <= along <= 1.10 and
            cross <= LATERAL_DEVIATION_LIMIT_M and
            -2.30 <= x <= -1.30 and -0.75 <= y <= 0.95)


def validate_corridor_map(pgm: bytes, *, resolution: float, origin: tuple[float, float]) -> dict:
    """Survey occupancy at 2.5 cm intervals; no Costmap/Planner PASS inference."""
    if (type(resolution) not in (int, float) or not math.isfinite(resolution)
            or not 0.049 <= resolution <= 0.051 or
            not isinstance(origin, (tuple, list)) or len(origin) != 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in origin)
            or abs(origin[0] + 10.0) > 1e-8 and abs(origin[0] + 4.0) > 1e-8):
        # Test map (-4,-3) is kept distinct from real official (-10,-10).
        raise ValueError("UNEXPECTED_MAP_RESOLUTION_OR_ORIGIN")
    width, height, image = _pgm(pgm)
    res = float(resolution)
    samples = max(2, int(math.ceil(_DEMO_LENGTH_M / .025)) + 1)
    nearest = []
    occupied = 0
    unknown = 0
    # The 0.9m local neighborhood suffices to prove clearance >= 0.45m,
    # even when the closest occupied cell is farther away.
    neighborhood_px = int(math.ceil(.90 / res))
    for n in range(samples):
        t = n / (samples - 1)
        x = DEMO_START[0] + (DEMO_GOAL[0] - DEMO_START[0]) * t
        y = DEMO_START[1] + (DEMO_GOAL[1] - DEMO_START[1]) * t
        column = math.floor((x - origin[0]) / res)
        row = height - 1 - math.floor((y - origin[1]) / res)
        if not (0 <= row < height and 0 <= column < width):
            raise ValueError("CORRIDOR_OUTSIDE_OFFICIAL_MAP")
        value = image[row * width + column]
        if value < 120:
            occupied += 1
        elif value < 230:
            unknown += 1
        best_m = .90
        for r in range(max(0, row - neighborhood_px),
                       min(height, row + neighborhood_px + 1)):
            offset = r * width
            for c in range(max(0, column - neighborhood_px),
                           min(width, column + neighborhood_px + 1)):
                if image[offset + c] < 120:
                    distance = math.hypot((c - column) * res, (r - row) * res)
                    if distance < best_m:
                        best_m = distance
        # Conservative occupied-cell rectangle: center-to-center less half
        # a pixel diagonal. Actual robot clearance still needs local costmap.
        nearest.append(max(0.0, best_m - math.sqrt(2) * res / 2))
    minimum = min(nearest)
    if occupied or unknown or minimum < MIN_RAW_CLEARANCE_M:
        raise ValueError("CORRIDOR_NOT_CLEAR_IN_STATIC_MAP")
    return {
        "status": "STATIC_MAP_CLEARANCE_CANDIDATE",
        "source_map_sha256": hashlib.sha256(pgm).hexdigest(),
        "start_map": list(DEMO_START),
        "goal_map": list(DEMO_GOAL),
        "path_distance_m": round(_DEMO_LENGTH_M, 4),
        "min_raw_clearance_m": round(minimum, 4),
        "raster_resolution_m": res,
        "sample_count": samples,
        "occupied_samples": occupied,
        "unknown_samples": unknown,
        "inflated_costmap_checked": False,
        "nav2_compute_path_checked": False,
        "gazebo_collision_checked": False,
        "goal_sent": False,
        "gate_accepted": False,
        "certified_estop": False,
    }


def official_map_readonly(pgm_path: Path, yaml_path: Path):
    doc = yaml_path.read_text(encoding="utf-8")
    if not (re.search(r"(?m)^image:\s*tb3_sandbox[.]pgm\s*$", doc)
            and re.search(r"(?m)^resolution:\s*0[.]0*5\d*\s*$", doc)
            and re.search(r"(?m)^origin:\s*\[-10[.]0+,\s*-10[.]0+,\s*0[.]0+\]\s*$", doc)
            and re.search(r"(?m)^negate:\s*0\s*$", doc)):
        raise ValueError("UNEXPECTED_OFFICIAL_JAZZY_MAP_METADATA")
    result = validate_corridor_map(pgm_path.read_bytes(),
                                  resolution=.05, origin=(-10., -10.))
    result["source_yaml_sha256"] = hashlib.sha256(yaml_path.read_bytes()).hexdigest()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map-pgm", type=Path, required=True)
    parser.add_argument("--map-yaml", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = official_map_readonly(args.map_pgm, args.map_yaml)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("P2_G07_DEMO_OPEN_CORRIDOR_STATIC_MAP_CANDIDATE_NO_GOAL "
              f"length_m={result['path_distance_m']} "
              f"min_raw_clearance_m={result['min_raw_clearance_m']} "
              "COSTMAP_NOT_VERIFIED GAZEBO_NOT_RUN")
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print("P2_G07_DEMO_OPEN_CORRIDOR_BLOCKED:" + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
