#!/usr/bin/env python3
"""P2-T02 overlay: add two official Collision Monitor polygons to P1 Nav2 YAML.

This is static preparation only. No ROS node, Goal, fault, or publisher is launched.
The existing axia_tb3_p1.launch.py accepts the generated --params_file value.
"""
import argparse
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
# Source-tree callers and the installed axia_safety_bringup share the same
# approved parameter policy, without resolving from process cwd.
LAUNCH_DIR=(ROOT / 'ros2_ws/src/axia_safety_bringup/launch'
            if (ROOT / 'ros2_ws/src/axia_safety_bringup/launch/axia_p1_launch_policy.py').is_file()
            else ROOT / 'launch')
sys.path.insert(0,str(LAUNCH_DIR))
from axia_p1_launch_policy import patch_nav2_parameters  # reuse P1 fail-closed routing

ZONE_NAMES = ('AXIA_StopFront', 'AXIA_SlowFront')
# Frozen teaching-candidate vertices; changing geometry requires an approved
# revised policy and accompanying tests, never a silent bounding-box edit.
APPROVED_VERTICES = {
    'AXIA_StopFront': [[0.40, 0.32], [0.40, -0.32], [-0.10, -0.32], [-0.10, 0.32]],
    'AXIA_SlowFront': [[0.75, 0.40], [0.75, -0.40], [-0.10, -0.40], [-0.10, 0.40]],
}


def _bbox(value: object) -> tuple:
    if not isinstance(value, str):
        raise ValueError('Zone points must use official Nav2 string syntax')
    points = yaml.safe_load(value)
    if not isinstance(points, list) or len(points) != 4 or any(
        not isinstance(p, list) or len(p) != 2 or any(
            not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x)
            for x in p) for p in points
    ):
        raise ValueError('Invalid zone polygon vertices')
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    if min(xs) >= max(xs) or min(ys) >= max(ys):
        raise ValueError('Degenerate zone rectangle')
    return (min(xs), max(xs), min(ys), max(ys))


def _zones_valid(zones: dict) -> None:
    if not isinstance(zones, dict) or set(zones) != set(ZONE_NAMES):
        raise ValueError('Expected only the two approved P2 front zones')
    boxes = []
    for name, action in zip(ZONE_NAMES, ('stop', 'slowdown')):
        z = zones[name]
        allowed = {'type', 'points', 'action_type', 'min_points', 'enabled', 'visualize'}
        if action == 'slowdown':
            allowed.add('slowdown_ratio')
        if not isinstance(z, dict) or set(z) != allowed:
            raise ValueError('Missing or extra zone keys: ' + name)
        if z['type'] != 'polygon' or z['action_type'] != action or z['min_points'] != 4:
            raise ValueError('Invalid zone action or scan point threshold: ' + name)
        if z['enabled'] is not True or z['visualize'] is not False:
            raise ValueError('Zone must remain enabled without additional publishers')
        if action == 'slowdown' and z['slowdown_ratio'] != 0.30:
            raise ValueError('Unapproved slowdown ratio')
        boxes.append(_bbox(z['points']))
        if yaml.safe_load(z['points']) != APPROVED_VERTICES[name]:
            raise ValueError('Unapproved polygon geometry or vertex ordering: ' + name)
    stop, slow = boxes
    if not (slow[0] <= stop[0] and stop[1] <= slow[1] and
            slow[2] <= stop[2] and stop[3] <= slow[3]):
        raise ValueError('Stop zone must be entirely inside slowdown zone')
    if stop[1] != 0.40 or slow[1] != 0.75:
        raise ValueError('Unapproved stop or slowdown distance')


def patch_p2_zone_parameters(source: dict, zones: dict) -> dict:
    _zones_valid(zones)
    config = patch_nav2_parameters(source)
    cm = config['collision_monitor']['ros__parameters']
    if not isinstance(cm.get('source_timeout'), (int, float)) or cm['source_timeout'] <= 0:
        raise ValueError('Collision Monitor source timeout must remain positive')
    original_names = cm.get('polygons')
    if not isinstance(original_names, list) or not original_names or any(
        not isinstance(name, str) for name in original_names
    ):
        raise ValueError('Existing official protective polygons must be retained')
    if any(name in original_names or name in cm for name in ZONE_NAMES):
        raise ValueError('P2 zone collision with existing official settings')
    for name in ZONE_NAMES:
        cm[name] = deepcopy(zones[name])
    cm['polygons'] = list(ZONE_NAMES) + list(original_names)
    return config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='installed official Nav2 params YAML')
    parser.add_argument('--zones', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='fresh output file; overwrite prohibited')
    args = parser.parse_args(argv)
    try:
        raw = args.source.read_bytes()
        zone_bytes = args.zones.read_bytes()
        merged = patch_p2_zone_parameters(yaml.safe_load(raw), yaml.safe_load(zone_bytes))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            yaml.safe_dump(merged, output, sort_keys=False)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print('P2_ZONE_OVERLAY_BLOCKED ' + str(exc), file=sys.stderr)
        return 2
    print('P2_ZONE_OVERLAY_STATIC_OK source_sha256=' + hashlib.sha256(raw).hexdigest()
          + ' zone_sha256=' + hashlib.sha256(zone_bytes).hexdigest()
          + ' output=' + str(args.output))
    print('G05_G06_BLOCKED=true G07_GAZEBO_NOT_VERIFIED=true')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
