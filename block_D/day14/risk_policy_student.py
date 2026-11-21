"""AXIA D14 교육용 G09 P/N/U -> LIMITED 요청 정책 (미완성 TODO).

원본: P3 staging p3_g09_risk_policy.py, Git blob 818a89077e95682c15906fba603b6eb8fe599d2c.
이 파일은 학생용 독립 구현 대상입니다. 실제 Supervisor/Guard/Goal 권한 없음.
"""
from dataclasses import dataclass
import math

VALID_SCOPE = "SYNTHETIC_ROS_L1_NO_MOTION"
MAX_RECEIPT_AGE_SEC = 0.5

@dataclass(frozen=True)
class RiskState:
    last_seq: int = -1
    last_rx_mono: float | None = None
    ever_received: bool = False
    limited_by_risk: bool = False
    last_verdict: str = "NONE"

def apply_verdict(state, payload, *, now_mono, unique_source, owned_goal, healthy):
    """TODO: 원본 S04 위험정책의 반환값 (RiskState, action) 계약 구현.

    1. monotonic 시계, 상태를 검증하십시오.
    2. Goal 소유권/건강 조건이 없으면 어떤 이동 권한도 만들지 마십시오.
    3. 출처, 유일한 발행자, seq 증가·중복·역행, payload를 검사하십시오.
    4. P/U/불명확 출처는 LIMITED 요청, N은 기존 제한을 절대 해제하지 않습니다.
    5. 반환되는 action은 가상 정책 출력일 뿐, /cmd_vel 명령이 아닙니다.
    """
    if not isinstance(state, RiskState) or type(now_mono) not in (int,float) or not math.isfinite(now_mono):
        raise ValueError("INVALID_RISK_STATE_OR_HOST_CLOCK")
    if not owned_goal or not healthy:
        return state, "NO_OWNED_HEALTHY_GOAL"
    return state, "D14_TODO_NOT_IMPLEMENTED"  # intentionally RED

def expired_verdict(state, *, now_mono):
    """TODO: 최초 수신 전 부팅 정상 유지; 수신 이후 0.5초 초과/시계 역행은 stale."""
    return False  # intentionally RED for stale input
