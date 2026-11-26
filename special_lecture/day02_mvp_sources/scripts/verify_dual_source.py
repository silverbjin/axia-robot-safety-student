#!/usr/bin/env python3
"""AXIA DAY02 G07 complete-source custody check (L0, ROS/Gazebo never launched)."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DIR=Path(__file__).resolve().parents[1]
MANIFEST=DIR/"DUAL_SOURCE_MANIFEST.json"
EXPECTED={
"accepted":("f7edb2d126502eeeed58ae014adadc7a2096d41b","1ad1d424358345420b8bfc67a6a7ca44d634a974",186,"2_OF_2_PASS"),
"failed":("a04f9a7da8d54bbd9f944d05388792cb706adf28","0d44f39c8f5927d21411c33e7a793ca1a3f6f368",187,"0_OF_2_FAIL"),
}
PACKAGES=("axia_fault_injector","axia_safety_bringup","axia_safety_supervisor","axia_scenario_verifier")
SRC_TREE="767c3d10187280303f5226a90ede205eb0059033"

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True,stderr=subprocess.PIPE).strip()

def verify(root=ROOT,manifest_path=MANIFEST):
    issues=[]
    try:
        m=json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as e:
        return {"status":"DUAL_G07_SOURCE_CUSTODY_L0_FAIL","issues":["MANIFEST_UNAVAILABLE:"+type(e).__name__],
                "ros_gazebo_run":False,"new_colcon_build":False}
    if m.get("schema")!="axia.day02.dual_g07_full_source_build.v1":
        issues.append("INVALID_SCHEMA")
    if m.get("packages")!=list(PACKAGES):
        issues.append("PACKAGE_LIST_CHANGED")
    b=m.get("build_contract",{})
    if (b.get("ros_distro")!="jazzy" or b.get("certified_estop") is not False
        or b.get("no_ros_goal") is not True or b.get("no_gazebo_run") is not True
        or b.get("new_l2_l3_evidence")!="NOT_RUN"):
        issues.append("SAFETY_SCOPE_CHANGED")
    checked={}
    for label,(source_sha,runtime_sha,count,verdict) in EXPECTED.items():
        record=m.get(label,{})
        sub="special_lecture/day02_mvp_sources/"+label+"/runtime"
        rootpath=root/sub
        if (record.get("runtime_source_sha")!=source_sha
            or record.get("runtime_tree_sha")!=runtime_sha
            or record.get("ros2_src_tree_sha")!=SRC_TREE
            or record.get("runtime_file_count")!=count
            or record.get("native_moving_l2")!=verdict):
            issues.append("MANIFEST_SOURCE_DRIFT:"+label)
        if label=="failed" and (record.get("root_cause")!="UNDETERMINED"
            or record.get("owner_l3")!="NOT_RUN"):
            issues.append("UNSUPPORTED_FAILED_ACCEPTANCE")
        if label=="accepted" and record.get("original_auto_verdict")!="HOLD_RAW_REVIEW_AND_VISUAL_PENDING":
            issues.append("OVERWRITTEN_ORIGINAL_HOLD")
        if not rootpath.is_dir():
            issues.append("SOURCE_MISSING:"+label)
            continue
        try:
            actual=git(root,"rev-parse","HEAD:"+sub)
            src=git(root,"rev-parse","HEAD:"+sub+"/ros2_ws/src")
            dirty=git(root,"status","--porcelain","--untracked-files=all","--",sub)
            paths=git(root,"ls-tree","-r","--name-only","HEAD",sub).splitlines()
        except (OSError,subprocess.CalledProcessError):
            issues.append("GIT_INSPECTION_FAILED:"+label)
            continue
        if actual!=runtime_sha:issues.append("RUNTIME_GIT_TREE_DRIFT:"+label)
        if src!=SRC_TREE:issues.append("ROS_SOURCE_TREE_DRIFT:"+label)
        if dirty:issues.append("WORKTREE_MODIFIED:"+label)
        if len(paths)!=count:issues.append("FILE_COUNT_DRIFT:"+label)
        for name in PACKAGES:
            srcfile=rootpath/"ros2_ws/src"/name/"package.xml"
            if not srcfile.is_file():issues.append("ROS_PACKAGE_MISSING:"+label+":"+name)
        checked[label]={"git_tree_sha":actual,"ros2_src_tree_sha":src,"files":len(paths),
                        "source_sha":source_sha,"historical_native_l2":verdict}
    return {"schema":"axia.day02.dual_source_audit.v1",
        "status":"DUAL_G07_SOURCE_CUSTODY_L0_PASS" if not issues else "DUAL_G07_SOURCE_CUSTODY_L0_FAIL",
        "checked":checked,"ros_gazebo_run":False,"new_colcon_build":False,
        "certified_estop":False,"issues":issues}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--json-out",type=Path)
    a=p.parse_args()
    r=verify()
    s=json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True)
    print(s)
    if a.json_out:
        dest=a.json_out.expanduser()
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            with dest.open("x",encoding="utf-8") as f:f.write(s+"\n")
        except FileExistsError:
            print("FAIL_OUTPUT_EXISTS_NO_OVERWRITE",file=sys.stderr)
            return 3
    return 0 if r["status"]=="DUAL_G07_SOURCE_CUSTODY_L0_PASS" else 3

if __name__=="__main__":
    sys.exit(main())
