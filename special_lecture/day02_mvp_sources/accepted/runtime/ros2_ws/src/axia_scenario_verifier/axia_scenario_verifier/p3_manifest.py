"""P3 offline scenario contract. Never starts Nav2, ROS, Gazebo or a fault."""
import datetime as dt
import json
import re
from pathlib import Path

IDS = {f"S{i:02d}": gate for i, gate in enumerate(("G08", "G07", "G10", "G09", "G10"), 1)}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
LEVELS = {"L0", "L1", "L2", "L3", "UNVERIFIED"}
KINDS = {"SYNTHETIC", "PUBLIC_CI_REFERENCE", "PRIVATE_REPORT_REFERENCE"}


def read_scenario(path: Path, directory: Path) -> dict:
    directory = directory.resolve()
    path = path.resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        raise ValueError("scenario path outside fixture directory or missing")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema") != "axia_p3_scenario_v1":
        raise ValueError("invalid P3 schema")
    sid = obj.get("scenario_id")
    if sid not in IDS or obj.get("gate") != IDS[sid]:
        raise ValueError("invalid scenario/gate mapping")
    if not HEX40.fullmatch(str(obj.get("source_sha", ""))):
        raise ValueError("missing or invalid evidence source SHA")
    if obj.get("verification_level") not in LEVELS or obj.get("evidence_kind") not in KINDS:
        raise ValueError("unrecognized evidence source or verification level")
    if obj.get("certified_estop") is not False or obj.get("gate_accepted") is not False:
        raise ValueError("offline fixture cannot attest E-Stop or formal acceptance")
    if obj.get("goal_sent") is not False or obj.get("fault_injected") is not False:
        raise ValueError("fixture must not assert a new goal or fault")
    ref = obj.get("source_ref")
    if not isinstance(ref, str) or not ref.strip() or ref.startswith("http://"):
        raise ValueError("missing or insecure source reference")
    stamp = obj.get("recorded_at_utc")
    if not isinstance(stamp, str):
        raise ValueError("recorded time is required")
    try:
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid recorded time") from exc
    if when.tzinfo is None or when > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        raise ValueError("naive/future evidence timestamp")
    if not isinstance(obj.get("description"), str) or not obj["description"].strip():
        raise ValueError("missing description")
    return obj


def load_five(directory: Path) -> list[dict]:
    if not directory.is_dir():
        raise ValueError("scenario directory missing")
    paths = sorted(directory.glob("S[0-9][0-9]_*.json"))
    if len(paths) != 5:
        raise ValueError("exactly five scenario fixtures required")
    items = [read_scenario(path, directory) for path in paths]
    if {x["scenario_id"] for x in items} != set(IDS):
        raise ValueError("duplicate or missing scenario IDs")
    return items
