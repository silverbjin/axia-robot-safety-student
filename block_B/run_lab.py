"""Pure Python D04/D05 educational replay; explicitly NOT robot safety evidence."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    from .fixture_io import load_fixtures
    from .block_b_todo import select_person, measure_person_range
except ImportError:  # python block_B/run_lab.py
    from fixture_io import load_fixtures
    from block_b_todo import select_person, measure_person_range


def run(fixtures: Path, out: Path) -> int:
    try:
        rows, depth = load_fixtures(fixtures)
        if out.exists():
            raise ValueError("Output directory must not exist")
        reports = []
        for sample in depth["samples"]:
            frame_id = sample["frame_id"]
            candidates = [row for row in rows if row["frame_id"] == frame_id]
            selected = select_person(candidates)
            distance = (measure_person_range(sample["depth_m"], selected,
                        sample["frame_stamp_s"], sample["depth_stamp_s"])
                        if selected is not None else None)
            reports.append({"frame_id": frame_id, "person_found": selected is not None,
                            "distance_m": distance, "range_valid": distance is not None})
        out.mkdir(parents=True, exist_ok=False)
        with (out / "person_range.csv").open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=["frame_id", "person_found", "distance_m", "range_valid"])
            writer.writeheader()
            writer.writerows(reports)
        (out / "summary.json").write_text(json.dumps({
            "source": "SYNTHETIC_COURSE_FIXTURE", "verified_level": "PYTHON_ONLY",
            "ros_verified": False, "gazebo_verified": False,
            "certified_estop_verified": False, "results": reports},
            ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(f"PYTHON_SYNTHETIC_ONLY: {len(reports)} frames; output={out}")
        return 0
    except (ValueError, KeyError, TypeError, OSError, NotImplementedError) as exc:
        print(f"LAB_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block B D04/D05 offline replay (NO ROS)")
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).parent / "fixtures")
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    args = parser.parse_args(argv)
    return run(args.fixtures, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
