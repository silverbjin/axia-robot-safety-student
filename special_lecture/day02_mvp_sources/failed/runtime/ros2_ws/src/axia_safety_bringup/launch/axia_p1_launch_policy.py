"""Fail-closed Nav2 Jazzy configuration overlay for AXIA P1.

Official package and input file never mutated. Does not certify runtime graph.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import logging
import tempfile

import yaml

REQUIRED = ("controller_server", "velocity_smoother", "collision_monitor")
CM_IN = "cmd_vel_supervised"
CM_OUT = "cmd_vel"


def patch_nav2_parameters(source):
    if not isinstance(source, dict):
        raise ValueError("Nav2 root must be mapping")
    config = deepcopy(source)
    for name in REQUIRED:
        if not isinstance(config.get(name), dict):
            raise ValueError("Missing Nav2 node: " + name)
        if not isinstance(config[name].get("ros__parameters"), dict):
            raise ValueError("Missing ros__parameters: " + name)
    for name in REQUIRED:
        params = config[name]["ros__parameters"]
        if params.get("enable_stamped_cmd_vel") not in (None, False):
            raise ValueError("Stamped Twist unsupported: " + name)
        params["enable_stamped_cmd_vel"] = False
        if name != "collision_monitor" and params.get("cmd_vel_out_topic") in (
            "cmd_vel", "/cmd_vel"
        ):
            raise ValueError("Unexpected final cmd_vel publisher config: " + name)
    cm = config["collision_monitor"]["ros__parameters"]
    if cm.get("cmd_vel_in_topic") not in ("cmd_vel_smoothed", CM_IN):
        raise ValueError("Untrusted collision monitor input")
    if cm.get("cmd_vel_out_topic") != CM_OUT:
        raise ValueError("Collision Monitor final output must be cmd_vel")
    # Baseline v1 requires Collision Monitor itself to observe the
    # controlled /safety/scan relay, not a bypassing raw /scan subscription.
    if cm.get("observation_sources") != ["scan"]:
        raise ValueError("Collision Monitor must have exactly one named scan source")
    source = cm.get("scan")
    if (not isinstance(source, dict) or source.get("type") != "scan"
            or source.get("topic") not in ("scan", "/scan", "/safety/scan")
            or source.get("enabled") is False):
        raise ValueError("Collision Monitor scan source missing or bypass configured")
    source["topic"] = "/safety/scan"
    # Preserve all source_timeout / collision polygons and other official
    # Nav2 settings. This rewiring changes no source file under /opt/ros.
    cm["cmd_vel_in_topic"] = CM_IN
    return config


def write_p1_parameters(source_path, *, directory=None):
    source_path = Path(source_path).expanduser().resolve(strict=True)
    raw = source_path.read_bytes()
    parsed = yaml.safe_load(raw)
    patched = patch_nav2_parameters(parsed)
    folder = Path(directory) if directory is not None else None
    if folder is not None:
        folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="axia_p1_nav2_", suffix=".yaml", dir=folder,
        encoding="utf-8", delete=False,
    ) as stream:
        yaml.safe_dump(patched, stream, sort_keys=False)
        output = Path(stream.name)
    logging.warning("AXIA P1 params original=%s SHA256=%s overlay=%s",
                    source_path, hashlib.sha256(raw).hexdigest(), output)
    return output
