#!/usr/bin/env python3
"""AXIA D08 Actor RTF diagnostic. Passive subscriber; no robot control.

Run from a SECOND terminal while D08 Gazebo+RViz demo is running.
Collects current world stats, Actor SDF profile, process and memory snapshot,
and a ZIP report. Does not launch/stop Gazebo, publish ROS topics or goals.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

TOPIC = "/world/default/stats"
RTF = re.compile(r"(?m)^\s*real_time_factor:\s*([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?\d+)?)\s*$")
PAUSE = re.compile(r"(?m)^\s*paused:\s*(true|false)\s*$", re.I)
SIMTIME = re.compile(r"(?ms)\bsim_time\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)\s*\}")
SERVER_PATTERN = re.compile(r"gz sim|gz-sim-server|/gz\s+sim|nav2_bringup", re.I)

def latest_scene() -> Path | None:
    base=Path.home()/"axia_d04_student_evidence"
    if not base.is_dir():
        return None
    dirs=sorted(base.glob("d04-gazebo-*"),key=lambda p:p.stat().st_mtime,reverse=True)
    for d in dirs:
        p=d/"scene/student_human_world.sdf.xacro"
        if p.is_file():
            return p
    return None

def actor_profile(scene: Path | None) -> dict:
    if scene is None or not scene.is_file():
        return {"status":"SCENE_NOT_FOUND","waypoints":[]}
    try:
        root=ET.parse(scene).getroot()
        script=root.find(".//actor[@name='axia_student_person']/script")
        if script is None:
            return {"status":"ACTOR_MISSING","waypoints":[]}
        points=[]
        for wp in script.findall("trajectory/waypoint"):
            t=float(wp.findtext("time","nan"))
            pose=[float(v) for v in (wp.findtext("pose") or "").split()[:3]]
            if len(pose)!=3 or not all(math.isfinite(v) for v in [t,*pose]):
                return {"status":"INVALID_WAYPOINT","waypoints":[]}
            points.append({"sim_s":t,"x_m":pose[0],"y_m":pose[1],"z_m":pose[2]})
        if len(points)<2:
            return {"status":"INSUFFICIENT_WAYPOINTS","waypoints":points}
        segments=[]
        for a,b in zip(points,points[1:]):
            elapsed=b["sim_s"]-a["sim_s"]
            if elapsed<=0:
                return {"status":"INVALID_TIME_ORDER","waypoints":points}
            distance=math.hypot(b["x_m"]-a["x_m"],b["y_m"]-a["y_m"])
            segments.append({"duration_sim_s":elapsed,"distance_m":round(distance,6),
                             "speed_mps_sim":round(distance/elapsed,6)})
        return {"status":"PARSED","actor":"axia_student_person",
                "scene_path":str(scene),"waypoints":points,"segments":segments,
                "loop_sim_s":points[-1]["sim_s"]-points[0]["sim_s"]}
    except (OSError,ET.ParseError,ValueError) as e:
        return {"status":"SCENE_PARSE_BLOCKED","reason":str(e),"waypoints":[]}

def parse_stats(raw: str) -> dict:
    rates=[float(m.group(1)) for m in RTF.finditer(raw)]
    rates=[x for x in rates if 0<=x<=10]
    pauses=[m.group(1).lower()=="true" for m in PAUSE.finditer(raw)]
    seconds=[int(m.group(1))+int(m.group(2))*1e-9 for m in SIMTIME.finditer(raw)]
    result={"rtf_samples":len(rates),"pause_samples":len(pauses),
            "paused_all":bool(pauses) and all(pauses),
            "sim_time_samples":len(seconds),
            "sim_time_progress_s":round(seconds[-1]-seconds[0],6) if len(seconds)>1 else None}
    if rates:
        result.update(rtf_median=round(statistics.median(rates),4),
                      rtf_min=round(min(rates),4),rtf_max=round(max(rates),4),
                      rtf_p10=round(sorted(rates)[int((len(rates)-1)*.1)],4))
    return result

def diagnosis(stats: dict, actor: dict) -> dict:
    result={"category":"INCONCLUSIVE","no_goal":True,
            "gui_pixels_verified":False,"safety_ttl_verified":False,
            "physical_actor_speed_measured":False,
            "recommendation":"Collect real RTF and the original actor SDF."}
    if stats.get("paused_all"):
        result.update(category="SIM_PAUSED",recommendation="Check Gazebo pause state. Do not modify Actor or control code.")
        return result
    if stats.get("rtf_samples",0)<3 or "rtf_median" not in stats:
        result.update(category="RTF_NOT_MEASURED",recommendation="Measure /world/default/stats with correct GZ_PARTITION.")
        return result
    speed=stats["rtf_median"]
    if stats.get("sim_time_progress_s") is not None and stats["sim_time_progress_s"]<=0:
        result.update(category="SIM_TIME_STALLED",recommendation="World time did not progress. Inspect server/clock.")
        return result
    if speed<0.8:
        result.update(category="LOW_RTF_CANDIDATE",
                      recommendation="Inspect CPU/GPU/WSLg rendering and concurrent RGBD+YOLO load before changing actor code.")
    elif actor.get("status")=="PARSED" and actor.get("segments") and max(s["speed_mps_sim"] for s in actor["segments"])<0.25:
        result.update(category="SLOW_ACTOR_TRAJECTORY_CANDIDATE",
                      recommendation="With normal RTF, consider D08-only 0/2/4-s waypoint profile. Preserve D04/D05.")
    else:
        result.update(category="RTF_OK_GUI_FPS_UNVERIFIED",
                      recommendation="RTF is adequate; investigate GUI FPS using on-screen evidence, not PID alone.")
    if actor.get("status")=="PARSED":
        for seg in actor["segments"]:
            seg["estimated_wall_s_at_median_rtf"]=round(seg["duration_sim_s"]/speed,2) if speed>0 else None
            seg["estimated_wall_speed_mps"]=round(seg["speed_mps_sim"]*speed,4)
        result["actor_time_estimation_only"]=True
    return result

def detect_partition() -> tuple[str|None,dict]:
    if os.environ.get("GZ_PARTITION"):
        return os.environ["GZ_PARTITION"],{"source":"env"}
    found={}
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        try:
            cmd=(path/"cmdline").read_bytes().replace(b"\x00",b" ").decode(errors="replace")
            if not SERVER_PATTERN.search(cmd):
                continue
            for item in (path/"environ").read_bytes().split(b"\x00"):
                if item.startswith(b"GZ_PARTITION="):
                    p=item.split(b"=",1)[1].decode(errors="replace")
                    if p and ("axia" in p or "d04" in p or "d08" in p):
                        found.setdefault(p,[]).append(int(path.name))
                    break
        except (OSError,PermissionError,ProcessLookupError):
            pass
    if len(found)==1:
        p=next(iter(found))
        return p,{"source":"running_process","pids":found[p]}
    return None,{"source":"auto","candidates":found,
                 "hint":"Use --partition value from D04_STUDENT_GUI GZ_PARTITION=..."}

def capture_command(cmd,env=None,timeout=10):
    try:
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         text=True,env=env,timeout=timeout,check=False)
        return r.returncode,r.stdout[-80000:]
    except (OSError,subprocess.TimeoutExpired) as e:
        return 127,str(e)

def snapshot(out:Path):
    _,ps=capture_command(["ps","-eo","pid,ppid,pcpu,pmem,rss,etime,comm,args"])
    lines=ps.splitlines()
    rows=[s for s in lines[1:] if re.search("gz.sim|gz-sim|rviz2|yolo_ros|image_view|ros2.launch|ros_gz|nav2",s,re.I)]
    (out/"processes.txt").write_text((lines[0] if lines else "")+"\n"+"\n".join(rows[:100])+"\n")
    resources=["CPU % is cumulative ps data, not a per-second profiler.\n"]
    for cmd in (["free","-m"],["nproc"]):
        rc,val=capture_command(cmd,timeout=8)
        resources.append("$ "+" ".join(cmd)+f" [rc={rc}]\n"+val)
    (out/"resources.txt").write_text("\n".join(resources))

def report(out:Path,data:dict)->Path:
    (out/"summary.json").write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    diag=data["diagnosis"]
    stats=data["stats"]
    rows=["# AXIA D08 Actor RTF diagnosis (read-only)","",
          "- Category: "+diag["category"],
          "- Partition: "+str(data["gz_partition"]),
          "- RTF median: "+str(stats.get("rtf_median","NOT_MEASURED")),
          "- RTF samples: "+str(stats["rtf_samples"]),
          "- Sim time progression: "+str(stats["sim_time_progress_s"]),
          "- Actor scene status: "+data["actor"]["status"],
          "- Recommended next action: "+diag["recommendation"],"",
          "Estimated Actor wall speed is SDF×RTF, NOT a measured physical pose trace.",
          "This does NOT prove GUI pixels, ROS message TTL, Nav2 motion, safety or E-Stop."]
    (out/"REPORT.md").write_text("\n".join(rows)+"\n")
    archive=out/"d08_actor_rtf_diagnostics.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            if p.is_file() and p!=archive:
                z.write(p,arcname=p.name)
    return archive

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds",type=int,default=20)
    ap.add_argument("--partition",help="GZ_PARTITION from demo log (auto if absent)")
    ap.add_argument("--scene",help="original generated student_human_world.sdf.xacro")
    ap.add_argument("--out",help="new output directory only")
    ap.add_argument("--from-stats",help="offline synthetic stats file for CI; NOT real Gazebo")
    a=ap.parse_args()
    if not 5<=a.seconds<=90:
        ap.error("--seconds must be 5..90")
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=Path(a.out).expanduser() if a.out else Path.home()/"axia_d08_diagnostics"/f"rtf_{stamp}_{os.getpid()}"
    if out.exists():
        print("D08_DIAG_OUTPUT_EXISTS_NO_OVERWRITE="+str(out),file=sys.stderr)
        return 2
    out.mkdir(parents=True,mode=0o700)
    scene=Path(a.scene).expanduser() if a.scene else latest_scene()
    actor=actor_profile(scene)
    partition=a.partition
    detection={"source":"--partition"} if partition else {}
    raw=""
    capture="OFFLINE" if a.from_stats else "BLOCKED"
    if a.from_stats:
        raw=Path(a.from_stats).read_text(encoding="utf-8")
        (out/"world_stats_raw.txt").write_text(raw)
    else:
        if not partition:
            partition,detection=detect_partition()
        if not partition:
            capture="PARTITION_NOT_FOUND"
        elif not shutil.which("gz"):
            capture="GAZEBO_CLI_MISSING"
        else:
            env=os.environ.copy()
            env["GZ_PARTITION"]=partition
            rc,topics=capture_command(["gz","topic","-l"],env,timeout=12)
            (out/"gazebo_topics.txt").write_text(topics)
            if rc!=0 or TOPIC not in topics.splitlines():
                capture="WORLD_STATS_TOPIC_NOT_VISIBLE"
            else:
                capture="CAPTURED"
                with (out/"world_stats_raw.txt").open("wb") as fp:
                    proc=subprocess.Popen(["gz","topic","-e","-t",TOPIC],env=env,
                                          stdout=fp,stderr=subprocess.STDOUT,
                                          start_new_session=True)
                    try:
                        snapshot(out)
                        time.sleep(a.seconds)
                    finally:
                        try:
                            os.killpg(proc.pid,signal.SIGINT)
                        except ProcessLookupError:
                            pass
                        try:
                            proc.wait(timeout=4)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid,signal.SIGKILL)
                            proc.wait(timeout=4)
                raw=(out/"world_stats_raw.txt").read_text(encoding="utf-8",errors="replace")
    if not (out/"processes.txt").exists():
        snapshot(out)
    stats=parse_stats(raw)
    diag=diagnosis(stats,actor)
    data={"schema":"axia.d08.actor_rtf_diagnostic.v1","collected_utc":stamp,
          "capture_status":capture,"gz_partition":partition,"partition_detection":detection,
          "sample_seconds_requested":a.seconds,"scene":str(scene) if scene else None,
          "stats":stats,"actor":actor,"diagnosis":diag,
          "real_ros_or_gazebo_verified_by_script":capture=="CAPTURED" and stats["rtf_samples"]>=3,
          "no_goal":True,"control_published":False,"safety_ttl_verified":False,
          "gui_pixels_verified":False}
    archive=report(out,data)
    print("D08_ACTOR_DIAG_CATEGORY="+diag["category"])
    print("D08_ACTOR_RTF_MEDIAN="+str(stats.get("rtf_median","NOT_MEASURED"))+
          " samples="+str(stats["rtf_samples"]))
    print("D08_ACTOR_DIAG_CAPTURE_STATUS="+capture)
    print("D08_ACTOR_DIAG_EVIDENCE="+str(out))
    print("D08_ACTOR_DIAG_ZIP="+str(archive))
    return 0 if capture in ("CAPTURED","OFFLINE") and stats["rtf_samples"]>=3 else 3

if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,ValueError,ET.ParseError) as exc:
        print("D08_ACTOR_DIAG_BLOCKED="+str(exc),file=sys.stderr)
        sys.exit(2)
