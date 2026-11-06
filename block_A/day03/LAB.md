# D03 Diagnostics → Safe Mode (2026-11-11, 19:00–23:00)
**이론 2h + Python 실습 2h.** 대상은 학생용 합성 데이터 분류이며 실제 ROS/Gazebo/인증 E-Stop이 아니다.

## 목표
DiagnosticStatus의 OK=0/WARN=1/ERROR=2/STALE=3을 구분하고, monotonic 수신경과 시간과 SW Stop 우선순위로 보수적 모드 후보를 계산한다.

## 터미널 1: 새 Ubuntu 터미널 (ROS/Gazebo 터미널 열지 않음)
```bash
# 학생 저장소 root
python3 --version
python3 -m pytest --version
PYTHONPATH=block_A/day03 python3 -m pytest -q block_A/tests/test_safety_public.py
# 초기 의도된 RED 예시: 10 failed, 1 passed, exit=1
```

## 120분 실습
1. 15분: diag_events.jsonl 4개 시나리오 예측.
2. 15분: Dataclass·Verdict와 공개 테스트 읽기.
3. 35분: 입력/시간/level 유효성 검사 구현.
4. 25분: STOP > ERROR/STALE > RECOVERY > WARN/OK 우선순위 구현.
5. 20분: 테스트 RED→GREEN 및 콘솔 로그 저장.
6. 10분: 검증 경계·미검증 항목 보고.

```bash
PYTHONPATH=block_A/day03 python3 -m pytest -q block_A/tests/test_safety_public.py
# 정답 구현 검증 예시: 11 passed, exit=0
```
실패 조치: ImportError는 저장소 root와 PYTHONPATH 검사. TODO_NOT_IMPLEMENTED는 의도된 RED. `age>timeout`만 수신소실 판정. `NORMAL_CANDIDATE`는 주행 승인이 아니다.

**제출:** todo_safety.py, 원본 RED/GREEN 로그·exit code, Safe Mode 우선순위 설명, ROS_VERIFIED=NOT_RUN, GAZEBO_VERIFIED=NOT_RUN. 종료 시 터미널 1을 닫는다.
