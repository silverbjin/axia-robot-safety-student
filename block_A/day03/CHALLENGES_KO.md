# D03 응용 과제 2개 — 선택/심화 (필수 30개 GREEN 후 진행)

`block_A/day03/challenges.py`의 두 **TODO 함수만** 수정한다. 공개 채점은 `bash block_A/day03/scripts/run_lab.sh challenges`이며, 필수 실습 합격 여부와 별개다. ROS·Gazebo 불필요.

## 응용 1. 건강 신호의 명시적 실패 우선순위

**문제 상황:** 상태가 NORMAL이지만 `scan_ok=false`, `nav2_action_ready=false`, `cm_lifecycle_ok=null`이다. 보고 가능한 확정 고장과 모르는 상태를 구별해야 한다.

**입력:** `raw_json: str` — `health_diagnostics` dict를 포함한 P1 합성 JSON.

**출력:** `tuple[str, ...]` — 핵심 신호 `(clock_ok, scan_ok, graph_ok, cm_lifecycle_ok, nav2_action_ready)`의 **정해진 순서**대로 정확히 Boolean `False`인 키만 나열.

**제약:** 누락/None은 실패(False)가 아니라 미확인으로 취급. JSON 오류 또는 `health_diagnostics`가 객체가 아니면 `ValueError`; 원본 문자열 로그 출력 금지.

**기대:** `{'scan_ok':false,'cm_lifecycle_ok':null,'nav2_action_ready':false}` → `('scan_ok','nav2_action_ready')`.

## 응용 2. 고장 후 수동 복구 래치 유지

**문제 상황:** 센서 진단 `ERROR → OK → OK`가 입력돼도 P1은 옛 Goal을 자동으로 재개해서는 안 된다.

**입력:** `samples: list[DiagnosticSample]`; 각 샘플 `observed_mono`는 이 간단한 합성 시퀀스의 현재 monotonic 시간으로 해석.

**출력:** `list[Verdict]`. 기존 `assess_diagnostic()`를 재사용하되 앞선 `PROTECTIVE_STOP` 또는 `SW_STOP_LATCHED`가 나온 이후에는 기존 보호정지 이력을 유지한다. 이 교육용 함수에는 Reset/Rearm 서비스 호출이 없으므로 자동 해제하지 않는다.

**기대:** `ERROR → OK → OK` → `PROTECTIVE_STOP → RECOVERY_REQUIRED → RECOVERY_REQUIRED`.

## 확인

~~~bash
bash block_A/day03/scripts/run_lab.sh challenges
~~~

초기에는 `4 failed`가 의도된 RED다. 두 함수를 구현한 뒤 **`4 passed`**를 목표로 한다. 강사에게 본인 구현·테스트 출력·왜 자동 주행 재개를 허용하면 안 되는지 3문장으로 설명한다.