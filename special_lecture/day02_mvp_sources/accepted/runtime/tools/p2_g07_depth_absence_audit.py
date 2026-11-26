#!/usr/bin/env python3
"""G07 read-only Gazebo/ROS depth publication absence audit (pre-Goal).

The official depth sensor definition remains in the installed Waffle source.
This G07 session uses a temporary model with only that <sensor> removed.
One existing Scan preflight ROS node records the discovered graph; one
bounded gz topic list is captured, no extra ROS participant or fake Scan.
"""
import argparse
import json
from pathlib import Path
import re

_DEPTH_ROS_TYPES={"sensor_msgs/msg/Image","sensor_msgs/msg/PointCloud2",
                  "sensor_msgs/msg/CompressedImage"}
_DEPTH_NAME=re.compile(r"depth|point.?cloud|intel_realsense_r200_depth",
                       re.IGNORECASE)


def assess(model,ros_topics,gz_topics,scan_report):
    result={
        "schema":"axia.g07.depth_sensor_absent_pre_goal.v1",
        "status":"HOLD","first_failure":"DEPTH_EVIDENCE_MISSING",
        "depth_sensor_enabled":None,"goal_sent":False,
        "sensor_definitions_preserved_in_official_model":True,
        "real_scan_and_safety_scan":False,"certified_estop":False,
    }
    if (not isinstance(model,str) or not isinstance(ros_topics,list)
            or not isinstance(gz_topics,list) or not isinstance(scan_report,dict)):
        return result
    if 'name="hls_lfcd_lds" type="gpu_lidar"' not in model:
        result["first_failure"]="G07_GAZEBO_LIDAR_MISSING"
        return result
    if 'name="intel_realsense_r200_depth" type="depth"' in model:
        result["depth_sensor_enabled"]=True
        result["first_failure"]="G07_DEPTH_SENSOR_STILL_ENABLED"
        return result
    result["depth_sensor_enabled"]=False
    if (scan_report.get("status")!="PASS_SCOPED_RECEIVED_SCAN_ONLY"
            or not all(scan_report.get("topic_results",{}).get(name,{}).get("pairs",0)>=15
                       for name in ("scan","safety_scan"))):
        result["first_failure"]="REAL_SCAN_AND_SAFETY_SCAN_NOT_PROVEN"
        return result
    result["real_scan_and_safety_scan"]=True
    depth_ros=[]
    for row in ros_topics:
        if not isinstance(row,dict):
            result["first_failure"]="ROS_GRAPH_SCHEMA_INVALID"
            return result
        name,types=row.get("name"),row.get("types")
        if not isinstance(name,str) or not isinstance(types,list):
            result["first_failure"]="ROS_GRAPH_SCHEMA_INVALID"
            return result
        if _DEPTH_NAME.search(name) or (any(t in _DEPTH_ROS_TYPES for t in types)
                                          and ("camera" in name.lower() or "image" in name.lower())):
            depth_ros.append(name)
    depth_gz=[x for x in gz_topics if isinstance(x,str) and _DEPTH_NAME.search(x)]
    result.update(depth_ros_topics=sorted(set(depth_ros)),
                  depth_gazebo_topics=sorted(set(depth_gz)))
    if not gz_topics:
        result["first_failure"]="GAZEBO_TRANSPORT_GRAPH_EMPTY"
        return result
    if depth_ros or depth_gz:
        result["first_failure"]="DEPTH_IMAGE_OR_POINTCLOUD_PUBLICATION_PRESENT"
        return result
    result.update(status="G07_REAL_DEPTH_ABSENT_SCAN_PRESENT_PASS",
                  first_failure="NONE")
    return result


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--scan-report",type=Path,required=True)
    p.add_argument("--gz-topics",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        model=a.model.read_text(encoding="utf-8")
        scan=json.loads(a.scan_report.read_text())
        gz=[s.strip() for s in a.gz_topics.read_text().splitlines()
            if s.strip() and s.startswith("/")]
        result=assess(model,scan.get("ros_discovered_topics"),gz,scan)
    except (OSError,ValueError,TypeError) as exc:
        result=assess(None,None,None,None)
        result["first_failure"]="DEPTH_PROBE_"+type(exc).__name__
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("AXIA_G07_DEPTH_SENSOR_RUNTIME "+json.dumps(result,sort_keys=True),flush=True)
    return 0 if result["status"]=="G07_REAL_DEPTH_ABSENT_SCAN_PRESENT_PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
