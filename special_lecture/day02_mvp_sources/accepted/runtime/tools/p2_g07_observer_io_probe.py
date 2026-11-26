"""Bounded, numeric-only ROS Observer callback I/O timing diagnostics.

No ROS imports, publishers, safety decisions, Goal authority or disk I/O.
The same host monotonic domain supplies entry, lock wait, JSON, write/flush.
DDS RMW source/received epochs are NOT converted to this clock domain.
"""
from collections import deque
import math

LIMIT_SEC={"pre_guard":.120,"supervised":.150,"guard":.150,
           "supervisor":.150,"odom":.300,"scan":.300,"clock":.300}


class BoundedObserverIoProbe:
    def __init__(self, max_samples=12000):
        if type(max_samples) is not int or not 2 <= max_samples <= 20000:
            raise ValueError("G07_OBSERVER_IO_PROBE_BOUNDED_CAPACITY_REQUIRED")
        self.rows=deque(maxlen=max_samples)
        self.total=0
        self.invalid=0

    def record(self,kind,t,started_ns,locked_ns,json_done_ns,
               write_done_ns,flush_done_ns,finalized_ns,did_flush):
        self.total+=1
        marks=(started_ns,locked_ns,json_done_ns,write_done_ns,
               flush_done_ns,finalized_ns)
        if (not isinstance(kind,str) or
            type(t) not in (float,int) or not math.isfinite(t) or
            any(type(x) is not int or x<0 for x in marks) or
            any(b<a for a,b in zip(marks,marks[1:])) or
            type(did_flush) is not bool):
            self.invalid+=1
            return
        self.rows.append((kind,float(t),*marks,did_flush))

    def summary(self,*,start=None,end=None,heartbeats=()):
        rows=list(self.rows)
        dropped=max(0,self.total-len(rows)-self.invalid)
        scope=(type(start) in (float,int) and
               type(end) in (float,int) and
               math.isfinite(start) and math.isfinite(end) and
               0<=start<end)
        scoped=[r for r in rows if scope and start<=r[1]<=end]
        pairs={}
        first={}
        by_kind={}
        for row in scoped:
            if row[0] in LIMIT_SEC:
                by_kind.setdefault(row[0],[]).append(row[1])
        for kind,values in by_kind.items():
            values.sort()
            candidates=[(a,b) for a,b in zip(values,values[1:]) if b>a]
            if not candidates:
                continue
            pairs[kind]=round(max(b-a for a,b in candidates)*1000,6)
            for a,b in candidates:
                if b-a > LIMIT_SEC[kind]+1e-9:
                    first[kind]={"kind":kind,"previous_at":round(a,9),
                                 "current_at":round(b,9),
                                 "gap_ms":round((b-a)*1000,6),
                                 "limit_ms":round(LIMIT_SEC[kind]*1000)}
                    break
        earliest=(min(first.values(),key=lambda x:(x["current_at"],x["kind"]))
                  if first else None)
        near=[v for v in first.values()
              if earliest and
              abs(v["current_at"]-earliest["current_at"])<=.05]
        def duration(row,idx0,idx1):
            return round((row[idx1]-row[idx0])/1e6,6)
        def condensed(row):
            return {"kind":row[0],"at":round(row[1],9),
                    "lock_wait_ms":duration(row,2,3),
                    "json_ms":duration(row,3,4),
                    "write_ms":duration(row,4,5),
                    "flush_ms":duration(row,5,6) if row[8] else 0.,
                    "lock_held_ms":duration(row,3,7),
                    "did_flush":row[8]}
        details=[condensed(row) for row in rows]
        def mx(key):
            return max((d[key] for d in details),default=0.)
        worst=sorted(details,key=lambda r:(r["lock_wait_ms"]+
                                          r["json_ms"]+
                                          r["write_ms"]+
                                          r["flush_ms"]),reverse=True)[:24]
        near_io=[d for d in details
                 if earliest and abs(d["at"]-earliest["current_at"])<=.5][:160]
        heartbeats=[x for x in heartbeats
                    if type(x) in (float,int) and math.isfinite(x)]
        beats=sorted(heartbeats)
        heartbeat_max=max(((b-a)*1000 for a,b in zip(beats,beats[1:])),
                          default=None)
        heartbeat_window=[round(x,9) for x in beats if
                          earliest and abs(x-earliest["current_at"])<=.5][:100]
        # Compare *only* the heartbeat interval inside the FIRST ROS
        # callback gap. Global heartbeat maximum elsewhere in the run
        # cannot prove first-gap process/GIL/host starvation.
        inside_first=[x for x in beats if earliest and
                      earliest["previous_at"] <= x <= earliest["current_at"]]
        first_hb_max=(max(((b-a)*1000 for a,b in zip(
            inside_first,inside_first[1:])),default=None)
                      if len(inside_first)>=2 else None)
        first_hb_covered=(bool(earliest) and len(inside_first)>=3
                          and inside_first[0]-earliest["previous_at"]<=.04
                          and earliest["current_at"]-inside_first[-1]<=.04)
        return {"schema":"axia.g07.observer_callback_io_probe.v1",
                "status":("PROBE_CAPTURED_FIRST_BOUNDARY_UNPROVEN_HOLD"
                          if scope and rows and dropped==0 and self.invalid==0
                          else "PROBE_DROPPED_OR_SCOPE_UNVERIFIED_HOLD"),
                "release":"HOLD","timing_safety_pass":False,
                "root_cause_proven":False,"io_root_cause_proven":False,
                "certified_estop":False,"owner_l3_accepted":False,
                "original_120_150_300ms_limits_unchanged":True,
                "captured":len(rows),"dropped":dropped,"invalid":self.invalid,
                "flush_count":sum(1 for row in rows if row[8]),
                "max_lock_wait_ms":mx("lock_wait_ms"),
                "max_json_ms":mx("json_ms"),
                "max_write_ms":mx("write_ms"),
                "max_flush_ms":mx("flush_ms"),
                "max_lock_held_ms":mx("lock_held_ms"),
                "first_violation":earliest,
                "first_per_channel":first,
                "correlated_channels":sorted(x["kind"] for x in near),
                "observer_max_interarrival_ms":pairs,
                "heartbeat_max_gap_ms":(
                    round(heartbeat_max,6) if heartbeat_max is not None else None),
                "heartbeat_in_first_gap_window":heartbeat_window,
                "first_violation_heartbeat_count":len(inside_first),
                "first_violation_heartbeat_max_gap_ms":(
                    round(first_hb_max,6) if first_hb_max is not None else None),
                "first_violation_heartbeat_coverage":first_hb_covered,
                "process_wide_stall_at_first_violation_proven":False,
                "worst_io_operations":worst,
                "first_gap_nearby_io":near_io,
                "first_gap_within_scoped_window":bool(earliest)}


class FirstExecutorSilenceSnapshot:
    """CI-only one-shot bounded thread *function* snapshot at first global silence.

    Runs in an existing 20ms heartbeat thread, not in ROS callbacks. Captures
    no file paths, locals, arguments, source lines, Goal UUIDs or raw rosbag.
    A stack snapshot is evidence for follow-up, NEVER proof of causal root.
    """
    def __init__(self, threshold_ms=160):
        if type(threshold_ms) is not int or not 120 <= threshold_ms <= 250:
            raise ValueError("G07_EXECUTOR_SILENCE_THRESHOLD_INVALID")
        self.threshold_ms=threshold_ms
        self._result=None

    def capture(self, *, now,last_callback_at,goal_active,
                spin_thread_ident,threads=None,frames=None,
                spin_started_at=None,spin_timeout_ms=None):
        if self._result is not None or goal_active is not True:
            return False
        if (type(now) not in (int,float)
                or type(last_callback_at) not in (int,float)
                or not (math.isfinite(now) and math.isfinite(last_callback_at))
                or type(spin_thread_ident) is not int):
            return False
        silence_ms=(now-last_callback_at)*1000.
        if not self.threshold_ms <= silence_ms <= 1000.:
            return False
        import sys
        import threading
        import re
        threads=list(threading.enumerate() if threads is None else threads)
        frames=sys._current_frames() if frames is None else frames
        by_role={}
        pools=0
        for th in threads:
            tid=getattr(th,"ident",None)
            if tid==spin_thread_ident:
                role="executor_spin"
            elif (str(getattr(th,"name","")).startswith("ThreadPoolExecutor")
                  and pools<2):
                role="executor_pool_"+str(pools)
                pools+=1
            else:
                continue
            names=[]
            fr=frames.get(tid)
            while fr is not None and len(names)<8:
                name=str(fr.f_code.co_name)
                safe=re.sub(r"[^a-zA-Z0-9_]","_",name)[:64]
                names.append(safe)
                fr=fr.f_back
            by_role[role]=names
        # Both instants use one host monotonic clock, never DDS epochs.
        spin_elapsed=None
        if (type(spin_started_at) in (int,float) and math.isfinite(spin_started_at)
                and 0<=spin_started_at<=now):
            value=(now-spin_started_at)*1000.
            if 0<=value<=1000:
                spin_elapsed=round(value,6)
        timeout=(spin_timeout_ms if type(spin_timeout_ms) is int
                 and 1<=spin_timeout_ms<=100 else None)
        self._result={
            "spin_once_inflight_elapsed_ms":spin_elapsed,
            "spin_once_requested_timeout_ms":timeout,
            "spin_once_timeout_overrun_observed":(
                spin_elapsed is not None and timeout is not None
                and spin_elapsed>timeout),
            "schema":"axia.g07.first_executor_silence_stack.v1",
            "status":("FIRST_EXECUTOR_SILENCE_STACK_CAPTURED_HOLD"
                      if by_role.get("executor_spin") else
                      "FIRST_EXECUTOR_SILENCE_STACK_UNAVAILABLE_HOLD"),
            "silence_ms":round(silence_ms,6),
            "threshold_ms":self.threshold_ms,
            "thread_roles":sorted(by_role),
            "frames_by_role":by_role,
            "release":"HOLD","root_cause_proven":False,
            "timing_safety_pass":False,"certified_estop":False}
        return True

    def result(self):
        if self._result is None:
            return {"schema":"axia.g07.first_executor_silence_stack.v1",
                    "status":"FIRST_EXECUTOR_SILENCE_NOT_CAPTURED_HOLD",
                    "release":"HOLD","root_cause_proven":False,
                    "timing_safety_pass":False,"certified_estop":False}
        return dict(self._result)


def select_bounded_executor_wait_candidate(env, *, owner_mode=False):
    """Opt-in CI-only 20ms MultiThreadedExecutor wait-set A/B; never Owner.

    This changes the scheduling experiment's wait horizon, not the existing
    two workers, callback groups, ROS QoS, safety TTLs, Goal or evidence.
    A correct run may STILL fail inter-node 120/150/300ms, never safety PASS.
    """
    if not isinstance(env,dict) and not hasattr(env,"get"):
        raise ValueError("G07_BOUNDED_WAIT_ENV_INVALID")
    raw=env.get("AXIA_G07_CI_EXECUTOR_WAIT_BOUNDED_AB","0")
    if raw not in ("0","1"):
        raise ValueError("G07_BOUNDED_WAIT_AB_INVALID_VALUE")
    if raw=="0":
        return False
    required={
        "GITHUB_ACTIONS":"true",
        "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
        "AXIA_P0_SIM_ONLY":"1",
        "AXIA_G07_CI_OWNER_OBSERVER_PARITY":"1",
        "AXIA_G07_OBSERVER_IO_PROBE":"1",
    }
    if (owner_mode or any(env.get(k)!=v for k,v in required.items())
            or env.get("AXIA_G07_EVENTS_EXECUTOR_AB","0")!="0"):
        raise ValueError("G07_BOUNDED_WAIT_REQUIRES_CI_MULTI2_READONLY_AB")
    return True


def select_ci_executor_guard_wake_ab(env, *, owner_mode=False):
    """One CI-only controlled A/B: wake existing Multi2 guard every 20ms.

    Relies only on Jazzy Executor.wake() (its existing GuardCondition).
    No new ROS node/publisher, callback group, worker or safety logic.
    Never available to Owner WSL2; cannot grant timing/Goal PASS.
    """
    raw=env.get("AXIA_G07_CI_EXECUTOR_GUARD_WAKE_AB","0")
    if raw not in ("0","1"):
        raise ValueError("G07_EXECUTOR_GUARD_WAKE_AB_INVALID")
    if raw=="0":
        return False
    needed={"GITHUB_ACTIONS":"true","AXIA_P0_SIM_ONLY":"1",
            "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
            "AXIA_G07_CI_OWNER_OBSERVER_PARITY":"1",
            "AXIA_G07_OBSERVER_IO_PROBE":"1"}
    if (owner_mode or any(env.get(k)!=v for k,v in needed.items())
            or env.get("AXIA_G07_EVENTS_EXECUTOR_AB","0")!="0"
            or env.get("AXIA_G07_CI_EXECUTOR_WAIT_BOUNDED_AB","0")!="0"):
        raise ValueError("G07_EXECUTOR_GUARD_WAKE_REQUIRES_ORIGINAL_CI_MULTI2")
    return True
