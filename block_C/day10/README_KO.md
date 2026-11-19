# D10 — Isolation Forest 정상 기준 이상탐지·조기 경고 검증

**2026-11-20(금) 19:00–22:00**, 이론 60분/실습 120분. 합성 데이터 (`SYNTHETIC_COURSE_FIXTURE`)만 사용합니다. 실제 TurtleBot3 계측이나 인증 E-Stop이 아닙니다.

**학습 목표 1:** Isolation Forest 기반 이상신호 탐지 구조 이해.  
**학습 목표 2:** 정상 패턴 기준 이상탐지 및 조기 경고 검증 실습.

학습 순서:
1. **[학생용 데모 관찰 가이드](STUDENT_DEMO_GUIDE_KO.md)** — 시스템 아키텍처·원본→특징·Train/Valid/Test와 강사 라이브 화면의 기대 결과.
2. **[학생용 120분 실습 가이드](STUDENT_LAB_GUIDE_KO.md)** — Python 3.12 환경·원본 무결성·D09 6특징 입력 확보·TODO 구현·출력 검증·첫 경고 분석.
3. `student_if_todo.py`의 `fit_evaluate_if`는 초기 `NotImplementedError` 상태이며 **정답 미포함**입니다.

기준 데이터: Raw **4,599행/46 Trace**, 6개 특징, Train **240 VALID 정상** / Valid **80 VALID 정상** / Test **100 VALID + 품질 오류 4**. Normal Train에 대해서만 model/scaler를 fit하고 정상 Valid만으로 95% 분위 threshold를 정하며 Test는 마지막 평가에만 사용합니다.

학생용 기초 확인:
~~~bash
bash block_C/scripts/block_c_once.sh --doctor
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d10
~~~

`NotImplementedError`로 시작하는 D10 실패는 학습자의 **EXPECTED_RED**입니다. 이 공개 테스트만 GREEN으로 바꾸어도 점수 누수·품질·평가 타이밍 검증이 끝난 것은 아니므로 실습 가이드의 실제 입력·산출물 점검을 따릅니다. 공개 스캐폴드 CI는 정답이 포함되지 않았는지 확인하며 학생 개별 풀이 PASS를 뜻하지 않습니다.

**안전 경계:** AI score는 비인증 교육용 WARNING이며 기존 Safety Supervisor/FSM/Stop/Nav2/Goal/`cmd_vel`을 변경하거나 발행하지 않습니다.
