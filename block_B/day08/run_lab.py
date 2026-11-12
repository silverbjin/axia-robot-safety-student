#!/usr/bin/env python3
"""D08 four-hour online integration runner. Python-only fixture replay."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import sys
import shutil
from pathlib import Path
from block_B.day08.integration_todo import integrate_case

FIXTURE=Path(__file__).parent/"fixtures"/"d08_synthetic_cases.json"
CSV_FIELDS=("case_id","person_detected","distance_m","range_status",
            "route_status","advice","expected_ratio")

def _reject_constant(value):
    raise ValueError("D08_BAD_JSON_CONSTANT:"+str(value))

def run(fixture:Path,out:Path):
    try:
        if fixture.is_symlink() or not fixture.is_file():
            raise ValueError("D08_FIXTURE_NOT_FOUND")
        if out.exists() or out.is_symlink():
            raise ValueError("D08_OUTPUT_MUST_NOT_EXIST")
        original=fixture.read_bytes()
        data=json.loads(original.decode("utf-8"),parse_constant=_reject_constant)
        if (not isinstance(data,dict)
          or data.get("schema")!="axia.d08.offline_integration.v1"
          or data.get("source")!="SYNTHETIC_COURSE_FIXTURE"
          or data.get("real_person_observed") is not False
          or data.get("ros_actual") is not False or data.get("gazebo_actual") is not False
          or data.get("position_source")!="SYNTHETIC_MAP_PROXY_NOT_CAMERA_TF"
          or not isinstance(data.get("routes"),dict)
          or not isinstance(data.get("cases"),list) or len(data["cases"])!=6):
            raise ValueError("D08_SYNTHETIC_FIXTURE_SCHEMA_INVALID")
        results=[integrate_case(c,data["routes"]) for c in data["cases"]]
        for case,result in zip(data["cases"],results):
            if (not isinstance(case.get("expected"),dict) or
                any(result.get(k)!=v for k,v in case["expected"].items())):
                raise ValueError("D08_OUTPUT_DOES_NOT_MATCH_CASE:"+str(case.get("case_id")))
        report={"schema":"axia.d08.report.v1",
          "source":"D08_SYNTHETIC_CLASSROOM","verified_level":"PYTHON_ONLY",
          "status":"D08_EDU_PYTHON_L0_COMPLETE",
          "fixture_sha256":hashlib.sha256(original).hexdigest(),
          "case_count":len(results),"results":results,
          "ros_verified":False,"gazebo_verified":False,"robot_moved":False,
          "collision_free_verified":False,"control_published":False,
          "safety_certified":False}
        out.mkdir(parents=True,exist_ok=False)
        with (out/"trace.csv").open("w",newline="",encoding="utf-8") as fp:
            writer=csv.DictWriter(fp,fieldnames=CSV_FIELDS,extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        (out/"summary.json").write_text(
            json.dumps(report,indent=2,allow_nan=False,ensure_ascii=False)+"\n",
            encoding="utf-8")
        # Snapshot the student's own D08 solution for ZIP grading; no teacher
        # reference, existing D04-D07 sources, secrets or private tests.
        solution=Path(__file__).parent/"integration_todo.py"
        if solution.is_symlink() or not solution.is_file():
            raise ValueError("D08_STUDENT_SOURCE_UNAVAILABLE")
        shutil.copyfile(solution,out/"integration_todo.py")
        print(f"D08_PYTHON_FIXTURE_REPLAY_PASS cases={len(results)} out={out}")
        return 0
    except (ValueError,KeyError,TypeError,NotImplementedError,UnicodeError,OSError) as exc:
        print(f"D08_LAB_BLOCKED:{type(exc).__name__}:{exc}",file=sys.stderr)
        return 2

def main():
    p=argparse.ArgumentParser(description="D08 offline D04-D07 integration; no ROS")
    p.add_argument("--fixture",type=Path,default=FIXTURE)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    return run(a.fixture,a.out)

if __name__=="__main__":
    raise SystemExit(main())
