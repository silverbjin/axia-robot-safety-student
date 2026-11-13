# AXIA Block B D06 — 학생용 3시간 실습 가이드

- **일시:** 2026-11-16(월) 19:00–22:00. 이론 60분 / 실습 120분
- **주제:** Safety Bubble — 거리 판정과 공식 Nav2 Collision Monitor의 차이
- **환경:** Windows WSL2 Ubuntu 24.04; 필수 Python 3.12 + pytest 8.3.5. ROS 2 Jazzy는 강사 전용 격리 L1 실험에 사용한다.
- **공개 소스:** https://github.com/silverbjin/axia-robot-safety-student (block_B/day06)
- **강의 한 줄 목표:** D05에서는 사람이 어디 있고 얼마나 멀리 있는지 **관측**했다. D06에서는 가까워진 장애물을 다룰 때 어떤 **보호 정책**이 필요한지 검증한다.

> 실습 함수는 **교육용 예상 상태/비율만 반환한다.** 로봇을 구동하거나 /cmd_vel을 발행하지 않는다. 실제 ROS L1 실습은 공식 nav2_collision_monitor를 로봇과 격리한 테스트 토픽에서 검증한다. STOP 명령은 차체 정지 또는 인증된 HW E-Stop 증거가 아니다.

## 1. 학습 목표 및 통과 기준

1. CLEAR·SLOWDOWN·STOP·UNKNOWN의 의미, 두 반경과 경계 포함 규칙을 설명한다.
2. classify_range()와 bubble_policy()의 **학생 TODO**를 RED → GREEN으로 해결하고 테스트 출력을 보존한다.
3. 공식 Nav2 Collision Monitor의 StopZone·SlowZone·min_points·observation_sources·source_timeout과 실제 cmd 입력/출력의 차이를 설명한다.
4. 실제 격리 CM 출력 0.20/0.06/0.00 m/s가 **ROS 통합 L1**의 증거임을 이해하고, /odom·물리 접촉·Goal·HW E-Stop을 검증한 적 없음을 설명한다.

## 2. 수업 시간표

| 시간 | 구간 | 작업 / 증거 |
|---|---|---|
| 19:00–20:00 | 이론 12개 주제 | D04/D05 → Safety Bubble → 공식 CM 구조·역할 |
| 20:00–20:10 | L1 환경 | Python·Git SHA 기록 |
| 20:10–20:25 | L2 YAML | CM stop/slow·scan·timeout 해설 |
| 20:25–20:45 | L3 RED | 학생 TODO 의도적 실패, 첫 NotImplementedError 추적 |
| 20:45–21:05 | L4 GREEN | 정상 1.20/0.65/0.30m 정책 구현 |
| 21:05–21:25 | L5 반례 | 0.40/0.75 경계·NaN·stale·UNKNOWN 검증 |
| 21:25–21:40 | L6 ROS L1 | 강사 CM 격리 시연·실측 출력/상태 표 작성 |
| 21:40–21:50 | L7 검토 | /cmd_vel 우회 여부·제어권/안전 용어 리뷰 |
| 21:50–22:00 | L8 제출 | 로그·SHA·평가표·미검증 명시 |

## 3. 실습 시작 — 터미널 사용법 (L1, 10분)

**터미널 S 하나만** 사용한다. D04/D05 작업 폴더를 보존하고 D06은 새 폴더로 복제한다. 이미 개인 D06 작업물이 있으면 새로 덮어쓰지 않는다.

~~~bash
(
  set -Eeuo pipefail
  REPO="$HOME/axia_d06_student_lab"
  if [ ! -e "$REPO" ]; then
    git clone --branch main --single-branch \
      https://github.com/silverbjin/axia-robot-safety-student.git "$REPO"
  fi
  cd "$REPO"
  test -f block_B/day06/safety_bubble_todo.py
  printf 'D06_STUDENT_SOURCE_SHA=%s\n' "$(git rev-parse HEAD)"
  python3 --version
  if [ ! -e .venv/bin/python ]; then python3 -m venv .venv; fi
  .venv/bin/python -m pip install -q 'pytest==8.3.5'
  mkdir -p "$HOME/axia_d06_student_evidence"
  .venv/bin/python -m compileall -q block_B/day06
)
~~~

**예상:** SHA 40자리, Python 3.12.x, 컴파일이 성공하면 오류 출력 없음. 실제 버전과 SHA를 제출 파일에 기록한다. 설치 오류는 소스 문제로 추정하지 말고 현재 네트워크·venv를 확인한다. ROS 환경이 자동 로드된 WSL2에서도 이후 pytest는 플러그인 자동 탐색을 끈다.

## 4. L2 — 공식 CM 설정 읽기 (15분)

교육용 격리 공식 YAML: https://github.com/silverbjin/axia-robot-safety-ci-public/blob/main/d06/params/collision_monitor_d06.yaml

| 항목 | 교육용 설정 | 의미 |
|---|---|---|
| StopZone | circle radius=0.40m, min_points=4 | 조건 충족 시 Twist 0으로 변환 |
| SlowZone | circle radius=0.75m, min_points=4, ratio=0.30 | 조건 충족 시 입력 명령을 감속 |
| observation_sources | scan | LaserScan 포인트를 대상으로 판정 |
| source_timeout | 0.5s | 센서 갱신이 늦으면 신뢰 불가, CLEAR 보장 아님 |
| cmd_vel_in_topic | /axia/d06/test/cmd_in | **격리** 명령 입력 |
| cmd_vel_out_topic | /axia/d06/test/cmd_out | **격리** 명령 출력. 실제 /cmd_vel 아님 |

**주의:** 학생 Python 입력의 distance_m 하나를 공식 CM에 그대로 넣는 것이 아니다. 공식 CM은 LaserScan·TF·영역 내 포인트 조건으로 행동을 결정한다. /axia/d06/test/scan은 교육용으로 만든 LaserScan이며 로봇 라이다의 실제 /scan이 아니다.

## 5. L3 — RED를 재현하고 실패 이유를 기록 (20분)

**터미널 S:**

~~~bash
cd "$HOME/axia_d06_student_lab"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.venv/bin/python -m pytest -q \
  block_B/day06/tests/test_d06_public.py::test_fixture_shape
set +e
.venv/bin/python -m pytest -q \
  block_B/day06/tests/test_d06_public.py \
  > "$HOME/axia_d06_student_evidence/d06_RED.log" 2>&1
RC=$?
set -e
cat "$HOME/axia_d06_student_evidence/d06_RED.log"
echo "D06_STUDENT_RED_RC=$RC"
~~~

**수정 전 예상:** fixture 검사는 `1 passed`; 전체 검사에서는 **`1 passed, 3 failed`**, 오류 `NotImplementedError: TODO_D06_CLASSIFY_RANGE` 및 `TODO_D06_BUBBLE_POLICY`, 종료코드가 0이 아님. 실행환경과 pytest 버전에 따라 실패 출력 순서나 소요 시간은 달라진다. 이것은 **학생에게 의도한 RED**이며 CI 전체 실패를 의미하지 않는다. 이미 본인이 구현한 함수는 GREEN일 수 있다. 기존 코드를 초기화하지 않는다.

질문: 첫 예외는 **테스트가 틀려서** 생긴 것인가, 아니면 **TODO 함수가 아직 구현되지 않아서** 발생했는가? 테스트를 지우거나 기대값을 고치지 말 것.

## 6. L4 — 정상 입력 GREEN (20분)

수정 범위는 **block_B/day06/safety_bubble_todo.py**의 `classify_range()`와 `bubble_policy()` 두 함수만. 다른 테스트/fixture는 변경하지 않는다.

정책은 다음과 같다.

| distance_m | valid | age_s | 기대 status | expected_ratio |
|---:|---|---:|---|---:|
| 1.20 | true | 0.0 | CLEAR | 1.0 |
| 0.65 | true | 0.0 | SLOWDOWN | 0.30 |
| 0.30 | true | 0.0 | STOP | 0.0 |
| None | false | 0.0 | UNKNOWN | None |

bubble_policy()는 status, expected_ratio, safety_certified=False, control_published=False를 담은 dict만 반환한다. **ROS 노드·토픽·파일 쓰기·실제 출력 Twist는 구현하지 않는다.**

~~~bash
cd "$HOME/axia_d06_student_lab"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/day06/tests/test_d06_public.py::test_student_all_distance_samples
~~~

**GREEN 기대:** `1 passed`. 아직 실패면 가장 먼저 타입/valid·age와 거리 비교 분기를 분리해 확인한다.

## 7. L5 — 경계·무효·stale 반례 GREEN (20분)

- d=**0.40m**는 STOP, d=**0.75m**는 SLOWDOWN (두 경계 포함).
- valid=false, None, NaN, Inf, 음수, bool, 숫자가 아닌 값 → UNKNOWN.
- age_s=**0.50s는 허용**, age_s=**0.51s는 UNKNOWN**. age가 음수/비유한 값이면 무효.
- 설정은 양수 `stop_radius < slowdown_radius`, `0 < slowdown_ratio < 1`, 유효한 max_age를 요구한다. 불법 설정은 ValueError.
- UNKNOWN의 비율은 `None`이며, CLEAR 또는 정지 인증으로 표시하지 않는다.

~~~bash
cd "$HOME/axia_d06_student_lab"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/day06/tests/test_d06_public.py \
  | tee "$HOME/axia_d06_student_evidence/d06_GREEN.log"
~~~

**학생 TODO를 올바르게 구현한 경우 기대:** `4 passed`. **이 문서는 실행 성공을 보증하지 않는다.** 이 수업에서 검증한 범위는 Python 합성 데이터 정책이다. 특히 `pytest 4 passed`는 실제 로봇 주행 성공이 아니다.

## 8. L6 — 공식 Nav2 Collision Monitor 격리 ROS L1 관찰 (15분)

이 구간은 **강사가 실행**한다. 학생은 기존 공개 증거 또는 강사 실시간 출력과 비교표를 작성한다. 학생은 **절대 /cmd_vel을 발행하거나 Nav2 Goal을 보내지 않는다.** Gazebo GUI가 나타나지 않는 것이 정상이다.

강사 공식 WSL2 원샷 가이드: 비공개 `training/block_B/instructor/D06_OWNER_WSL2_ONCE_KO.md`. 공개 실행기 pin은 `bc3fa7abe63ef3677bbf8b342e4aba96fd3e6ea1`; 내부 검증 소스 pin은 `94f4900f89f8e04c4d0a45461ac39ea9e13d6e6f`.

| 단계 | 입력 Twist | CM 출력 **기존 ROS L1 실측** | 관찰 상태 |
|---|---:|---:|---|
| 1.20m | 0.20m/s | 0.20m/s (22개) | CLEAR |
| 0.65m | 0.20m/s | 0.06m/s (22개) | SlowZone/action_type=2 |
| 0.30m | 0.20m/s | 0.00m/s (3개) | StopZone/action_type=1 |

**기존 검증 증거:** 공개 GitHub Actions https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42656227824 및 기존 강사 WSL2 원본 보고서. 위 값은 **과거 실측**이며 수업 당일 실측을 대신하여 꾸며낸 값이 아니다. 수업에서 실제 실행하면 새 verdict.json과 stdout으로 다시 확인한다.

### 강사 A / 선택 모니터 B 분리 원칙

- **강사 터미널 A:** 격리 원샷만 포그라운드 실행; 출력은 표준출력과 evidence 아래 runtime.log로 보존. 실행 완료시 자동 종료.
- **선택 강사 터미널 B:** A와 동일 ROS_DOMAIN_ID인 경우에만 읽기 전용 `ros2 topic list`, `ros2 topic info /axia/d06/test/cmd_out`를 확인할 수 있다. 짧은 시험이므로 화면을 놓칠 수 있으며 **최종 판정은 저장된 verdict.json**으로 한다. 터미널 B에서 `Ctrl+C`는 모니터만 닫는다.
- **학생 터미널 S:** ROS 시연을 하지 않고 TDD/실습 요약만 진행. 강사 실행과 충돌하지 않도록 별도 WSL2 셸 또는 PC에서 실행.

**소스 기반으로만 검사하는 명령 `--self-check` 결과는 ROS 실행 아님.** 실제 ROS 패키지 실행을 봤더라도 `/odom`, 물리 접촉, base watchdog의 지속 정지 등은 이 L1의 증거가 아니다.

## 9. L7 안전 리뷰 (10분)

체크: 학생 코드에 ROS publisher / `/cmd_vel` 호출이 없는가? `UNKNOWN`을 CLEAR로 반환하지 않는가? stop/slowzone 중첩에 STOP 우선인가? 격리 토픽이 실제 /cmd_vel과 다른가? SW Stop·인증 E-Stop을 혼동하지 않는가?

**중요 질문:** `cmd_out.linear.x=0`으로 확인할 수 있는 것은 **공식 CM이 출력 명령을 0으로 만들었다**는 사실뿐이다. 차체 실제 정지는 `/odom` 등 별도 증거, 물리 충돌은 시뮬레이터/센서 별도 증거가 필요하다.

## 10. L8 제출 및 종료 (10분)

제출 파일: `d06_RED.log`, `d06_GREEN.log`, 수정한 TODO 두 함수, 규칙표, CM YAML 해설, 강사 L1 상태/출력표, 검증 수준(`PYTHON_SYNTHETIC`/`ROS_L1_EXISTING_EVIDENCE`/`ROS_L1_NEW_LIVE`)과 미검증 항목, `git rev-parse HEAD`.

~~~bash
cd "$HOME/axia_d06_student_lab"
{
  printf 'STUDENT_BASE_SHA=%s\n' "$(git rev-parse HEAD)"
  git status --short
  echo 'D06_SCOPE=PYTHON_SYNTHETIC; ROBOT_ACTUATION_NOT_RUN'
} | tee "$HOME/axia_d06_student_evidence/d06_summary.txt"
~~~

종료: 학생 터미널 S에서 `exit`, 강사 A는 원샷 자동종료 또는 A에서 `Ctrl+C`, 강사 선택 B는 `Ctrl+C` 후 `exit`. 각 학생이 직접 실행한 프로세스만 종료한다. 다른 사람의 ROS 작업·기존 D04/D05 폴더를 `killall`, `reset --hard`, `clean -fd`로 일괄 삭제하지 않는다.

## 11. 학생 평가 루브릭 (100점)

| 항목 | 배점 | 확인할 증거 |
|---|---:|---|
| 4상태·경계 이해 | 20 | 1.20/0.65/0.30 및 0.40/0.75 설명 |
| RED → GREEN TDD | 30 | 의도적 실패 원인·pytest GREEN 또는 미완성 선언·원본 로그 |
| UNKNOWN 안전 해석 | 20 | NaN/stale/missing 반례, CLEAR로 승격 금지 |
| CM 설정·제어권 해석 | 20 | 공식 LaserScan zone/min_points/source_timeout, 격리 cmd in/out 구분 |
| 증거·검증 한계·종료 | 10 | SHA/실제 출력/미검증/올바른 종료 안내 |

**합격 권장 기준:** 70점 이상이면서 `/cmd_vel` 금지 준수, UNKNOWN을 CLEAR로 잘못 매핑하지 않을 것. 이 점수는 학습 평가 기준이지 실제 로봇 안전 인증이 아니다.

## 12. 막힐 때 선택지

- **venv/pytest 준비 실패:** 강사 출력과 기존 공개 fixture 표를 직접 해석하고 재실행 불가를 기록한다. GREEN으로 표시하지 않는다.
- **의도한 RED만 지속:** 마지막 오류보다 첫 `NotImplementedError`와 입력값 종류를 좁혀 수정한다. 테스트/fixture를 임의로 고치지 않는다.
- **강사 ROS L1 설치 또는 네트워크 실패:** 이미 보존된 성공 CI·WSL2 verdict을 **과거 증거**로 읽기 전용 시연하고, 이번 Live는 NOT_RUN/BLOCKED로 기록한다. 실패한 원샷을 반복하지 않는다.
- **교육 범위 종료:** Gazebo 물리 주행·Nav2 Goal·인증 E-Stop으로 실습을 확장하지 않는다.