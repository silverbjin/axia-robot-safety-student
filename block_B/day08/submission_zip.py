#!/usr/bin/env python3
"""D08 online ZIP packager, allowlisted files only. No solution/secret copying.

This is an evidence container (student code/test logs), not a safety proof.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

REQUIRED=("summary.json","trace.csv","pytest.txt","integration_todo.py")
SAFETY_FLAGS=("ros_verified","gazebo_verified","robot_moved",
              "collision_free_verified","control_published","safety_certified")
MAX_FILE_BYTES=1_048_576

def _parse_constant(value):
    raise ValueError("D08_NONSTANDARD_JSON_CONSTANT:"+str(value))

def _validate_summary(raw,trace,pytest_text):
    summary=json.loads(raw.decode("utf-8"),parse_constant=_parse_constant)
    if (not isinstance(summary,dict)
            or summary.get("schema")!="axia.d08.report.v1"
            or summary.get("source")!="D08_SYNTHETIC_CLASSROOM"
            or summary.get("verified_level")!="PYTHON_ONLY"
            or summary.get("status")!="D08_EDU_PYTHON_L0_COMPLETE"
            or summary.get("case_count")!=6
            or not re.fullmatch("[a-f0-9]{64}",str(summary.get("fixture_sha256")))):
        raise ValueError("D08_REPORT_CONTRACT_INVALID")
    if any(summary.get(key) is not False for key in SAFETY_FLAGS):
        raise ValueError("D08_FORGED_REAL_WORLD_SAFETY_CLAIM")
    rows=summary.get("results")
    if not isinstance(rows,list) or len(rows)!=6:
        raise ValueError("D08_EXPECTED_SIX_CASE_RESULTS")
    expected_ids=[item.get("case_id") for item in rows if isinstance(item,dict)]
    if len(expected_ids)!=6 or len(set(expected_ids))!=6:
        raise ValueError("D08_CASE_IDS_INVALID")
    for row in rows:
        if (any(row.get(key) is not False for key in SAFETY_FLAGS)
                or row.get("source")!="D08_SYNTHETIC_CLASSROOM"
                or row.get("verified_level")!="PYTHON_ONLY"
                or row.get("range_status") not in ("CLEAR","SLOWDOWN","STOP","UNKNOWN")
                or row.get("advice") not in ("UNKNOWN_REVIEW","STOP_EXPECTED",
                              "SLOWDOWN_EXPECTED","REPLAN_REVIEW","MONITOR_ONLY")):
            raise ValueError("D08_INVALID_OR_UNSAFE_CASE")
    text=trace.decode("utf-8")
    reader=csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "case_id" not in reader.fieldnames:
        raise ValueError("D08_TRACE_SCHEMA_INVALID")
    if [r.get("case_id") for r in reader]!=expected_ids:
        raise ValueError("D08_TRACE_REPORT_MISMATCH")
    if not re.search(r"(?m)^\d+ passed in \d+(?:\.\d+)?s\s*$",pytest_text):
        raise ValueError("D08_PYTEST_SUCCESS_EVIDENCE_MISSING")
    return summary

def package_submission(run_dir:Path,out:Path):
    created_by_this_call=False
    try:
        if (not run_dir.is_dir() or run_dir.is_symlink()
                or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()):
            raise ValueError("D08_OUTPUT_OR_SOURCE_INVALID")
        data={}
        for name in REQUIRED:
            f=run_dir/name
            if f.is_symlink() or not f.is_file():
                raise ValueError("D08_REQUIRED_FILE_MISSING_OR_SYMLINK:"+name)
            if f.stat().st_size>MAX_FILE_BYTES:
                raise ValueError("D08_FILE_TOO_LARGE:"+name)
            data[name]=f.read_bytes()
        _validate_summary(data["summary.json"],data["trace.csv"],
                          data["pytest.txt"].decode("utf-8"))
        checksums="".join(hashlib.sha256(data[n]).hexdigest()+"  "+n+"\n"
                          for n in REQUIRED).encode("ascii")
        with out.open("xb") as fp:
            created_by_this_call=True
            with zipfile.ZipFile(fp,"w",compression=zipfile.ZIP_DEFLATED,allowZip64=False) as z:
                for name in (*REQUIRED,"SHA256SUMS"):
                    payload=data.get(name,checksums)
                    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED
                    info.external_attr=0o600<<16
                    z.writestr(info,payload)
        with zipfile.ZipFile(out) as z:
            if (set(z.namelist())!=set((*REQUIRED,"SHA256SUMS"))
                    or z.testzip() is not None):
                raise ValueError("D08_ZIP_INTEGRITY_FAILED")
        print(f"D08_SUBMISSION_ZIP_PASS output={out} files=5 PYTHON_ONLY")
        return 0
    except (ValueError,TypeError,KeyError,OSError,UnicodeError,zipfile.BadZipFile) as exc:
        # The caller must never receive a partial successful-looking ZIP.
        if created_by_this_call:
            try:
                out.unlink(missing_ok=True)
            except OSError:
                pass
        print(f"D08_ZIP_BLOCKED:{type(exc).__name__}:{exc}",file=sys.stderr)
        return 2

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--run-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    return package_submission(a.run_dir,a.out)

if __name__=="__main__":
    raise SystemExit(main())
