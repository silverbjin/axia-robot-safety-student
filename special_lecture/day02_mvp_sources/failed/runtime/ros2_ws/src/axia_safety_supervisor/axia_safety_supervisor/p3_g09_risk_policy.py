"""S04 non-certified P/N/U verdict -> safety LIMITED request policy.

ROS-free. The input is existing time-indexed P/N/U G09 fixture transport, NOT
a certified detector, owner authority, robot command, or independent sensor.
An invalid/unknown verdict cannot authorize speed. A received N is NEVER
permitted to remove a previous P/U or protective/manual safety restriction.
Only explicit S04 CI-enabled P2 Supervisor may consume it.
"""
from dataclasses import dataclass,replace
import math

VALID_SCOPE="SYNTHETIC_ROS_L1_NO_MOTION"
MAX_RECEIPT_AGE_SEC=.5


@dataclass(frozen=True)
class RiskState:
    last_seq:int=-1
    last_rx_mono:float|None=None
    ever_received:bool=False
    limited_by_risk:bool=False
    last_verdict:str="NONE"


def _finite(x):
    return type(x) in (int,float) and math.isfinite(x)


def apply_verdict(state, payload, *, now_mono, unique_source, owned_goal, healthy):
    """Returns (next RiskState, action) -- no ROS command or Goal authority."""
    if not isinstance(state,RiskState) or not _finite(now_mono):
        raise ValueError("INVALID_RISK_STATE_OR_HOST_CLOCK")
    if not owned_goal or not healthy:
        return state,"NO_OWNED_HEALTHY_GOAL"
    if not unique_source or not isinstance(payload,dict):
        return replace(state,limited_by_risk=True,last_verdict="U",
                       ever_received=True,last_rx_mono=now_mono),"LIMIT_ON_UNTRUSTED"
    seq=payload.get("seq")
    if type(seq) is not int or seq<0:
        return replace(state,limited_by_risk=True,last_verdict="U",
                       ever_received=True,last_rx_mono=now_mono),"LIMIT_ON_INVALID_SEQUENCE"
    if seq<=state.last_seq:
        # Duplicate/replayed N cannot clear risk; a stale transport will
        # separately constrain motion through expired_verdict().
        return state,"REJECT_REPLAY_OR_REORDERED"
    if (payload.get("scope")!=VALID_SCOPE or payload.get("gate_accepted") is not False
            or payload.get("goal_sent") is not False
            or payload.get("certified_estop") is not False):
        return replace(state,last_seq=seq,last_rx_mono=now_mono,ever_received=True,
                       limited_by_risk=True,last_verdict="U"),"LIMIT_ON_INVALID_PROVENANCE"
    label=payload.get("verdict")
    if label not in ("P","N","U"):
        label="U"
    if label=="N":
        next_state=replace(state,last_seq=seq,last_rx_mono=now_mono,
                           ever_received=True,last_verdict="N")
        return next_state,("KEEP_LIMITED_NO_AUTOMATIC_CLEAR" if state.limited_by_risk
                           else "NORMAL_UNCHANGED_NO_FALSE_RISK")
    return replace(state,last_seq=seq,last_rx_mono=now_mono,
                   ever_received=True,last_verdict=label,limited_by_risk=True),(
                       "LIMIT_ON_PREDICTED_P" if label=="P" else "LIMIT_ON_UNKNOWN_U"
                   )


def expired_verdict(state, *, now_mono):
    """Any previously received non-limiting N becomes restrictive if stale.

    Never clears a latched/limited state or invents an authorized Goal.
    """
    if not isinstance(state,RiskState) or not _finite(now_mono):
        return True
    if not state.ever_received or state.last_rx_mono is None:
        return False  # before first S04 fixture, normal G07 startup untouched
    return (now_mono<state.last_rx_mono
            or now_mono-state.last_rx_mono>MAX_RECEIPT_AGE_SEC)
