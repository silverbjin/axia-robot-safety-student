#!/usr/bin/env python3
"""Offline read-only Day02 release verification; never launches ROS, Gazebo or Goals."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
DAY02=Path(__file__).resolve().parents[1]
MANIFEST=DAY02/"COURSE_RELEASE_MANIFEST.json"
def blob_sha(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def validate(root=ROOT,manifest_path=MANIFEST):
    try:
        m=json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as exc:
        return {"status":"FAIL_L0_RELEASE_MANIFEST","errors":[type(exc).__name__],"ros_gazebo_run":False,"goal_sent":False}
    bad=[]
    if m.get("schema")!="axia.day02.complete_mvp.classroom_release.v1":
        bad.append("INVALID_RELEASE_SCHEMA")
    if m.get("source_commit_sha")!="f7edb2d126502eeeed58ae014adadc7a2096d41b":
        bad.append("INVALID_STUDENT_PIN")
    ci=m.get("proven_ci",{})
    if ci.get("workflow_sha")!="64ba0161e66126b4743b4b12a859f4a5349ae58a" or ci.get("run_id")!=44965035965 or len(ci.get("job_ids",[]))!=2:
        bad.append("UNVERIFIED_NATIVE_RUN_PIN")
    owner=m.get("owner_raw_review",{})
    if owner.get("report_commit_sha")!="c2c4f66c532be2a41855239860b9a9f5d60c4586" or owner.get("scope")!="L3_OWNER_NUMERIC_AND_LIFECYCLE_RAW_REVIEW_PASS_SCOPED" or owner.get("original_auto_verdict")!="HOLD_RAW_REVIEW_AND_VISUAL_PENDING":
        bad.append("OWNER_SCOPE_CHANGED")
    lim=m.get("scope_limits",{})
    if lim.get("certified_estop") is not False or lim.get("safety_ttl_changes") is not False or lim.get("ros_gazebo_in_this_release_verifier")!="NOT_RUN" or lim.get("student_git_main_merged") is not False:
        bad.append("SAFETY_OR_MAIN_POLICY_CHANGED")
    locked=m.get("locked_runtime_blobs")
    if not isinstance(locked,dict) or len(locked)!=8:
        bad.append("INVALID_SOURCE_FILE_COUNT")
        locked={}
    matched=0
    for rel,want in locked.items():
        if not isinstance(rel,str) or not rel.startswith("block_B/day07/h01_runtime/") or ".." in Path(rel).parts:
            bad.append("INVALID_LOCKED_SOURCE_PATH")
            continue
        f=root/rel
        if not f.is_file():
            bad.append("MISSING_RUNTIME_FILE:"+rel)
        elif blob_sha(f)!=want:
            bad.append("RUNTIME_BLOB_DRIFT:"+rel)
        else:
            matched+=1
    flagged=[str(p.relative_to(DAY02)) for p in DAY02.rglob("*") if p.is_file() and (p.name.lower().startswith(("solution","hidden_test")) or p.suffix.lower() in (".pt",".onnx",".db3"))]
    if flagged: bad.append("PRIVATE_PAYLOAD_IN_RELEASE:"+",".join(flagged))
    return {"schema":"axia.day02.verify_release.v1","status":"L0_RELEASE_CONTRACT_PASS" if not bad else "FAIL_L0_RELEASE_CONTRACT","checked_runtime_blobs":matched,"expected_runtime_blobs":len(locked),"source_commit_sha":m.get("source_commit_sha"),"public_ci_native_l2":"REUSED_2_OF_2_NOT_RERUN","owner_l3":"REUSED_PASS_SCOPED_NOT_RERUN","ros_gazebo_run":False,"goal_sent":False,"certified_estop":False,"errors":bad}
def main():
    p=argparse.ArgumentParser(description="L0 only, no physical or simulated Goal")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    result=validate()
    output=json.dumps(result,ensure_ascii=False,sort_keys=True)
    print(output)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(output+"\n",encoding="utf-8")
    return 0 if result["status"]=="L0_RELEASE_CONTRACT_PASS" else 2
if __name__=="__main__":sys.exit(main())
