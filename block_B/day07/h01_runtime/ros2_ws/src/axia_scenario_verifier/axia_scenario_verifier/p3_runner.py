"""P3 fixture-only CLI, evidence inventory and immutable per-run artifact hashes.

Reuses the existing axia_scenario_verifier package and runner status codes.
No claim of ROS/Gazebo execution or formal G08-G11 acceptance is made.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

from .p3_inventory import inspect_inventory
from .p3_linkage import read_linkage
from .p3_manifest import load_five
from .p3_oracles import verify_cases
from .p3_replay import read_replay, check_sequence
from .runner import EXIT_PASS, EXIT_FAIL, EXIT_INCONCLUSIVE, EXIT_ERROR, sha256, atomic_json

ROOT = Path(__file__).resolve().parents[4]


def source_commit(root: Path) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False, timeout=5)
        s = p.stdout.strip()
        return s if p.returncode == 0 and len(s) == 40 and all(c in "0123456789abcdef" for c in s) else None
    except (OSError, subprocess.SubprocessError):
        return None


def run(*, root: Path = ROOT, results_root: Path = Path("results/p3"), selected: str = "all", evidence_dir: Path | None = None,
        owner_inventory: Path | None = None) -> tuple[int, Path]:
    root = root.resolve()
    items = load_five(root / "scenarios")
    if selected != "all":
        items = [s for s in items if s["scenario_id"] == selected]
        if not items:
            raise ValueError("unknown scenario ID")
    pnu_path = root / "fixtures/p3/s04_pnu.json"
    if not pnu_path.is_file():
        raise ValueError("PNU fixture missing")
    pnu = json.loads(pnu_path.read_text(encoding="utf-8"))
    cases = verify_cases(pnu)
    # Annotate reviewed source references without altering historical fixture,
    # real robot authorization, L0 verdict, or formal G08-G11 acceptance.
    linked_source_evidence, linked_evidence_sha256 = read_linkage(root)
    inventory_assessment = (inspect_inventory(owner_inventory, root / "docs/reports/p3_r01_source_registry.json")
                            if owner_inventory is not None else None)
    run_id = datetime.now(timezone.utc).strftime("p3-%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    dest = results_root.resolve() / run_id
    dest.mkdir(parents=True, exist_ok=False)
    records = []
    for item in items:
        sid = item["scenario_id"]
        if sid == "S04":
            ok = all(c["pass"] for c in cases)
            status = "OFFLINE_FIXTURE_PASS" if ok else "FAIL"
            detail = cases
        else:
            status, detail = "NOT_VERIFIED", []  # Reference is not authenticated raw evidence.
            if evidence_dir is not None:
                try:
                    replay = read_replay(evidence_dir, item)
                    valid, reason = check_sequence(sid, replay)
                    status = "REPLAY_ORACLE_PASS" if valid else "FAIL"
                    detail = [{"reason": reason, "count": len(replay)}]
                except (ValueError, OSError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
                    status, detail = "FAIL", [{"reason": type(exc).__name__ + ": " + str(exc)}]
        records.append({"scenario_id": sid, "gate": item["gate"], "status": status,
                        "evidence_kind": item["evidence_kind"], "verification_level": "L0" if status in ("OFFLINE_FIXTURE_PASS", "REPLAY_ORACLE_PASS") else "UNVERIFIED",
                        "reference_level": item["verification_level"], "source_sha": item["source_sha"],
                        "source_ref": item["source_ref"], "gate_accepted": False,
                        "goal_sent": False, "fault_injected": False, "certified_estop": False,
                        "runner_goal_sent": False, "runner_fault_injected": False,
                        "source_goal_sent": None, "source_fault_injected": None,
                        "source_raw_reviewed": False, "case_results": detail})
    status = "FAIL" if any(r["status"] == "FAIL" for r in records) else "INCONCLUSIVE"
    rc = EXIT_FAIL if status == "FAIL" else EXIT_INCONCLUSIVE
    if inventory_assessment is not None:
        by_scenario = {}
        for record in inventory_assessment["records"]:
            by_scenario.setdefault(record["scenario_id"], []).append(record["observation"])
        for record in records:
            record["owner_inventory_observations"] = by_scenario.get(record["scenario_id"], [])
    manifest = {"schema": "axia_p3_run_v1", "run_id": run_id,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "runner_source_sha": source_commit(root), "profile": "OFFLINE_FIXTURE_ONLY",
                "goal_sent": False, "fault_injected": False, "certified_estop": False,
                "runner_goal_sent": False, "runner_fault_injected": False,
                "capture_provenance_attested": False,
                "linked_evidence_sha256": linked_evidence_sha256,
                "linked_evidence_annotation_only": True,
                "owner_inventory_assessment": inventory_assessment,
                "input_sha256": {p.relative_to(root).as_posix(): sha256(p) for p in sorted((root / "scenarios").glob("S[0-9][0-9]_*.json")) + [pnu_path]},
                "records": records}
    atomic_json(dest / "manifest.json", manifest)
    summary = {"run_id": run_id, "status": status, "exit_code": rc,
               "runner_ready_offline": source_commit(root) is not None and all(r["status"] != "FAIL" for r in records),
               "demo_package_ready": False, "formal_accepted": False,
               "owner_inventory_assessment": inventory_assessment,
               "linked_source_evidence": linked_source_evidence,
               "linked_evidence_sha256": linked_evidence_sha256,
               "gates": {g: "NOT_ACCEPTED" for g in ("G08", "G09", "G10", "G11")},
               "records": records}
    atomic_json(dest / "summary.json", summary)
    with (dest / "audit_events.jsonl").open("w", encoding="utf-8") as audit:
        for r in records:
            audit.write(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                    "event": "SCENARIO_VERDICT", "scenario_id": r["scenario_id"],
                                    "status": r["status"], "verification_level": r["verification_level"],
                                    "source_sha": r["source_sha"], "goal_sent": False,
                                    "gate_accepted": False, "certified_estop": False},
                                   sort_keys=True, ensure_ascii=False) + "\n")
    (dest / "summary.md").write_text(
        "# AXIA P3 — " + status + "\n\nOffline fixture runner; no Goal, fault, ROS or Gazebo was executed.\n\n"
        + "\n".join(f"- {r['scenario_id']}: {r['status']} ({r['verification_level']}; reference={r['reference_level']})" for r in records)
        + "\n\nFormal G08–G11: NOT_ACCEPTED. SW_STOP is not a certified hardware E-Stop.\n", encoding="utf-8")
    with (dest / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("scenario_id", "gate", "status", "measurement_level", "goal_result", "fault_latency_sec", "stop_latency_sec"))
        for r in records:
            w.writerow((r["scenario_id"], r["gate"], r["status"], r["verification_level"], "NOT_MEASURED", "", ""))
    suite = ET.Element("testsuite", name="axia_p3_offline", tests=str(len(records)))
    for r in records:
        case = ET.SubElement(suite, "testcase", classname="axia.p3", name=r["scenario_id"])
        if r["status"] == "FAIL":
            ET.SubElement(case, "failure", message="PNU_ORACLE_MISMATCH")
        elif r["status"] == "NOT_VERIFIED":
            ET.SubElement(case, "skipped", message="REFERENCE_NOT_RAW_EVIDENCE")
    ET.ElementTree(suite).write(dest / "junit.xml", encoding="utf-8", xml_declaration=True)
    lines = [sha256(p) + "  " + p.name for p in sorted(dest.iterdir()) if p.is_file()]
    (dest / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rc, dest


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="AXIA P3 offline fixture validation; NEVER sends Goal/Fault")
    p.add_argument("--scenario", choices=["all", "S01", "S02", "S03", "S04", "S05"], default="all")
    p.add_argument("--results-root", type=Path, default=Path("results/p3"))
    p.add_argument("--evidence-dir", type=Path, default=None, help="optional hash-linked offline JSONL replays, NOT L3 proof")
    p.add_argument("--owner-inventory", type=Path, default=None,
                   help="optional read-only Owner inventory; metadata only, NEVER L2/L3 proof")
    p.add_argument("--allow-partial-ci", action="store_true", help="CI-only: tolerate NOT_VERIFIED; does not change verdict")
    args = p.parse_args(argv)
    try:
        rc, dest = run(results_root=args.results_root, selected=args.scenario, evidence_dir=args.evidence_dir,
                       owner_inventory=args.owner_inventory)
        print(json.dumps({"run_dir": str(dest), "status": "INCONCLUSIVE" if rc == EXIT_INCONCLUSIVE else "FAIL",
                          "gate_accepted": False, "profile": "OFFLINE_FIXTURE_ONLY", "exit_code": rc}))
        return EXIT_PASS if args.allow_partial_ci and rc == EXIT_INCONCLUSIVE else rc
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("P3_RUNNER_ERROR " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
