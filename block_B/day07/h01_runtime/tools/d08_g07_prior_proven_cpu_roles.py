#!/usr/bin/env python3
"""D08 sim-only reuses Cycle36's real-L2-proven G07 CPU role partition.

This is an OS scheduling hypothesis, not a safety algorithm or a release
claim. Prior G07 exact real L2 #43863443121: 4 CPU roles CM {1,2},
Gazebo physical server {3}, observer/GUI CPU0. Keep Guard 150ms, CM
120ms and Scan300ms unchanged; actual current-D08 moving L2 is required.

Only an EXACT run-owned official CM executable and Gazebo physics-server
process may be adjusted. No shell pkill, no unowned taskset, no ROS
publishers, no Goal/stop decision. Fail CLOSED before a moving Goal.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

SERVER_ONE = re.compile(r"^gz sim -r -s (/tmp/nav2_[A-Za-z0-9_]+\\.sdf)$")
SERVER_PATH = re.compile(r"^/tmp/nav2_[A-Za-z0-9_]+\\.sdf$")
SHA40 = re.compile(r"^[a-f0-9]{40}$")


def choose_cpu_roles(allowed):
    if not isinstance(allowed,(set,list,tuple)) or any(
            type(c) is not int or c < 0 for c in allowed):
        raise ValueError("D08_G07_C36_ALLOWED_CPU_SET_INVALID")
    cpus = sorted(set(allowed))
    if len(cpus) < 4:
        raise ValueError("D08_G07_C36_NEEDS_AT_LEAST_FOUR_AVAILABLE_CORES")
    cm = {cpus[1], cpus[-2]}
    server = set(cpus) - cm - {cpus[0]}
    if len(cm)!=2 or not server or (cm & server):
        raise ValueError("D08_G07_C36_NONOVERLAP_CPU_CONTRACT_FAILED")
    return cm, server


def _official_server(argv):
    if not isinstance(argv,(tuple,list)) or not argv or any(type(a) is not str for a in argv):
        return False
    if len(argv)==1:
        return SERVER_ONE.fullmatch(argv[0]) is not None
    return (len(argv)==5 and Path(argv[0]).name=="gz" and
            list(argv[1:4])==["sim","-r","-s"] and
            SERVER_PATH.fullmatch(argv[4]) is not None)


def _official_cm(argv):
    return (isinstance(argv,(list,tuple)) and len(argv)>=1
            and type(argv[0]) is str
            and Path(argv[0]).name=="collision_monitor"
            and "/nav2_collision_monitor/" in argv[0])


def match_roles(rows,launch_pgid,uid):
    if type(launch_pgid) is not int or launch_pgid<2 or type(uid) is not int:
        raise ValueError("D08_G07_C36_OWNERSHIP_ARGUMENT_INVALID")
    cms=[];gz=[]
    for row in rows:
        if not isinstance(row,(list,tuple)) or len(row)!=4:
            continue
        pid,group,argv,owner=row
        if type(pid) is not int or type(group) is not int or type(owner) is not int:
            continue
        if pid<2 or group!=launch_pgid or owner!=uid:
            continue
        if _official_cm(argv):
            cms.append(pid)
        if _official_server(argv):
            gz.append(pid)
    if len(cms)!=1 or len(gz)!=1 or cms[0]==gz[0]:
        raise ValueError("D08_G07_C36_ONE_OWNED_CM_AND_GZ_SERVER_NOT_UNIQUE")
    return cms[0],gz[0]


def validate_scope(env):
    needs={
      "GITHUB_ACTIONS":"true",
      "AXIA_P0_SIM_ONLY":"1",
      "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
      "AXIA_G07_TASK04_CI_GUI_MOVING":"1",
      "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
      "AXIA_D08_G07_SINGLE_SESSION":"1",
      "AXIA_G07_OWNER_STARTUP_PARITY":"1",
      "AXIA_D08_G07_CPU_ROLE_C36":"1",
    }
    if any(env.get(key)!=value for key,value in needs.items()):
        raise ValueError("D08_G07_C36_CI_SIM_ONLY_SCOPE_NOT_AUTHORIZED")
    if env.get("AXIA_G07_TASK04_OWNER_MOVING_L3")=="1":
        raise ValueError("D08_G07_C36_OWNER_NOT_ADMITTED")
    return True


def _proc_rows():
    rows=[]
    for item in Path("/proc").iterdir():
        if not item.name.isdecimal():
            continue
        pid=int(item.name)
        try:
            raw=(item/"cmdline").read_bytes()
            if not raw:
                continue
            argv=[x.decode("utf-8","replace") for x in raw.rstrip(b"\\0").split(b"\\0")]
            rows.append((pid,os.getpgid(pid),argv,(item/"status").stat().st_uid))
        except (OSError,ProcessLookupError):
            continue
    return rows


def _role_threads(pid,pgid):
    task=Path("/proc")/str(pid)/"task"
    tids=sorted(int(p.name) for p in task.iterdir() if p.name.isdecimal())
    if pid not in tids or not tids:
        raise ValueError("D08_G07_C36_OWNED_ROLE_THREADS_MISSING")
    if any(os.getpgid(tid)!=pgid for tid in tids):
        raise ValueError("D08_G07_C36_ROLE_THREAD_SESSION_CHANGED")
    return tids


def run(launch_pgid,expected_sha,out,env=None):
    env=dict(os.environ if env is None else env)
    validate_scope(env)
    if not SHA40.fullmatch(expected_sha or ""):
        raise ValueError("D08_G07_C36_STUDENT_SHA_NOT_PINNED")
    if out.exists() or out.is_symlink() or not out.parent.is_dir():
        raise ValueError("D08_G07_C36_OUTPUT_NOT_FRESH")
    current=subprocess.check_output(
        ["git","rev-parse","HEAD"],text=True,timeout=5).strip()
    if current!=expected_sha:
        raise ValueError("D08_G07_C36_RUN_SOURCE_SHA_MISMATCH")
    if not env.get("GZ_PARTITION","").startswith("axia_p2_"):
        raise ValueError("D08_G07_C36_ISOLATED_GAZEBO_PARTITION_MISSING")
    allowed=set(os.sched_getaffinity(0))
    cm_cores,gz_cores=choose_cpu_roles(allowed)
    cm_pid,gz_pid=match_roles(_proc_rows(),launch_pgid,os.geteuid())
    cm_threads=_role_threads(cm_pid,launch_pgid)
    gz_threads=_role_threads(gz_pid,launch_pgid)
    if not SERVER_PATH.fullmatch(
            next((v[-1] for _,pgid,argv,uid in _proc_rows()
                  if pgid==launch_pgid and uid==os.geteuid() and
                  _official_server(argv) for v in [argv]),"")):
        # The one-arg form is already validated in match_roles, but cannot
        # yield a final argv element that is the SDF path; use /proc role
        # ownership rather than silently admitting another process.
        pass
    # Only after validating BOTH roles and their thread ownership: pin
    # EVERY currently existing TID of the actual official CM and gz server.
    for tid in cm_threads:
        os.sched_setaffinity(tid,cm_cores)
    for tid in gz_threads:
        os.sched_setaffinity(tid,gz_cores)
    if any(set(os.sched_getaffinity(t))!=cm_cores for t in cm_threads):
        raise ValueError("D08_G07_C36_CM_AFFINITY_READBACK_MISMATCH")
    if any(set(os.sched_getaffinity(t))!=gz_cores for t in gz_threads):
        raise ValueError("D08_G07_C36_GZ_AFFINITY_READBACK_MISMATCH")
    result={"status":"D08_G07_C36_GAZEBO_CM_CPU_ROLE_READBACK_PASS_NO_GOAL",
         "source_sha":expected_sha,"session_pgid":launch_pgid,
         "cm_pid":cm_pid,"gz_pid":gz_pid,
         "cm_cores":sorted(cm_cores),"gz_server_cores":sorted(gz_cores),
         "cm_threads":len(cm_threads),"gz_threads":len(gz_threads),
         "goal_sent":False,"guard_ttl_modified":False,
         "scan_ttl_modified":False,"cm_release_120ms_verified":False,
         "moving_l2_accepted":False,"certified_estop":False}
    with out.open("x",encoding="utf-8") as file:
        json.dump(result,file,indent=2,sort_keys=True)
        file.write("\\n")
    print("D08_G07_C36_REAL_OWNED_CM_SERVER_CPU_ROLE_PASSED_NO_GOAL "
          +json.dumps({"cm_cores":sorted(cm_cores),
                        "gz_cores":sorted(gz_cores),
                        "cm_threads":len(cm_threads),
                        "gz_threads":len(gz_threads)},sort_keys=True),
          flush=True)
    return 0


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--launch-pgid",type=int,required=True)
    ap.add_argument("--expected-sha",required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        raise SystemExit(run(args.launch_pgid,args.expected_sha,args.output))
    except (ValueError,OSError,subprocess.SubprocessError,PermissionError) as exc:
        print("D08_G07_C36_CPU_PARTITION_BLOCKED_BEFORE_GOAL "+
              type(exc).__name__+":"+str(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
