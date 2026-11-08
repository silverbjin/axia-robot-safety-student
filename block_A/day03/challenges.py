"""Two optional application challenges (no ROS or robot authority).

Leave ONLY two small core functions incomplete; fixtures/runner/tests already work.
"""
from __future__ import annotations

from todo_safety import DiagnosticSample, Verdict

CRITICAL_KEYS = ('clock_ok', 'scan_ok', 'graph_ok',
                 'cm_lifecycle_ok', 'nav2_action_ready')


def challenge1_failed_health(raw_json: str) -> tuple[str, ...]:
    """응용1: P1 JSON에서 명시적으로 False인 핵심 건강지표를 정해진 순서로 반환.

    A None or missing value is UNKNOWN, not False; invalid JSON is an input error.
    TODO: parse safely, validate health_diagnostics object and report failures.
    """
    raise NotImplementedError('TODO_CHALLENGE_01')


def challenge2_recovery_sequence(samples: list[DiagnosticSample], *,
                                 timeout_s: float = 0.5) -> list[Verdict]:
    """응용2: 고장 후 정상 진단으로 변해도 자동 복귀하지 않는 것을 시뮬레이션.

    Treat samples' observed_mono as each step's current monotonic time.
    Each assessed verdict PROTECTIVE_STOP or SW_STOP_LATCHED latches a stop.
    Without a separate authorized reset/rearm event, later OK stays
    RECOVERY_REQUIRED. Use assess_diagnostic; never issue real ROS commands.
    TODO: implement a pure list-of-Verdict transform.
    """
    raise NotImplementedError('TODO_CHALLENGE_02')