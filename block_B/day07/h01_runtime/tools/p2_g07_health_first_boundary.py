"""Read-only bounded first HEALTH evidence for one native Jazzy/Gazebo session.

No ROS imports, clocks converted across domains, cmd_vel, Goal authority,
safety threshold adjustment, service calls or optimistic PASS.
"""
from collections import deque
import math


class HealthFirstBoundary:
    def __init__(self, *, max_samples=48):
        if type(max_samples) is not int or not 2<=max_samples<=128:
            raise ValueError("G07_HEALTH_BOUNDARY_BOUNDED_CAPACITY_REQUIRED")
        self.max_samples=max_samples
        self.samples=0
        self.first=None
        self.tail=deque(maxlen=max_samples)
        self.first_transition=None
        self._prev_state=None
        self._invalid=0

    def record(self, at, snap, data):
        if not (type(at) in (int,float) and math.isfinite(at)
                and isinstance(snap,dict) and isinstance(data,dict)):
            self._invalid+=1
            return
        supervisor=data.get("supervisor")
        supervisor=supervisor if isinstance(supervisor,dict) else {}
        guard=data.get("guard")
        guard=guard if isinstance(guard,dict) else {}
        health=supervisor.get("health_diagnostics")
        health=health if isinstance(health,dict) else {}
        state=supervisor.get("state")
        if type(state) is not str:state=None
        cm=health.get("cm_lifecycle_ok")
        if cm is not True:cm=cm if cm is False else None
        clock=bool(snap.get("clock_advancing") is True)
        scan_val=data.get("scan")
        scan_present=(type(scan_val) in (int,float) and
                      math.isfinite(scan_val))
        blockers=[]
        if cm is not True:blockers.append("cm_lifecycle_ok_not_true")
        if not clock:blockers.append("clock_not_advancing")
        if not scan_present:blockers.append("scan_missing")
        if guard.get("latched") is True:blockers.append("guard_latched")
        row={
            "at_host_monotonic":round(at,6),
            "supervisor_state":state,
            "cm_lifecycle_ok":cm,
            "clock_advancing":clock,
            "scan_present":scan_present,
            "guard_latched":guard.get("latched") is True,
            "health_clock_ok":health.get("clock_ok") is True,
            "health_scan_ok":health.get("scan_ok") is True,
            "health_graph_ok":health.get("graph_ok") is True,
            "nav2_action_ready":health.get("nav2_action_ready") is True,
            "blockers":blockers
        }
        for name in ("clock","scan","odom","guard","supervisor"):
            t=snap.get(name+"_at")
            if type(t) in (int,float) and math.isfinite(t) and at>=t:
                row[name+"_observer_age_ms"]=round((at-t)*1000,6)
            else:
                row[name+"_observer_age_ms"]=None
        self.samples+=1
        if self.first is None:self.first=row
        if (self._prev_state is not None and state is not None
                and state!=self._prev_state and self.first_transition is None):
            self.first_transition={"from":self._prev_state,"to":state,
                                   "at_host_monotonic":row["at_host_monotonic"]}
        if state is not None:self._prev_state=state
        self.tail.append(row)

    def result(self):
        first=self.first
        last=self.tail[-1] if self.tail else None
        # This status is *always* HOLD. Only the unchanged strict runner can
        # decide readiness and admit an authorized Goal in CI/Owner.
        return {
            "schema":"axia.g07.events_executor_first_health_boundary.v1",
            "status":"FIRST_HEALTH_READINESS_UNVERIFIED_HOLD",
            "release":"HOLD","root_cause_proven":False,
            "goal_sent":False,"owner_l3_accepted":False,
            "certified_estop":False,"safety_ttl_changed":False,
            "samples":self.samples,"invalid":self._invalid,
            "dropped_middle_samples":max(0,self.samples-len(self.tail)),
            "first_readiness_blockers":(
                list(first["blockers"]) if first else ["no_health_samples"]),
            "first_sample":first,"last_sample":last,
            "first_state_transition":self.first_transition,
            "tail_samples":list(self.tail)
        }
