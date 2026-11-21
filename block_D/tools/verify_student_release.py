"""AXIA BLOCK_D final: one-shot, offline, student-only release verifier.

Purpose: verify the published *starter* package, not that students completed TODOs.
D13 and D14 must have their exact intentional RED tests; D15 must pass.
No ROS, Gazebo, robot control, Goal, network, instructor checkout or unsafe reset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_G07_BLOBS = {
    "block_B/day07/h01_runtime/docs/AXIA_G07_TASK04_DEMO_BASELINE_20261119_KO.md":
        "4d255be8eca57ca9447474e62063d43892f9bfb8",
    "block_B/day07/h01_runtime/ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_base_guard_node.py":
        "cfcc7d53d0e7d2fbd0450f80332f6ddc3e4c2f9f",
    "block_B/day07/h01_runtime/ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_supervisor_node.py":
        "920f36c966c7b72a858e73e120bc36598948f5d2",
    "block_B/day07/h01_runtime/tools/p2_g07_ci_moving_goal.py":
        "8bf6c00209f106a5c68f2fc5c57542654932bce4",
}

def git_blob_sha1(path: Path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def _run(cmd: list[str], *, cwd: Path, log_file: Path, timeout: int=60) -> tuple[int,str]:
    result = subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,timeout=timeout,check=False)
    text = result.stdout or ""
    log_file.write_text(text,encoding="utf-8")
    return result.returncode, text

def _require(cond, description):
    if not cond:
        raise RuntimeError("BLOCK_D_RELEASE_CONTRACT_FAIL: " + description)

def verify_release(root: Path=ROOT, out: Path=Path("/tmp/axia_block_d_final")) -> dict:
    root, out = Path(root).resolve(), Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)

    for rel, expected in EXPECTED_G07_BLOBS.items():
        _require(git_blob_sha1(root/rel)==expected,"G07 immutable baseline blob "+rel)
    _require(git_blob_sha1(root/"block_D/release/RELEASE_MANIFEST.json")==
             "0b05d08d5bb5bbecaf94c0f41360a0168754708f",
             "Stage 1 release manifest was modified")

    _require('return "U"' in (root/"block_D/day13/reachability_student.py").read_text(),
             "D13 starter TODO must remain intentionally unfinished")
    _require("D14_TODO_NOT_IMPLEMENTED" in (root/"block_D/day14/risk_policy_student.py").read_text(),
             "D14 starter TODO must remain intentionally unfinished")
    for private in ("p3_oracles.py","p3_g09_risk_policy.py","p3_g10_compound.py",
                    "INSTRUCTOR_ANSWER_KEY_KO.md"):
        _require(not list((root/"block_D").rglob(private)),
                 "Instructor answer leaked into Student block_D: "+private)

    report={"schema":"axia.block_d.final_student_l0.v1",
            "status":"PENDING","new_ros_gazebo_goal_executed":False,
            "teacher_answer_published":False,
            "g07_runtime_immutable":True,
            "baseline_proof":"REUSED_PREVIOUS_G07_JRCIGOL_PUBLIC_DERIVED_ONLY",
            "student_solutions_completed":False,
            "scope":"STUDENT_STARTER_CONTRACT_OFFLINE_L0_NOT_HARDWARE_ESTOP"}
    for day, total, failures, cli_rc in (("D13",10,2,2),("D14",20,11,2),("D15",18,0,0)):
        d=day.lower()
        dayout=out/d
        dayout.mkdir(parents=True,exist_ok=True)
        rc,log=_run([sys.executable,"-m","unittest","discover",
                     "-s",f"block_D/day{day[-2:]}/tests","-p","test_*.py","-v"],
                     cwd=root,log_file=dayout/"unittest.log")
        matched=re.findall(r"Ran (\d+) tests?",log)
        _require(bool(matched) and int(matched[-1])==total,
                 day+" tests count wrong; see "+str(dayout/"unittest.log"))
        if failures:
            _require(rc==1 and f"FAILED (failures={failures})" in log,
                     day+f" starter expected {failures} intentional RED tests only")
        else:
            _require(rc==0 and re.search(r"\bOK\b",log) is not None,
                     day+" evidence unit tests must be all GREEN")

        rc2,clog=_run([sys.executable,f"block_D/day{day[-2:]}/run_lab.py",
                       "--out",str(dayout)],
                      cwd=root,log_file=dayout/"runner.log")
        _require(rc2==cli_rc,day+f" runner exit code should be {cli_rc}")
        record={"test_count":total,"expected_failures":failures,
                "test_exit_code":rc,"runner_exit_code":rc2,
                "release_case_status":"INTENTIONAL_STUDENT_RED" if failures else "EVIDENCE_L0_GREEN"}
        if day=="D13":
            raw=json.loads((dayout/"d13_results.json").read_text())
            _require(len(raw["cases"])==8 and sum(bool(x["pass"]) for x in raw["cases"])==6
                and {x["id"] for x in raw["cases"] if not x["pass"]}==
                  {"P_same_time_overlap","N_same_route_different_time"},
                "D13 exact two expected P/N student TODO cases")
            _require((dayout/"P_same_time_overlap.html").is_file(),"D13 local P viewer absent")
            record["case_count"],record["expected_case_pass"]=8,6
        elif day=="D14":
            raw=json.loads((dayout/"d14_policy_results.json").read_text())
            _require(len(raw["cases"])==16 and sum(bool(x["pass"]) for x in raw["cases"])==2,
                     "D14 expected 16 cases and two early non-implemented baseline passes")
            _require((dayout/"d14_policy_timeline.html").is_file(),"D14 SVG timeline missing")
            record["case_count"],record["expected_case_pass"]=16,2
        else:
            raw=json.loads((dayout/"d15_evidence_review.json").read_text())
            _require(raw["baseline"]["numeric_gate"]=="EDUCATION_NUMERIC_ACCEPTED",
                     "D15 G07 preserved numeric contract")
            _require(raw["baseline"]["raw_machine_status"]=="HOLD_RAW_REVIEW_AND_VISUAL_PENDING",
                     "D15 original HOLD must never be changed")
            _require(raw["baseline"]["formal_accepted"] is False
                     and raw["baseline"]["certified_estop"] is False
                     and raw["baseline"]["visual_verified"] is False
                     and raw["baseline"]["first_violation_timestamp"] is None,
                     "D15 formal/GUI/ESTOP/first-timestamp status falsely promoted")
            _require(len(raw["snapshots"])==7 and len(raw["counterexamples"])==5,
                     "D15 evidence snapshots or mutation count wrong")
            _require(all(z["detected"] and z["not_accepted"] for z in raw["counterexamples"]),
                     "D15 a tampered evidence sample was not rejected")
            _require(raw["pnu_separation"]["safe_separation"]
                     and raw["pnu_separation"]["g07_owner_human_detector_attested"] is False,
                     "D13/D14 synthetic PNU misattributed to jrCIgoGl actual Owner")
            _require((dayout/"d15_offline_replay.html").is_file(),
                     "D15 read-only HTML evidence timeline missing")
            record["negative_mutations_detected"]=5
            record["seven_ordinal_stages"]=7
        report[day]=record
        print(f"BLOCK_D_{day}_STARTER_L0_PASS tests={total} intended_red={failures} cli_rc={rc2}")

    report["status"]="BLOCK_D_RELEASE_STUDENT_CONTRACT_PASS"
    (out/"BLOCK_D_RELEASE_RESULT.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("BLOCK_D_RELEASE_STUDENT_CONTRACT_PASS=1 ROS_GAZEBO_OWNER_GOAL_NOT_RUN=1")
    print("BLOCK_D_RELEASE_REPORT="+str(out/"BLOCK_D_RELEASE_RESULT.json"))
    return report

def main():
    p=argparse.ArgumentParser(description="AXIA BLOCK_D final synthetic release check")
    p.add_argument("--out",type=Path,required=True,
                   help="private temporary output, e.g. /tmp/axia-block-d-final")
    args=p.parse_args()
    verify_release(ROOT,args.out)

if __name__=="__main__":
    main()
