# AXIA Day 2: SW Stop 래치와 복구 — 학생용 TODO

**목표:** 정지 래치와 fault 해제, 운영자 재승인을 분리하여 설명하고 Python 상태 모델을 구현한다.

1. `axia_student/stop_latch.py`의 네 TODO를 확인한다.
2. `pytest -q tests/test_stop_latch_behavior.py`를 실행하여 의도된 **RED**(NotImplementedError)를 확인한다.
3. 안전 상태에서 `motion_allowed=False`를 기본값으로 유지한다.
4. fault가 사라졌다는 사실만으로 자동 재주행/자동 rearm이 발생하지 않도록 한다.
5. `operator_approved=False`면 rearm을 거부한다.
6. fault 해제 전 재승인은 거부하고, 해제 후 운영자의 명시적 재승인으로 **새 Goal 수락 자격만** 회복한다. 기존 Goal의 자동 재개는 금지한다.
7. GREEN 후 수정된 설계와 테스트 증거를 코드 리뷰한다.

**공개 테스트는 최종 인수 테스트가 아니다.** 강사 정답과 Hidden Tests는 별도 비공개 저장소에서 관리한다. 소프트웨어 정지는 인증된 E-Stop이 아니다.
