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
                "worst_io_operations":worst,
                "first_gap_nearby_io":near_io,
                "first_gap_within_scoped_window":bool(earliest)}
