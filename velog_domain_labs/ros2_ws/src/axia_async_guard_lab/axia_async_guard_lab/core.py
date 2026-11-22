from dataclasses import dataclass

@dataclass(frozen=True)
class SupervisorCommand:
    sent_monotonic:float
    velocity:float

@dataclass(frozen=True)
class GuardDecision:
    reason:str
    velocity:float

def guard_decision(now,cm_received_at,cm_velocity,recent_commands,*,
                   cm_ttl_sec=0.15,grace_sec=0.12,slowdown_ratio=0.30,tolerance=0.01):
    raise NotImplementedError("TODO 04: freshness, command history, ZERO-only")
