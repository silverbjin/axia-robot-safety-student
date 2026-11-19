#!/usr/bin/env python3
"""T07 Owner-only Jazzy/Gazebo evidence case runner; never self-approves motion.

Exactly one Supervisor-owned NavigateToPose via /axia/safety/goal_pose after
per-case controlling-TTY approval. For G05/G06, call the existing owned-PID
Crash Injector with a SECOND case-specific TTY approval and live ROS admission.
G07 uses a real Gazebo cylinder/contact sensor and measures LaserScan/CM/Twist.
All outputs are CANDIDATE/BLOCKED; independent raw review decides acceptance.
SIMULATION ONLY; not a certified E-Stop.
"""
import argparse
import faulthandler
from collections import deque
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from p2_g07_ci_moving_goal_oracle import normalize_cm_rmw_info
from p2_l3_acceptance_contract import (before_moving_fault,
                                         before_moving_g07_slowdown,
                                         check_case_result, zone_phase_sample,
                                         recent_stop_dwell)
from p2_evidence_oracles import assess_process_fault, assess_zone, assess_zone_demo
from p2_mvp_one_goal_oracle import check_demo_zone_motion
from p2_l3_gz_fixture import admit_preloaded as admit_preloaded_fixture, move as move_fixture, CONTACT_TOPIC, RADIUS
from p2_l3_coordinate_frames import (make_frame_anchor, obstacle_world_pose)
from p2_g07_spawn_contract import official_tb3_spawn
from p2_mvp_demo_timing import clear_phase_reference
from p2_mvp_stop_geometry import STOP_DISPATCH_M
from p2_g07_demo_corridor import DEMO_GOAL, official_map_readonly
from p2_g07_relocated_no_goal_probe import sector_min as pre_goal_side_scan, DEMO_WORLD_POSE
from p2_g07_owner_prepositioned import pregoal_side_obstacle_ready, demo_moving_stage_allowed
from p2_owned_process_fault import (read_process, signal_with_pre_goal_consent)
from p2_shell_owner_consent import consume_receipt as consume_shell_consent
from axia_fault_injector.p2_process_fault_policy import matches_role
from p2_pre_goal_process_gate import inspect as inspect_pre_goal_processes

ROOT = Path(__file__).resolve().parents[1]


def _terminal_text(code):
    return {4:'SUCCEEDED',5:'CANCELED',6:'ABORTED'}.get(code,'UNKNOWN')


def _target_pid(name, session, required_environment):
    matches=[]
    role_count=0
    session_count=0
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():continue
        pid=int(entry.name)
        try:
            info=read_process(pid)
            if not matches_role(info, name):
                continue
            role_count+=1
            if info.session != session:
                continue
            session_count+=1
            if all(info.environ.get(k)==v for k,v in required_environment.items()):
                matches.append(pid)
        except (OSError,ProcessLookupError,ValueError):continue
    if len(matches)!=1:
        # Counts only; never dump cmdline or environment variables.
        raise RuntimeError(f'OWNED_PID_AMBIGUOUS:{name}:count={len(matches)}'
                           f':role_count={role_count}:session_count={session_count}')
    return matches[0]


class Observer:
    def __init__(self, node, folder, *, buffered_evidence=False,
                 periodic_flush_sec=None, sensor_header_ledger=False):
        from action_msgs.msg import GoalStatusArray
        from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
        from nav_msgs.msg import Odometry
        from rosgraph_msgs.msg import Clock
        from sensor_msgs.msg import LaserScan
        from std_msgs.msg import String
        from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
        self.node=node
        self.amcl_map_pose=None
        self.amcl_map_pose_at=None
        # For the exact G07 Owner/CI shared profile, register the genuine
        # map/odom TF receiver BEFORE this node enters MultiThreadedExecutor.
        # Two actual public L2 runs failed with listener creation after spin
        # (even when waiting 10 seconds); no synthesized map pose is allowed.
        if os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1":
            from tf2_ros import Buffer,TransformListener
            self._g07_tf_buffer=Buffer()
            self._g07_tf_listener=TransformListener(self._g07_tf_buffer,node,spin_thread=False)
            node._axia_g07_tf_buffer=self._g07_tf_buffer
            node._axia_g07_tf_listener=self._g07_tf_listener
            print("G07_TF_LISTENER_REGISTERED_BEFORE_EXECUTOR REAL_TF_ONLY",flush=True)
        if periodic_flush_sec is not None and (
                type(periodic_flush_sec) not in (int,float)
                or not math.isfinite(periodic_flush_sec)
                or not .5<=periodic_flush_sec<=1.0
                or not buffered_evidence):
            raise ValueError("BOUNDED_BUFFERED_EVIDENCE_FLUSH_CONTRACT")
        self._periodic_flush_sec=periodic_flush_sec
        self._last_periodic_flush_mono=time.monotonic()
        # CI-only timing evidence uses callback ENTRY time, not the time
        # after decoding every real LiDAR ray. Owner retains prior semantics.
        self._ci_callback_entry_timestamps=buffered_evidence
        # H01 NO-GOAL evidence is opt-in only; original MVP/Owner semantics
        # remain unchanged by default (no extra subscriptions or QoS change).
        if type(sensor_header_ledger) is not bool:
            raise ValueError("H01_SENSOR_HEADER_AUDIT_BOOL_REQUIRED")
        self._ttl_sensor_header_ledger=sensor_header_ledger
        self.lock=threading.Lock()
        # Owner evidence stays line-buffered by default; the CI-only G07
        # Observer can avoid shared-Docker-filesystem flushes on every
        # sensor/clock callback, which bias timing interarrival measurements.
        # CI snapshots the ledger under the same lock at its evidence gate.
        self.event_file=(folder/'actual_ros_events.jsonl').open(
            'x',encoding='utf-8',buffering=(65536 if buffered_evidence else 1))
        self.odom=deque(maxlen=1500);self.cmd=deque(maxlen=1200)
        self.pre=deque(maxlen=1200);self.vin=deque(maxlen=1200)
        self.guard=None;self.supervisor=None
        self.clock_ticks=deque(maxlen=4)
        self.goal_status={};self.current_uuid=None;self.goal_events=[]
        self.guard_latch_at=None
        self.latest={};self.latest_scan=None;self.latest_side_scan=None
        self.pose=None
        self._sub=[]
        def sub(cls,topic,fn,qos):self._sub.append(node.create_subscription(cls,topic,fn,qos))
        sub(Odometry,'/odom',self._odom,qos_profile_sensor_data)
        sub(Twist,'/cmd_vel',lambda m:self._twist('final',m),10)
        # G07 CI/Owner parity only: the EXISTING read-only Observer
        # receives Jazzy RMW publication/receipt metadata. It does NOT
        # add a ROS subscription, change QoS, mutate CM, or affect Guard.
        self._g07_rmw_info=(os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1")
        if self._g07_rmw_info:
            sub(Twist,'/cmd_vel_pre_guard',
                lambda m,info:self._twist('pre_guard',m,info=info),10)
            sub(Twist,'/cmd_vel_supervised',
                lambda m,info:self._twist('supervised',m,info=info),10)
        else:
            sub(Twist,'/cmd_vel_pre_guard',lambda m:self._twist('pre_guard',m),10)
            sub(Twist,'/cmd_vel_supervised',lambda m:self._twist('supervised',m),10)
        sub(String,'/axia/p2/base_guard',lambda m:self._state('guard',m),10)
        sub(String,'/axia/safety/state',lambda m:self._state('supervisor',m),10)
        sub(Clock,'/clock',self._clock,qos_profile_sensor_data)
        sub(LaserScan,'/safety/scan',self._scan,qos_profile_sensor_data)
        qos=QoSProfile(depth=10)
        qos.reliability=QoSReliabilityPolicy.RELIABLE
        qos.durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
        sub(GoalStatusArray,'/navigate_to_pose/_action/status',self._action,qos)
        # Same proven QoS as P1 navigation readiness: official AMCL can
        # publish a SINGLE localization pose while stationary. /tf is
        # VOLATILE and a late listener may miss that initial map→odom update.
        # A newly admitted G07 observer uses the real retained AMCL map pose,
        # never a fabricated TF or raw /odom-as-map fallback.
        if os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1":
            amcl_qos=QoSProfile(depth=1)
            amcl_qos.reliability=QoSReliabilityPolicy.RELIABLE
            amcl_qos.durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
            sub(PoseWithCovarianceStamped,'/amcl_pose',self._amcl_map_pose,amcl_qos)


    def _write(self,kind,*,at=None,**kv):
        t=time.monotonic() if at is None else at
        with self.lock:
            self.event_file.write(json.dumps({'kind':kind,'t':t,**kv},sort_keys=True)+'\n')
            flush_sec=getattr(self, "_periodic_flush_sec", None)
            if flush_sec is not None:
                if 0 <= t-self._last_periodic_flush_mono >= flush_sec:
                    # Reduce ~250 callback-driven flushes/s to one every
                    # 0.75s, but keep bounded on-disk evidence on native abort.
                    self.event_file.flush()
                    self._last_periodic_flush_mono=t
            self.latest[kind]=t
        return t
    def _odom(self,m):
        # Host MONOTONIC callback entry vs genuine ROS sim-time Header; do
        # not compute absolute source age by mixing these two clock domains.
        entry_at=time.monotonic() if self._ttl_sensor_header_ledger else None
        header_stamp_ns=(int(m.header.stamp.sec)*1000000000+
                         int(m.header.stamp.nanosec)) if self._ttl_sensor_header_ledger else None
        q=m.pose.pose.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        x,y=m.pose.pose.position.x,m.pose.pose.position.y
        vx,wz=m.twist.twist.linear.x,m.twist.twist.angular.z
        t=self._write('odom',at=entry_at,vx=vx,wz=wz,x=x,y=y,yaw=yaw,
                      **({"header_stamp_ns":header_stamp_ns}
                         if self._ttl_sensor_header_ledger else {}))
        with self.lock:
            self.pose=(x,y,yaw);self.odom.append({'t':t,'vx':vx,'wz':wz})
    def _twist(self,kind,m,*,info=None):
        if info is None:
            t=self._write(kind,vx=m.linear.x,wz=m.angular.z)
        else:
            # Entry time precedes metadata decoding: no fake callback delay.
            callback_at=time.monotonic()
            timing=normalize_cm_rmw_info(info)
            t=self._write(kind,at=callback_at,vx=m.linear.x,wz=m.angular.z,
                          **(timing if timing is not None
                             else {"rmw_message_info_unavailable":True}))
        with self.lock:
            entry={'t':t,'vx':m.linear.x,'wz':m.angular.z}
            if kind=='final':self.cmd.append(entry)
            elif kind=='pre_guard':self.pre.append(entry)
            else:self.vin.append(entry)
    def _state(self,kind,m):
        try:data=json.loads(m.data)
        except (ValueError,TypeError):data={'invalid':True}
        self._write(kind,data=data)
        with self.lock:
            if kind=='guard':
                self.guard=data
                if data.get('latched') is True and self.guard_latch_at is None:
                    self.guard_latch_at=self.latest['guard']
            else:self.supervisor=data
    def _clock(self,m):
        ns=int(m.clock.sec)*1000000000+int(m.clock.nanosec)
        self._write('clock',ns=ns)
        with self.lock:
            if not self.clock_ticks or self.clock_ticks[-1]!=ns:self.clock_ticks.append(ns)
    def _scan(self,m):
        # Host-monotonic ROS callback entry is the correct delivery-time
        # boundary for the CI LaserScan 300ms interarrival gate.
        scan_callback_at = time.monotonic() if (
            self._ci_callback_entry_timestamps or self._ttl_sensor_header_ledger) else None
        header_stamp_ns=(int(m.header.stamp.sec)*1000000000+
                         int(m.header.stamp.nanosec)) if self._ttl_sensor_header_ledger else None
        values=[v for i,v in enumerate(m.ranges) if
            abs(m.angle_min+i*m.angle_increment)<=0.18
            and math.isfinite(v) and m.range_min<=v<=m.range_max]
        d=min(values) if values else None
        side=pre_goal_side_scan(m)
        self._write('scan',front_m=d,side_m=side,at=scan_callback_at,
                    **({"header_stamp_ns":header_stamp_ns}
                       if self._ttl_sensor_header_ledger else {}))
        with self.lock:
            self.latest_scan=d
            self.latest_side_scan=side
    def _action(self,m):
        for z in m.status_list:
            uuid=bytes(z.goal_info.goal_id.uuid).hex()
            t=self._write('action',uuid=uuid,status=int(z.status))
            with self.lock:
                self.goal_status[uuid]=int(z.status)
                self.goal_events.append((t,uuid,int(z.status)))
                if int(z.status)==2:self.current_uuid=uuid

    def _amcl_map_pose(self,m):
        from p2_l3_coordinate_frames import verified_amcl_map_pose
        p=m.pose.pose.position
        q=m.pose.pose.orientation
        try:
            pose=verified_amcl_map_pose(m.header.frame_id,p.x,p.y,
                                        q.x,q.y,q.z,q.w)
        except ValueError:
            # Invalid or non-map frames never enter the accepted map anchor.
            self._write('amcl_pose_invalid')
            return
        at=self._write('amcl_pose',source='actual_nav2_amcl_transient_local')
        with self.lock:
            self.amcl_map_pose=pose
            self.amcl_map_pose_at=at

    def snapshot(self, *, include_graph=True):
        # CI moving-Goal admission proves exclusive graph once before Goal.
        # During its 25ms evidence poll, avoid three blocking DDS discovery
        # queries per iteration; they can interfere with 150ms CM/Guard TTL.
        # Owner and all original callers retain the live graph by default.
        now=time.monotonic()
        with self.lock:
            s={'mono':now,'guard':self.guard or {},
               'goal_uuid':(self.supervisor or {}).get('goal_id'),
               'action_status':self.goal_status.get((self.supervisor or {}).get('goal_id')),
               'clock_advancing':len(self.clock_ticks)>=2 and self.clock_ticks[-1]>self.clock_ticks[0]}
            for k in ('scan','odom','guard','action','supervisor','clock','final','pre_guard','supervised'):
                s[k+'_at']=self.latest.get(k)
            for k,arr in (('odom_speed',self.odom),('final_speed',self.cmd),
                          ('pre_guard_speed',self.pre),('supervised_speed',self.vin)):
                s[k]=arr[-1]['vx'] if arr else None
        if include_graph:
            s['final_publishers']=[(p.node_name,p.topic_type) for p in self.node.get_publishers_info_by_topic('/cmd_vel')]
            s['supervisor_publishers']=[(p.node_name,p.topic_type) for p in self.node.get_publishers_info_by_topic('/cmd_vel_supervised')]
            s['cm_publishers']=[(p.node_name,p.topic_type) for p in self.node.get_publishers_info_by_topic('/cmd_vel_pre_guard')]
        return s
    def data(self):
        with self.lock:
            return {'odom':list(self.odom),'cmd':list(self.cmd),
                    'pre':list(self.pre),'vin':list(self.vin),
                    'guard':dict(self.guard or {}),'supervisor':dict(self.supervisor or {}),
                    'goals':dict(self.goal_status),'goal_events':list(self.goal_events),
                    'guard_latch_at':self.guard_latch_at,
                    'goal_uuid':(self.supervisor or {}).get('goal_id'),
                    'scan':self.latest_scan,'side_scan':self.latest_side_scan,
                    'pose':self.pose,
                    'amcl_map_pose':self.amcl_map_pose,
                    'amcl_map_pose_at':self.amcl_map_pose_at}
    def flush_events(self):
        """Sync all callbacks through the monotonic evidence boundary."""
        with self.lock:
            self.event_file.flush()

    def close(self):
        with self.lock:self.event_file.flush();self.event_file.close()


def wait_for(check,seconds,step=.05):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=check()
        if result:return result
        time.sleep(step)
    return None


def _call_start(node, observer):
    from std_srvs.srv import Trigger
    client=node.create_client(Trigger,'/axia/safety/start')
    if not client.wait_for_service(timeout_sec=8):raise RuntimeError('SUPERVISOR_START_SERVICE_MISSING')
    state=observer.data()['supervisor']
    h=state.get('health_diagnostics',{})
    if (state.get('state') not in ('BOOT_SAFE','NORMAL')
            or not all(h.get(k) is True for k in ('clock_ok','scan_ok','graph_ok','cm_lifecycle_ok','nav2_action_ready'))):
        raise RuntimeError('SUPERVISOR_NOT_HEALTHY_AT_START')
    future=client.call_async(Trigger.Request())
    if not wait_for(lambda:future.done(),8):raise RuntimeError('SUPERVISOR_START_TIMEOUT')
    response=future.result()
    if response is None or response.success is not True:raise RuntimeError('SUPERVISOR_START_REJECTED')
    return True


def _publish_goal(node, observer, *, demo_corridor=False):
    from geometry_msgs.msg import PoseStamped
    subscribers=node.get_subscriptions_info_by_topic('/axia/safety/goal_pose')
    matches=[x for x in subscribers if x.node_name=='axia_safety_supervisor'
             and x.topic_type=='geometry_msgs/msg/PoseStamped']
    if len(matches)!=1:raise RuntimeError('SUPERVISOR_GOAL_TOPIC_NOT_UNIQUE')
    if observer.data()['supervisor'].get('state')!='NORMAL':raise RuntimeError('NOT_NORMAL_BEFORE_GOAL')
    pub=node.create_publisher(PoseStamped,'/axia/safety/goal_pose',10)
    # Default P1 corridor stays immutable. The explicit G07-only demo mode
    # uses an independently surveyed longer FREE-MAP candidate, not a new
    # nominal/fault Goal. Its Nav2 runtime plan is NOT proven by map sampling.
    gx,gy = DEMO_GOAL if demo_corridor else (-1.6,-.5)
    pose=PoseStamped();pose.header.frame_id='map'
    pose.header.stamp=node.get_clock().now().to_msg()
    pose.pose.position.x=gx;pose.pose.position.y=gy;pose.pose.orientation.w=1.0
    pub.publish(pose)
    observer._write('owner_goal_published',x=gx,y=gy,frame='map',
                    demo_open_corridor=bool(demo_corridor))
    return pub


def _find_pids(case,launch_pid):
    env={'ROS_DOMAIN_ID':os.environ['ROS_DOMAIN_ID'],'GZ_PARTITION':os.environ['GZ_PARTITION']}
    name='p2_supervisor_node' if case=='G05' else 'collision_monitor'
    return _target_pid(name,launch_pid,env),_target_pid('p2_base_guard_node',launch_pid,env)


def _fault_case(case,node,obs,folder,launch_pid,source_sha,consent):
    # Use the already-running typed Observer. A second ROS process and
    # post-motion TTY roundtrip exceeded the entire 1.8s field Goal duration.
    pre=wait_for(lambda:obs.snapshot() if before_moving_fault(obs.snapshot())[0] else None,10)
    if pre is None:raise RuntimeError('MOVING_GOAL_WITH_GUARD_UNVERIFIED')
    target,guard=_find_pids(case,launch_pid)
    # Repeat live admission in the trusted Injector immediately before SIGKILL.
    audit=signal_with_pre_goal_consent(
        consent=consent, case=case, pid=target, guard_pid=guard,
        launch_pid=launch_pid, source_sha=source_sha,
        ros_domain_id=os.environ['ROS_DOMAIN_ID'],
        gz_partition=os.environ['GZ_PARTITION'],
        evidence_dir=folder, live_snapshot=obs.snapshot())
    event_t=audit['at_host_monotonic_sec']
    print('P2_FAULT_SIGNAL_SENT case='+case+' pid='+str(target)+' goal='+str(audit['verified_goal_uuid']), flush=True)
    obs._write('fault_signal_ack',case=case,pid=target,fault_t=event_t)
    wait_for(lambda: (obs.data()['guard'].get('latched') is True
                      and obs.data()['goals'].get(audit.get('verified_goal_uuid')) in (5,6)),9)
    time.sleep(2)
    data=obs.data()
    goal=audit.get('verified_goal_uuid')
    terminal=_terminal_text(data['goals'].get(goal))
    latch_at=data.get('guard_latch_at')
    if latch_at is None:
        raise RuntimeError('GUARD_LATCH_TIMESTAMP_MISSING')
    # Require guard PROCESS remains owned and executable after the fault.
    try:
        guard_info=read_process(guard)
        guard_alive=(guard_info.session==launch_pid and guard_info.command
                     and matches_role(guard_info, 'p2_base_guard_node'))
    except (OSError,ValueError):
        guard_alive=False
    reactivated=any(t>event_t and status==2 for t,uuid,status in data['goal_events'])
    result={'case':case,'source_sha':source_sha,'goal_uuid':goal,
            'gz_partition':os.environ['GZ_PARTITION'],
            'ros_domain_id':os.environ['ROS_DOMAIN_ID'],
            'fault_target_verified':True,
            'guard_alive':bool(guard_alive),
            'guard_latched':data['guard'].get('latched') is True,
            'terminal_status':terminal,
            'old_goal_reactivated':reactivated,
            'fault_mono':event_t,'odom':data['odom'],
            'cmd_after_latch':[{'vx':c['vx'],'wz':c['wz']} for c in data['cmd']
                               if c['t']>=latch_at],
            'certified_estop':False,'gate_accepted':False}
    return assess_process_fault(result),result


def _map_robot_pose(node,obs=None):
    # Retain old TF-only interface for unrelated legacy calls.
    # G07 exact CI/Owner profile uses official AMCL's actual pose in map,
    # with identical transient-local QoS as staged Nav2 readiness.
    # No synthetic TF, fixed coordinates or odom/world fallback.
    if obs is not None and os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1":
        def actual_amcl():
            e=obs.data()
            pose=e.get('amcl_map_pose')
            at=e.get('amcl_map_pose_at')
            if pose is None or at is None or not 0<=time.monotonic()-at<=30.0:
                return None
            return pose
        pose=wait_for(actual_amcl,3.0,step=.05)
        if pose is None:
            # Real Owner vJpsc6Wy: /amcl_pose was not delivered to the
            # late Observer, while Nav2's genuine map->odom and odom->base
            # TF chains continued (832 + 2791 messages in actual rosbag).
            # No publish, retry of /set_initial_pose, odom-as-map, or
            # synthetic world anchor. Reuse already-running TF listener.
            from rclpy.time import Time
            from tf2_ros import TransformException
            from p2_l3_coordinate_frames import verified_live_map_tf_pose
            buf=getattr(node,'_axia_g07_tf_buffer',None)
            if buf is None:
                raise RuntimeError('G07_AMCL_MAP_POSE_UNAVAILABLE_BEFORE_GOAL')
            def actual_map_tf():
                try:
                    if not buf.can_transform('map','base_link',Time()):
                        return None
                    with obs.lock:
                        now_ns=obs.clock_ticks[-1] if obs.clock_ticks else None
                    if now_ns is None:
                        return None
                    transform=buf.lookup_transform('map','base_link',Time())
                    return verified_live_map_tf_pose(transform,clock_ns=now_ns)
                except (TransformException,ValueError):
                    return None
            pose=wait_for(actual_map_tf,3.0,step=.05)
            if pose is None:
                raise RuntimeError('G07_AMCL_MAP_POSE_UNAVAILABLE_BEFORE_GOAL')
            obs.map_pose_source='tf_map_base_link'
            print('G07_LIVE_MAP_TF_VERIFIED_BEFORE_GOAL',flush=True)
            return pose
        obs.map_pose_source='amcl_pose_map_transient_local'
        print('G07_AMCL_ACTUAL_MAP_POSE_TRANSIENT_LOCAL_VERIFIED_BEFORE_GOAL',flush=True)
        return pose
    # TF is consumed via the existing live ROS executor, not assumed
    # to be equal to /odom or Gazebo world.
    from tf2_ros import Buffer, TransformListener
    from rclpy.time import Time
    buf=getattr(node,'_axia_g07_tf_buffer',None)
    if buf is None:
        # Legacy G05/G06/P1 paths unchanged; G07 parity requires early TF.
        buf=Buffer()
        listener=TransformListener(buf,node,spin_thread=False)
    else:
        listener=getattr(node,'_axia_g07_tf_listener')
        print("G07_TF_PREEXECUTOR_BUFFER_REUSED BEFORE_GOAL",flush=True)
    # This is pre-Goal only. Actual dynamic map TF may arrive >3s after a
    # newly attached listener on CI/WSLg even if staged navigation is READY.
    # The shared G07 pure deadline preserves the fail-closed map contract.
    from p2_l3_coordinate_frames import wait_for_actual_map_tf
    if not wait_for_actual_map_tf(
            lambda:buf.can_transform('map','base_link',Time()),
            budget_sec=10.0):
        raise RuntimeError('G07_MAP_TO_BASE_TF_UNAVAILABLE')
    transform=buf.lookup_transform('map','base_link',Time())
    q=transform.transform.rotation
    yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    p=transform.transform.translation
    # Retain listener while lookup is active; no new frame is published.
    return (p.x,p.y,yaw)


def _relative_obstacle_pose(data,distance,world_anchor,*,demo_corridor=False):
    pose=data.get('pose')
    if pose is None:raise RuntimeError('LIVE_ODOM_POSE_MISSING')
    return obstacle_world_pose(world_anchor,pose,distance,RADIUS,demo_corridor=demo_corridor)

def _zone_case(obs,folder,source_sha,contact_log,world_anchor,fixture,*,demo_corridor=False):
    # G07 uses the original short, verified 0.4m Nav2 corridor.
    # The old 3 x 1.6s fixed sleeps outlasted that Goal (~2s field),
    # so slowdown/stop previously sampled terminal zero, not live CM.
    # Move through physically bounded zones while the Goal is *moving*;
    # record actual fresh scan, supervised input and CM output AFTER move.
    phases=[]
    for stage,distance in [('clear',1.2),('slowdown',.65),('stop',.34)]:
        # The physical fixture has already been moved into the clear zone
        # BEFORE the Goal by admit_preloaded_fixture (native ACK). Repeating
        # that expensive call after Goal consumed the short demo corridor.
        move_started=time.monotonic()
        if stage=='clear':
            # The 0.4 m fixed P1 Goal is short. Reuse only recent actual
            # Observer scan / Supervisor / CM samples, never synthesize them
            # or extend the approved corridor just to fill a time window.
            fresh_clear=clear_phase_reference(obs.snapshot())
            if fresh_clear is not None:
                move_started=fresh_clear
            obs._write('g07_preloaded_clear_zone_observed')
        elif not demo_corridor and demo_moving_stage_allowed(False,stage):
            # Formal/legacy G07 unchanged: its original moving world poses.
            x,y=_relative_obstacle_pose(obs.data(),distance,world_anchor)
            reply=move_fixture(x,y)
            (folder/f'g07_move_{stage}.log').write_text(reply)
            obs._write('gz_physical_obstacle_move',phase=stage,x=x,y=y)
        else:
            # This G07-only demo has its physical obstacle in the validated
            # world lane BEFORE the Goal. NEVER call slow native Gazebo CLI
            # while the Owner-controlled robot is turning or moving.
            if demo_moving_stage_allowed(True,stage):
                raise RuntimeError('G07_DEMO_UNAUTHORIZED_POST_GOAL_GZ_MUTATION')
            obs._write('g07_owner_wait_prepositioned_zone',phase=stage)
        # Repeated fresh ROS samples are required; never synthesize a phase.
        # Wider phase observation windows are justified by real WSL2 odom:
        # prior Goal turned ~0.72rad while Gazebo set_pose blocked for 2.59s.
        deadline=time.monotonic() + (
            (3.0 if stage=='clear' else 20.0 if stage=='slowdown' else 38.0)
            if demo_corridor else .75)
        sample=None
        while time.monotonic()<deadline:
            snap=obs.snapshot()
            if demo_corridor:
                if snap.get('action_status')!=2:
                    raise RuntimeError('G07_PREPOSITIONED_GOAL_NOT_EXECUTING_'+stage.upper())
                if snap.get('guard',{}).get('latched') is not False:
                    raise RuntimeError('G07_PREPOSITIONED_GUARD_NOT_FORWARDING_'+stage.upper())
            sample=zone_phase_sample(stage,obs.data(),snap,move_started)
            if sample is not None:
                break
            time.sleep(.025)
        if sample is None:
            snap=obs.snapshot();data=obs.data()
            (folder/f'g07_prepositioned_{stage}_diagnostics.json').write_text(
                json.dumps({'stage':stage,'front_scan_m':data.get('scan'),
                  'side_scan_m':data.get('side_scan'),
                  'goal_action_status':snap.get('action_status'),
                  'guard':snap.get('guard'),
                  'supervised_speed':snap.get('supervised_speed'),
                  'pre_guard_speed':snap.get('pre_guard_speed'),
                  'odom_speed':snap.get('odom_speed'),
                  'gate_accepted':False,'certified_estop':False},
                  sort_keys=True,indent=2)+'\n')
            raise RuntimeError('G07_'+stage.upper()+'_PHYSICAL_CM_RESPONSE_MISSING')
        phases.append(sample)
        obs._write('g07_live_zone_phase',**sample)
    # Wait until odom itself proves >=1s continuous stop; not fixed sample
    # count or a synthetic-only final status. Stale odom never satisfies it.
    def verified_dwell():
        snap=obs.snapshot()
        t=snap.get('odom_at')
        if not isinstance(t,(float,int)) or not 0<=time.monotonic()-t<=.3:
            return None
        result=recent_stop_dwell(obs.data()['odom'])
        return result if result>=1.0 else None
    dwell=wait_for(verified_dwell,2.0)
    if dwell is None:
        raise RuntimeError('G07_ACTUAL_ODOM_ZERO_DWELL_UNVERIFIED')
    data=obs.data()
    contact_text=contact_log.read_text(errors='replace') if contact_log.exists() else ''
    touched= ('collision1' in contact_text or 'data: true' in contact_text)
    # No continuous native contact feed is NOT proof of 0 contacts.
    coverage=('time {' in contact_text or 'header {' in contact_text)
    raw={'case':'G07','source_sha':source_sha,
         'gz_partition':os.environ['GZ_PARTITION'],'goal_uuid':data.get('goal_uuid'),
         'physical_obstacle_scan':True,
         'entity_preloaded_world':fixture.get('preloaded') is True,
         'set_pose_ack':fixture.get('set_pose_ack') is True,
         'contact_topic_proven':fixture.get('contact_topic_proven') is True,
         'collision_ground_truth':coverage,
         'collision_count':int(touched) if coverage or touched else None,
         'demo_scope':'SIMULATED_MVP_NO_CONTACT_CERTIFICATION',
         'zones':phases,
         'odom_stop_dwell_sec':dwell,'certified_estop':False,'gate_accepted':False}
    if coverage or touched:
        # Keep full acceptance oracle unchanged, including zero-contact proof.
        return assess_zone(raw),raw
    # Demo only: same real scan, CM slowdown/stop and odom dwell thresholds,
    # but no collision-free claim when native Contact telemetry is unavailable.
    return assess_zone_demo(raw),raw


def _mvp_one_goal_case(obs,folder,source_sha,world_anchor,fixture):
    """One consented Nav2 Goal: physically preloaded slow zone, then STOP move.

    The previous 0.4m Goal finished in 1.46s, BEFORE the 3.03s Gazebo move ACK.
    Do NOT repeatedly run a synchronous Gazebo CLI in a moving 0.4m corridor.
    Start in the demonstrated SlowZone, use actual ROS CM data there, then
    perform ONE bounded physical set_pose before the restricted Goal finishes.
    This separately scoped MVP does not establish a CLEAR-to-SLOW transition
    while moving, Contact ground truth or formal G07 acceptance.
    """
    def active():
        snap=obs.snapshot()
        return snap.get('action_status')==2 and snap.get('guard',{}).get('latched') is False
    moved_at=time.monotonic()
    def moving_slow():
        snap=obs.snapshot()
        if not active():return None
        if not before_moving_g07_slowdown(snap)[0]:return None
        return zone_phase_sample('slowdown',obs.data(),snap,moved_at)
    slow=wait_for(moving_slow,9.0,step=.025)
    if slow is None:
        raise RuntimeError('MVP_GOAL_SLOWZONE_LIVE_CM_NOT_PROVEN')
    slow_snapshot=obs.snapshot()
    if slow_snapshot.get('action_status')!=2:
        raise RuntimeError('MVP_GOAL_NOT_EXECUTING_WHEN_SLOW_OBSERVED')
    obs._write('g07_mvp_moving_slowzone',**slow)
    (folder/'g07_mvp_slow_phase.json').write_text(json.dumps(slow,sort_keys=True,indent=2)+'\n')
    if not active():
        raise RuntimeError('MVP_GOAL_TERMINATED_BEFORE_STOP_MOVE')
    # The real 0UqpnePv Owner L3 failed at .52m: set_pose ACK took 2.596s
    # but the post-ACK physical LaserScan minimum was 0.458m (>STOP 0.4m).
    # Place at the bounded 0.43m simulator-only dispatch distance, which must
    # first be physically calibrated by real no-Goal Gazebo L2. This is NOT a
    # runtime collision-free claim: only actual post-ACK sensor data can PASS.
    x,y=_relative_obstacle_pose(obs.data(),STOP_DISPATCH_M,world_anchor)
    stop_move_started=time.monotonic()
    ack=move_fixture(x,y)
    stop_ack_at=time.monotonic()
    (folder/'g07_mvp_stop_pose_ack.log').write_text(ack)
    ack_duration=stop_ack_at-stop_move_started
    obs._write('g07_mvp_stop_obstacle_moved',
               x=x,y=y,ack_duration=ack_duration,dispatch_m=STOP_DISPATCH_M)
    snap=obs.snapshot()
    if snap.get('action_status')!=2:
        raise RuntimeError('MVP_GOAL_TERMINATED_DURING_STOP_MOVE')
    min_front_after_ack=None
    sensor_samples_after_ack=0
    def moving_stop():
        nonlocal min_front_after_ack,sensor_samples_after_ack
        snap=obs.snapshot()
        fresh_scan_at=snap.get('scan_at')
        data=obs.data()
        front=data.get('scan')
        if (type(fresh_scan_at) in (int,float)
                and fresh_scan_at>stop_ack_at
                and type(front) in (int,float)
                and math.isfinite(front)):
            sensor_samples_after_ack+=1
            min_front_after_ack=(front if min_front_after_ack is None else
                                 min(front,min_front_after_ack))
        if snap.get('action_status')!=2:return None
        if snap.get('guard',{}).get('latched') is True:return None
        # Freshness must be AFTER set_pose ACK, not merely after dispatch.
        return zone_phase_sample('stop',data,snap,stop_ack_at)
    stop=wait_for(moving_stop,2.0,step=.025)
    final_snap=obs.snapshot()
    (folder/'g07_mvp_stop_diagnostics.json').write_text(
        json.dumps({
            'requested_dispatch_distance_m':STOP_DISPATCH_M,
            'native_set_pose_ack':bool(ack),
            'gz_ack_duration_sec':ack_duration,
            'physical_scan_min_after_ack_m':min_front_after_ack,
            'post_ack_scan_poll_count':sensor_samples_after_ack,
            'physical_scan_front_last_m':obs.data().get('scan'),
            'cm_input_speed_last':final_snap.get('supervised_speed'),
            'cm_output_speed_last':final_snap.get('pre_guard_speed'),
            'actual_odom_speed_last':final_snap.get('odom_speed'),
            'goal_action_status':final_snap.get('action_status'),
            'guard_latched':final_snap.get('guard',{}).get('latched'),
            'stop_zone_observed':stop is not None,
            'gate_accepted':False,
            'certified_estop':False,
        },sort_keys=True,indent=2)+'\n')
    if stop is None:
        if (min_front_after_ack is not None and
                min_front_after_ack>=.4):
            raise RuntimeError(
                'MVP_STOP_ZONE_NOT_REACHED:min_front='
                +format(min_front_after_ack,'.3f'))
        raise RuntimeError('MVP_LIVE_PHYSICAL_CM_STOP_RESPONSE_NOT_PROVEN')
    stop_snapshot=obs.snapshot()
    if stop_snapshot.get('action_status')!=2:
        raise RuntimeError('MVP_GOAL_NOT_EXECUTING_WHEN_STOP_OBSERVED')
    obs._write('g07_mvp_live_stopzone',**stop)
    def still_stopped():
        snap=obs.snapshot()
        at=snap.get('odom_at')
        if not isinstance(at,(float,int)) or not 0<=time.monotonic()-at<=.30:
            return None
        sec=recent_stop_dwell(obs.data()['odom'])
        return sec if sec>=1.0 else None
    dwell=wait_for(still_stopped,2.3,step=.025)
    if dwell is None:
        raise RuntimeError('MVP_ACTUAL_ODOM_STOP_DWELL_MISSING')
    data=obs.data()
    raw={
        'case':'G07','source_sha':source_sha,
        'goal_uuid':data.get('goal_uuid'),'gz_partition':os.environ['GZ_PARTITION'],
        'physical_obstacle_scan':True,
        'entity_preloaded_world':fixture.get('preloaded') is True,
        'set_pose_ack':fixture.get('set_pose_ack') is True,
        'slowdown_pose_ack':fixture.get('set_pose_ack') is True,
        'stop_pose_ack':bool(ack),
        'slow_action_status':slow_snapshot.get('action_status'),
        'stop_action_status':stop_snapshot.get('action_status'),
        'slow':slow,'stop':stop,'odom_stop_dwell_sec':dwell,
        'collision_ground_truth':False,'collision_count':None,
        'pre_goal_clear_to_slow_transition_not_observed_while_moving':True,
        'certified_estop':False,'gate_accepted':False,
    }
    return check_demo_zone_motion(raw),raw

def run(args):
    if args.case=='G07' and args.mvp_relocated_obstacle:
        # Exact same Nav2 Goal, Gazebo STOP intrusion, CLEAR/SLOW/STOP,
        # first safety TTL breach, and strict post-ACK 1s odom oracle as
        # public real-Gazebo L2. Shell has separately admitted the Owner
        # TTY Goal before entry; common runner verifies owned /proc PIDs.
        # Original G05/G06 and legacy G07 modes remain unchanged.
        from argparse import Namespace
        from p2_g07_ci_moving_goal import run as run_shared_g07
        shared_args=Namespace(
            source_sha=args.source_sha,
            startup=args.output.parent/'startup_verdict.json',
            pregoal=args.output.parent/'g07_shared_pregoal/owner_pregoal_l2.json',
            output=args.output,
            owner_launch_pid=args.launch_pid)
        return run_shared_g07(shared_args)
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.parameter import Parameter
    folder=args.output
    folder.mkdir(parents=True,exist_ok=False)
    os.chmod(folder,0o700)
    report={'case':args.case,'status':'BLOCKED','reason':'NOT_STARTED',
            'source_sha':args.source_sha,'certified_estop':False,'gate_accepted':False}
    contact_proc=None;contact_stream=None;executor=None;node=None;thread=None;obs=None
    trace_file=(folder/'python_thread_watchdog.log').open('x',encoding='utf-8',buffering=1)
    progress_file=(folder/'execution_stages.jsonl').open('x',encoding='utf-8',buffering=1)
    def progress(phase):
        # fsync each stage: if the outer 100s runner kills Python the last
        # completed stage remains inspectable independently of ROS.
        event={'stage':phase,'host_monotonic':time.monotonic()}
        progress_file.write(json.dumps(event,sort_keys=True)+'\n')
        progress_file.flush()
        os.fsync(progress_file.fileno())
        if obs is not None and not obs.event_file.closed:
            obs.flush_events()
        report['last_stage']=phase
        persist()
        print('P2_L3_STAGE '+phase,flush=True)
    def persist():
        with (folder/'case_result.json').open('w') as fp:
            json.dump(report,fp,indent=2,sort_keys=True);fp.write('\n')
    persist()
    try:
        # Real WSL2 G07 rc=139 occurred 14.997s after OWNER_RUN_BEGIN,
        # coincident with the old repeated 15s watchdog stack dump.
        # Keep fatal SIGSEGV Python traces but do not inject a recurring
        # diagnostic timer into a busy rclpy MultiThreadedExecutor.
        # The shell still enforces its independent 100s hard timeout.
        faulthandler.enable(file=trace_file, all_threads=True)
        progress('OWNER_RUN_BEGIN')
        if not (os.environ.get('AXIA_P0_SIM_ONLY')=='1' and
                os.environ.get('ROS_DISTRO')=='jazzy' and
                os.environ.get('GZ_PARTITION','').startswith('axia_p2_')):
            raise RuntimeError('SIMULATION_MARKERS_INVALID')
        if not os.isatty(0) or not os.path.exists('/dev/tty'):
            raise RuntimeError('OWNER_TTY_REQUIRED')
        actual=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,timeout=5).strip()
        if actual!=args.source_sha:raise RuntimeError('EXACT_SOURCE_SHA_MISMATCH')
        rclpy.init()
        node=Node('axia_p2_owner_l3_observer',parameter_overrides=[Parameter('use_sim_time',value=True)],
                  automatically_declare_parameters_from_overrides=True)
        obs=Observer(node,folder,buffered_evidence=(args.case=='G07'),
                     periodic_flush_sec=(.75 if args.case=='G07' else None))
        executor=MultiThreadedExecutor(num_threads=2);executor.add_node(node)
        thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
        if not wait_for(lambda: obs.data()['supervisor'].get('health_diagnostics',{}).get('cm_lifecycle_ok') is True
                        and len(obs.clock_ticks)>=2 and obs.data()['scan'] is not None,10):
            raise RuntimeError('REAL_SUPERVISOR_OR_SCAN_NOT_READY')
        # Always validate all THREE role-owned processes from the actual
        # /proc table before any Goal, /start or Gazebo obstacle mutation.
        # A SHA, session, CM or Guard mismatch is a hard pre-Goal BLOCK.
        first_owners = inspect_pre_goal_processes(
            args.launch_pid, args.source_sha, actual, os.environ)
        with (folder/'pre_goal_process_admission.json').open('x') as fp:
            json.dump(first_owners, fp, indent=2, sort_keys=True)
            fp.write('\n')
        if first_owners['status'] != 'P2_PRE_GOAL_PID_CANDIDATE':
            raise RuntimeError('PRE_GOAL_PROCESS_ADMISSION:'+first_owners.get('reason','UNKNOWN'))
        report['pre_goal_owned_processes'] = first_owners['pid_by_role']
        progress('THREE_ROLE_PRE_GOAL_PID_PASS')
        world_anchor=None
        if args.case=='G07':
            # RED field archive bMy6KkY3: /odom x~0, map x~-2.
            # Validate map corridor from TF; create Gazebo obstacle only
            # from verified installed official Nav2 Gazebo WORLD spawn.
            map_pose=_map_robot_pose(node,obs)
            world_pose=official_tb3_spawn()
            odom_pose=obs.data()['pose']
            world_anchor=make_frame_anchor(
                map_pose=map_pose,odom_pose=odom_pose,world_pose=world_pose,
                map_pose_source=('amcl_pose_map_transient_local'
                                 if os.environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1"
                                 else 'tf_map_base_link'))
            (folder/'g07_frame_alignment.json').write_text(
                json.dumps(world_anchor,indent=2,sort_keys=True)+'\n')
            progress('G07_MAP_ODOM_GAZEBO_WORLD_FRAMES_VERIFIED')
            if args.mvp_relocated_obstacle:
                # Reuse OFFICIAL Jazzy raster; do not move static world obstacles
                # without synchronously updating the AMCL map and costmaps.
                from ament_index_python.packages import get_package_share_directory
                base=Path(get_package_share_directory('nav2_bringup'))/'maps'
                survey=official_map_readonly(base/'tb3_sandbox.pgm',
                                             base/'tb3_sandbox.yaml')
                (folder/'g07_demo_map_corridor.json').write_text(
                    json.dumps(survey,indent=2,sort_keys=True)+'\n')
                progress('G07_DEMO_OPEN_CORRIDOR_STATIC_MAP_VERIFIED_NO_GOAL')
            if args.mvp_relocated_obstacle:
                # Actual CI L2 proved this SAME static-world coordinate using
                # a native set_pose ACK and two fresh ROS side-bearing LiDAR
                # messages: 2.521m -> 0.708m. Validate it *before* any Goal.
                # No static sandbox world, Nav2 map or CM zone edits.
                current=obs.data()
                ref=current.get('pose')
                if (not isinstance(ref,tuple) or
                    abs(ref[0]-odom_pose[0])>.05 or
                    abs(ref[1]-odom_pose[1])>.05 or
                    abs(ref[2]-odom_pose[2])>.1):
                    raise RuntimeError('G07_PREGOAL_WAFFLE_NOT_AT_VERIFIED_SPAWN')
                x,y=DEMO_WORLD_POSE
                fixture=admit_preloaded_fixture(x,y,folder,require_contact=False)
                ack_at=time.monotonic()
                def pregoal_relocated_sensor():
                    state=obs.data();snap=obs.snapshot()
                    latest_odom=state['odom'][-1] if state['odom'] else {}
                    return pregoal_side_obstacle_ready(
                        side_m=state.get('side_scan'),
                        front_m=state.get('scan'),
                        laser_at=snap.get('scan_at'),
                        pose_ack_at=ack_at,now=time.monotonic(),
                        odom_vx=latest_odom.get('vx'),
                        odom_wz=latest_odom.get('wz'),
                        goal_sent=False)
                if not wait_for(pregoal_relocated_sensor,6.0,step=.025):
                    snap=obs.snapshot();state=obs.data()
                    (folder/'g07_pregoal_relocated_probe_failure.json').write_text(
                        json.dumps({'side_scan_m':state.get('side_scan'),
                           'front_scan_m':state.get('scan'),
                           'scan_last_host_time':snap.get('scan_at'),
                           'pose_ack_monotonic':ack_at,
                           'actual_odom':state['odom'][-1] if state['odom'] else None,
                           'goal_sent':False,'gate_accepted':False,
                           'certified_estop':False},sort_keys=True,indent=2)+'\n')
                    raise RuntimeError('G07_PREGOAL_SIDE_LIDAR_NOT_MATCHED_TO_REAL_CI')
                state=obs.data()
                (folder/'g07_prepositioned_scene.json').write_text(
                    json.dumps({'world_position':list(DEMO_WORLD_POSE),
                      'front_scan_m':state['scan'],
                      'side_scan_m':state['side_scan'],
                      'native_set_pose_ack':fixture['set_pose_ack'],
                      'same_geometry_as_real_ci_l2':True,
                      'goal_sent':False,'gate_accepted':False,
                      'certified_estop':False},sort_keys=True,indent=2)+'\n')
                progress('G07_PREGOAL_SIDE_LIDAR_CONFIRMED')
            else:
                preload_distance=.65 if args.mvp_one_goal else 1.35
                x,y=_relative_obstacle_pose(obs.data(),preload_distance,world_anchor)
                fixture=admit_preloaded_fixture(x,y,folder,require_contact=False)
            if args.mvp_one_goal:
                # Pre-Goal physical obstacle must be in actual slow zone,
                # and its LaserScan must have arrived AFTER Gazebo ACK.
                ready_at=time.monotonic()
                if not wait_for(lambda:obs.data()['scan']
                                if isinstance(obs.data()['scan'],float)
                                and .4<obs.data()['scan']<.75
                                and isinstance(obs.snapshot().get('scan_at'),float)
                                and obs.snapshot()['scan_at']>=ready_at
                                else None,5.0):
                    raise RuntimeError('MVP_PREGOAL_PHYSICAL_SLOWZONE_SCAN_MISSING')
                progress('G07_MVP_PREGOAL_PHYSICAL_SLOWZONE_ACK')
            report['fixture']=fixture
            if fixture['contact_topic_proven']:
                contact_stream=(folder/'g07_native_contacts.log').open('x',encoding='utf-8')
                contact_proc=subprocess.Popen(['gz','topic','-e','-t',CONTACT_TOPIC],
                                              stdout=contact_stream,stderr=subprocess.STDOUT,
                                              start_new_session=True)
            else:
                (folder/'g07_native_contacts.log').write_text(
                    'CONTACT_TOPIC_UNAVAILABLE: collision_ground_truth=false\n')
                progress('G07_DEMO_ONLY_CONTACT_TELEMETRY_MISSING')
        # Check owned target and Guard PID before /start or publishing any Goal.
        # Revalidate identities again at the fault boundary after real motion.
        # Second, independent per-case TTY consent BEFORE moving. The short
        # validated 0.4m corridor previously completed before a post-Goal
        # human could approve a Crash. Approval alone never sends a signal.
        crash_consent = None
        if args.case in ('G05', 'G06'):
            progress('OWNER_SHELL_CRASH_CONSENT_VERIFY')
            if args.shell_crash_consent is None:
                raise RuntimeError('SHELL_CRASH_CONSENT_MISSING_BEFORE_GOAL')
            crash_consent = consume_shell_consent(
                args.shell_crash_consent, args.case, args.source_sha,
                args.launch_pid, os.environ['ROS_DOMAIN_ID'],
                os.environ['GZ_PARTITION'])
            report['crash_consent_approved_before_goal'] = True
            progress('OWNER_SHELL_CRASH_CONSENT_CONFIRMED')
        # In addition to shell-level per-case TTY consent, do not start unless
        # the correct actual Supervisor health and final command graph remain.
        snap=obs.snapshot()
        if snap['final_publishers'] != [('axia_base_command_guard','geometry_msgs/msg/Twist')]:
            raise RuntimeError('FINAL_CMD_PUBLISHER_NOT_UNIQUE')
        # Bound the approval pause and fail before /start or Goal if the
        # executor or physical sensors stopped updating while the Owner typed.
        if args.case in ('G05', 'G06'):
            now=time.monotonic()
            if (not snap.get('clock_advancing') or
                    any(not isinstance(snap.get(k+'_at'),(float,int))
                        or not 0 <= now-snap[k+'_at'] <= 0.5
                        for k in ('scan','odom','guard','supervisor','clock'))):
                raise RuntimeError('OWNER_APPROVAL_RETURNED_BUT_ROS_OBSERVER_STALE')
        # Owner consent may take seconds: ensure every process is still
        # in the same session/partition and no PID was recycled during TTY IO.
        second_owners = inspect_pre_goal_processes(
            args.launch_pid, args.source_sha, actual, os.environ)
        with (folder/'pre_goal_process_recheck.json').open('x') as fp:
            json.dump(second_owners, fp, indent=2, sort_keys=True)
            fp.write('\n')
        if (second_owners['status'] != 'P2_PRE_GOAL_PID_CANDIDATE'
                or second_owners['pid_by_role'] != first_owners['pid_by_role']):
            raise RuntimeError('PRE_GOAL_PROCESS_RECHECK_BLOCKED:'+
                               second_owners.get('reason','PID_CHANGED'))
        progress('THREE_ROLE_POST_TTY_PID_PASS')
        _call_start(node,obs)
        if not wait_for(lambda:obs.data()['supervisor'].get('state')=='NORMAL',4):
            raise RuntimeError('SUPERVISOR_NOT_NORMAL_AFTER_START')
        pub=_publish_goal(node,obs,demo_corridor=args.mvp_relocated_obstacle)
        progress('NAV2_GOAL_PUBLISHED')
        if args.case in ('G05','G06'):
            verdict,raw=_fault_case(args.case,node,obs,folder,args.launch_pid,args.source_sha,crash_consent)
        else:
            # Never move any obstacle without real, Owner-approved Nav2 motion,
            # exact Guard/CM command graph and live owned Goal UUID.
            motion_gate=before_moving_g07_slowdown if args.mvp_one_goal else before_moving_fault
            last_motion_reason='NO_OBSERVER_SAMPLE'
            def owned_moving_snapshot():
                nonlocal last_motion_reason
                snap=obs.snapshot()
                ok,last_motion_reason=motion_gate(snap)
                return snap if ok else None
            if not wait_for(owned_moving_snapshot,10):
                raise RuntimeError('G07_NO_ACTUAL_SUPERVISED_MOTION:'+last_motion_reason)
            if args.mvp_one_goal:
                verdict,raw=_mvp_one_goal_case(obs,folder,args.source_sha,world_anchor,fixture)
            else:
                verdict,raw=_zone_case(
                    obs,folder,args.source_sha,
                    folder/'g07_native_contacts.log',world_anchor,fixture,
                    demo_corridor=args.mvp_relocated_obstacle)
        (folder/'quantitative_input.json').write_text(json.dumps(raw,indent=2,sort_keys=True)+'\n')
        check,reason=check_case_result(verdict)
        if not check:raise RuntimeError(reason)
        report.update(status=verdict['status'],reason=verdict['reason'],
                      numerical_candidate=verdict.get('numerical_candidate',False),
                      measured_stop_latency_sec=verdict.get('measured_stop_latency_sec'),
                      gate_accepted=False)
        print('P2_L3_'+args.case+'_'+report['status']+' RAW_REVIEW_REQUIRED')
        return 0 if report['status']=='NUMERICAL_CANDIDATE' else 2
    except Exception as exc:
        progress('BLOCKED_EXCEPTION_'+type(exc).__name__)
        report.update(status='BLOCKED',reason=type(exc).__name__+':'+str(exc)[:160],gate_accepted=False)
        print('P2_L3_'+args.case+'_BLOCKED '+report['reason'],file=sys.stderr)
        return 2
    finally:
        if executor is not None:executor.shutdown(timeout_sec=2)
        if thread is not None:thread.join(timeout=2)
        if obs is not None:obs.close()
        if node is not None:node.destroy_node()
        try:
            if rclpy.ok():rclpy.shutdown()
        except Exception:pass
        if contact_proc is not None:
            contact_proc.terminate()
            try:contact_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:contact_proc.kill();contact_proc.wait(timeout=3)
        if contact_stream is not None:contact_stream.close()
        faulthandler.disable()
        trace_file.close()
        progress('OWNER_RUN_FINALLY')
        progress_file.close()
        persist()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',choices=('G05','G06','G07'),required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-sha',required=True)
    p.add_argument('--launch-pid',type=int,required=True)
    p.add_argument('--shell-crash-consent',type=Path)
    p.add_argument('--mvp-one-goal',action='store_true',help='Original short P1 Goal; retained for regression only')
    p.add_argument('--mvp-relocated-obstacle',action='store_true',
                   help='G07-only 1.237m free-map corridor, preloaded CLEAR then real moving SLOW/STOP; Owner TTY needed')
    args=p.parse_args()
    if args.mvp_one_goal and args.mvp_relocated_obstacle:
        p.error('G07 demo modes are mutually exclusive')
    if args.mvp_relocated_obstacle and args.case!='G07':
        p.error('--mvp-relocated-obstacle requires G07')
    if args.mvp_relocated_obstacle and os.environ.get('AXIA_P2_G07_RELOCATED_OBSTACLE')!='1':
        p.error('--mvp-relocated-obstacle needs Owner shell simulation marker')
    if args.mvp_one_goal and args.case!='G07':
        p.error('--mvp-one-goal only applies to G07 simulation')
    if args.mvp_one_goal and os.environ.get('AXIA_P2_MVP_ONE_GOAL')!='1':
        p.error('--mvp-one-goal requires shell-set AXIA_P2_MVP_ONE_GOAL=1')
    return run(args)

if __name__=='__main__':raise SystemExit(main())
