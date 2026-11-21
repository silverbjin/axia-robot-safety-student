#!/usr/bin/env python3
"""Read-only G07 G20 evidence: actual Nav2 PlannerServer /plan vs fixture.

The official Jazzy PlannerServer publishes nav_msgs/Path to "plan" only
when there is a subscriber; a global planner path is NOT the controller's
local trajectory nor proof of collision risk. No plan, no provenance, no
fresh data, bad frames, or invalid anchor always means HOLD.

No extra publisher/Goal/cmd_vel; no change to Safety TTL/fixture/action.
"""
import math
import threading
import time

MAX_PATH_POINTS=2048
MAX_PLAN_AGE_SEC=15.0

def _finite(v):
    return type(v) in (int,float) and math.isfinite(v)

def _triplet(v):
    if (not isinstance(v,(list,tuple)) or len(v)!=3 or
            not all(_finite(x) for x in v)):
        return None
    return tuple(float(x) for x in v)

def _angle(x):
    return math.atan2(math.sin(x),math.cos(x))

def _distance_to_segment(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    length2=dx*dx+dy*dy
    if length2<1e-8:return None
    t=max(0.0,min(1.0,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2))
    px=a[0]+t*dx;py=a[1]+t*dy
    return math.hypot(px-p[0],py-p[1]),math.atan2(dy,dx)

def _verified_transform(anchor,odom,fixture_world):
    if (not isinstance(anchor,dict)
            or anchor.get("world_pose_source")!="validated_official_nav2_world_spawn"
            or anchor.get("relative_motion_source")!="ros_odom"
            or anchor.get("map_pose_source") not in (
                "tf_map_base_link","amcl_pose_map_transient_local")):
        return None
    map0=_triplet(anchor.get("map_pose"))
    odom0=_triplet(anchor.get("odom_pose"))
    world0=_triplet(anchor.get("world_pose"))
    live=_triplet(odom)
    if any(x is None for x in (map0,odom0,world0,live)):
        return None
    c=math.cos(map0[2]-odom0[2]);s=math.sin(map0[2]-odom0[2])
    rx=live[0]-odom0[0];ry=live[1]-odom0[1]
    pose=(map0[0]+c*rx-s*ry,map0[1]+s*rx+c*ry,
          _angle(map0[2]+live[2]-odom0[2]))
    fpose=None
    if fixture_world is not None:
        if (not isinstance(fixture_world,(tuple,list)) or len(fixture_world)!=2
                or not all(_finite(x) for x in fixture_world)):
            return None
        # World -> Map from exact separately verified shared world spawn.
        cc=math.cos(map0[2]-world0[2]);ss=math.sin(map0[2]-world0[2])
        fx=fixture_world[0]-world0[0];fy=fixture_world[1]-world0[1]
        fpose=(map0[0]+cc*fx-ss*fy,map0[1]+ss*fx+cc*fy)
    return pose,fpose

class PlanWitness:
    def __init__(self):
        self._lock=threading.Lock()
        self._latest=None

    def observe(self,frame_id,points,*,stamp_ns=None,at_monotonic=None):
        """Call from original Observer's same ROS node callback, no file I/O."""
        now=time.monotonic() if at_monotonic is None else at_monotonic
        if (frame_id!="map" or not _finite(now) or now<0
                or not isinstance(points,(list,tuple))
                or not 2<=len(points)<=MAX_PATH_POINTS):
            return False
        coords=[]
        for p in points:
            if (not isinstance(p,(list,tuple)) or len(p)!=2
                    or not all(_finite(v) for v in p)):
                return False
            coords.append((float(p[0]),float(p[1])))
        if (not any(math.dist(a,b)>=.01 for a,b in zip(coords,coords[1:]))
                or stamp_ns is not None and
                (type(stamp_ns) is not int or stamp_ns<0)):
            return False
        with self._lock:
            self._latest=(float(now),tuple(coords),stamp_ns)
        return True

    def summarize(self,anchor,odom_pose,*,fixture_world_xy=None,
                  at_monotonic=None,phase="UNKNOWN",front_m=None,
                  supervised_vx=None):
        now=time.monotonic() if at_monotonic is None else at_monotonic
        result=dict(schema="axia.g07.g20.nav2_global_plan_phase.v1",
                    phase=phase if phase in (
                        "PRE_FIXTURE","AFTER_FIXTURE_ACK",
                        "SLOW_OBSERVED","SLOW_OBSERVATION_FAILED")
                        else "UNKNOWN",
                    status="NAV2_PLAN_NOT_OBSERVED_HOLD",
                    release="HOLD",root_cause="UNDETERMINED",
                    root_cause_proven=False,fixture_alignment_proven=False,
                    nav2_local_trajectory_proven=False,
                    nav2_plan_publisher_identity_proven=False,
                    goal_straight_as_plan_proven=False,
                    actual_obstacle_on_trajectory_proven=False,
                    certified_estop=False,owner_wsl2_l3_accepted=False,
                    safety_ttl_changed=False,source_topic="/plan")
        if _finite(front_m):
            result["real_front_m"]=round(float(front_m),6)
        if _finite(supervised_vx):
            result["actual_supervised_vx"]=round(float(supervised_vx),6)
        if not _finite(now) or now<0:
            result["status"]="CLOCK_UNVERIFIED_HOLD"
            return result
        transformed=_verified_transform(anchor,odom_pose,fixture_world_xy)
        if transformed is None:
            result["status"]="FRAME_ANCHOR_UNVERIFIED_HOLD"
            return result
        pose,fixture=transformed
        result["robot_map_xy"]=[round(pose[0],5),round(pose[1],5)]
        result["robot_map_yaw_rad"]=round(pose[2],6)
        with self._lock:
            current=self._latest
        if current is None:return result
        stamp,points,header_stamp_ns=current
        age=now-stamp
        if not 0<=age<=MAX_PLAN_AGE_SEC:
            result["status"]="NAV2_PLAN_STALE_HOLD"
            return result
        result["plan_age_sec"]=round(age,6)
        result["plan_points"]=len(points)
        result["path_header_stamp_provided"]=header_stamp_ns is not None
        # PlannerServer /plan is a global visualisation path. Do not
        # present its tangent as a proven local controller command.
        min_robot=(float("inf"),None,None)
        min_fixture=float("inf")
        for i,(a,b) in enumerate(zip(points,points[1:])):
            rd=_distance_to_segment(pose,a,b)
            if rd is not None and rd[0]<min_robot[0]:
                min_robot=(rd[0],i,rd[1])
            if fixture is not None:
                fd=_distance_to_segment(fixture,a,b)
                if fd is not None and fd[0]<min_fixture:
                    min_fixture=fd[0]
        if min_robot[1] is None:
            result["status"]="NAV2_PLAN_DEGENERATE_HOLD"
            return result
        from p2_g07_demo_corridor import DEMO_GOAL
        straight=math.atan2(DEMO_GOAL[1]-pose[1],DEMO_GOAL[0]-pose[0])
        result.update(
            status="NAV2_GLOBAL_PLAN_GEOMETRY_CANDIDATE_HOLD",
            nearest_plan_segment_index=min_robot[1],
            robot_nearest_plan_distance_m=round(min_robot[0],6),
            plan_tangent_yaw_rad=round(min_robot[2],6),
            straight_goal_bearing_rad=round(straight,6),
            robot_to_plan_tangent_rad=round(_angle(min_robot[2]-pose[2]),6),
            straight_goal_vs_plan_tangent_rad=round(_angle(straight-min_robot[2]),6))
        if fixture is not None and math.isfinite(min_fixture):
            result["obstacle_min_path_distance_m"]=round(min_fixture,6)
        return result
