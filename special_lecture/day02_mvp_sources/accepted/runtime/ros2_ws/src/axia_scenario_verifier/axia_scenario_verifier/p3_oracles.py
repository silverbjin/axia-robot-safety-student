"""Pure time-indexed 2D overlap oracle for training fixtures, not live control."""
import math


def classify_pair(robot: dict, person: dict, *, now_sec: float, stale_sec: float = 0.5) -> str:
    """P: spatial+time overlap, N: no overlap, U: stale/missing/invalid data."""
    try:
        now, stale = float(now_sec), float(stale_sec)
        if not math.isfinite(now) or not math.isfinite(stale) or stale <= 0:
            return "U"
        for obj in (robot, person):
            if not isinstance(obj, dict):
                return "U"
            vals = [float(obj[k]) for k in ("x", "y", "radius", "start_sec", "end_sec", "observed_sec")]
            if not all(math.isfinite(v) for v in vals):
                return "U"
            x, y, radius, start, end, observed = vals
            if radius < 0 or start > end or observed > now or now - observed > stale:
                return "U"
        temporal = max(float(robot["start_sec"]), float(person["start_sec"])) <= min(float(robot["end_sec"]), float(person["end_sec"]))
        spatial = math.hypot(float(robot["x"]) - float(person["x"]), float(robot["y"]) - float(person["y"])) <= float(robot["radius"]) + float(person["radius"])
        return "P" if temporal and spatial else "N"
    except (KeyError, ValueError, TypeError, OverflowError):
        return "U"



def classify_time_indexed(robot_trajectory: list[dict], person: dict, *,
                          now_sec: float, dt_sec: float = 0.2,
                          horizon_sec: float = 3.0, stale_sec: float = 0.5,
                          confidence_min: float = 0.5) -> str:
    """L0 only: project one tracked person against the robot at the SAME t.

    P = at least one co-timed disk overlap; N = no co-timed overlap;
    U = stale/future/low-confidence person or invalid/incomplete trajectory.
    This is not a live control or Gazebo/person-detection attestation.
    """
    try:
        numbers = (now_sec, dt_sec, horizon_sec, stale_sec, confidence_min)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in numbers):
            return "U"
        now, dt, horizon, stale, minimum = map(float, numbers)
        if dt <= 0 or horizon <= 0 or stale <= 0 or not (0 <= minimum <= 1):
            return "U"
        count = round(horizon / dt) + 1
        if count < 2 or count > 100 or abs((count - 1) * dt - horizon) > 1e-6:
            return "U"
        if not isinstance(person, dict) or not isinstance(robot_trajectory, list):
            return "U"
        if len(robot_trajectory) != count:
            return "U"
        fields = ("x", "y", "vx", "vy", "radius", "confidence", "observed_sec")
        if any(type(person.get(k)) not in (int, float) or
               not math.isfinite(person[k]) for k in fields):
            return "U"
        px, py, vx, vy = (float(person[k]) for k in ("x", "y", "vx", "vy"))
        radius = float(person["radius"])
        observed = float(person["observed_sec"])
        confidence = float(person["confidence"])
        if (radius < 0 or not (minimum <= confidence <= 1.0)
                or not (0 <= now - observed <= stale)):
            return "U"
        overlap = False
        for index, point in enumerate(robot_trajectory):
            if not isinstance(point, dict) or any(
                type(point.get(k)) not in (int, float) or
                not math.isfinite(point[k])
                for k in ("t_sec", "x", "y", "radius")
            ):
                return "U"
            t = float(point["t_sec"])
            if abs(t - (now + index * dt)) > 1e-6 or point["radius"] < 0:
                return "U"
            future_age = t - observed
            human_x = px + vx * future_age
            human_y = py + vy * future_age
            if not math.isfinite(human_x) or not math.isfinite(human_y):
                return "U"
            if math.hypot(float(point["x"]) - human_x,
                          float(point["y"]) - human_y) <= float(point["radius"]) + radius:
                overlap = True
        return "P" if overlap else "N"
    except (KeyError, ValueError, TypeError, OverflowError):
        return "U"


def verify_cases(data: dict) -> list[dict]:
    if data.get("schema") != "axia_p3_pnu_v1" or not isinstance(data.get("cases"), list):
        raise ValueError("invalid PNU fixture schema")
    cases = data["cases"]
    if len(cases) < 5 or len({c.get("id") for c in cases}) != len(cases):
        raise ValueError("insufficient or duplicate PNU cases")
    if not {"P", "N", "U"} <= {c.get("expected") for c in cases}:
        raise ValueError("P/N/U coverage missing")
    outcomes = []
    for case in cases:
        actual = classify_pair(case.get("robot"), case.get("person"), now_sec=case.get("now_sec", float("nan")))
        record = {"case_id": case["id"], "expected": case["expected"], "actual": actual,
                  "pass": actual == case["expected"]}
        if "time_indexed" in case:
            indexed = case["time_indexed"]
            if not isinstance(indexed, dict):
                indexed_actual = "U"
            else:
                indexed_actual = classify_time_indexed(
                    indexed.get("robot_trajectory"), indexed.get("person"),
                    now_sec=indexed.get("now_sec", float("nan")))
            record["time_indexed_actual"] = indexed_actual
            record["pass"] = record["pass"] and indexed_actual == case["expected"]
        outcomes.append(record)
    return outcomes
