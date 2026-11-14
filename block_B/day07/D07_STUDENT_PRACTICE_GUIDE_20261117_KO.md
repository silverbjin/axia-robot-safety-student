# D07 학생용 실습 가이드 — 3시간 수업, TDD로 사람 회피 경로 판단하기

> **2026-11-17(화) 19:00–22:00 / 이론 60분 + 실습 120분.**  
> 기존 [D07 3시간 학습 가이드](D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md)와 [D07 학생 데모 가이드](D07_STUDENT_DEMO_GUIDE_20261117_KO.md)를 함께 사용한다.  
> ROS 2 Jazzy/Gazebo 설치는 이 학생 Python 실습의 필수 조건이 아니다. 수업 중 H01 실제 회피 주행은 **BLOCKED / NOT_RUN**이므로 학생에게 실제 이동 Goal이나 속도 명령을 요구하지 않는다.

## 수업 흐름과 산출물

| 시간 | 내용 | 학생이 남길 결과 |
|---|---|---|
| 19:00–20:00 | LO1 이론 — Nav2와 AXIA 구조, Costmap/Planner vs STOP, L1·H01 증거 구분 | 핵심 계층 책임 표 |
| 20:00–20:10 | 실습 1 — 설치·브랜치·SHA 확인 | `source_sha.txt` |
| 20:10–20:25 | 실습 2 — `routes.json` 실제 좌표 그림 | 경로 그림과 0.35m buffer |
| 20:25–20:45 | 실습 3 — **RED** | `d07_RED.log`, `red_rc.txt` |
| 20:45–21:10 | 실습 4 — **GREEN** (두 TODO만) | `d07_GREEN.log`, `green_rc.txt` |
| 21:10–21:25 | 실습 5 — `UNKNOWN` 반례 | 독립 반례 1개 |
| 21:25–21:40 | 실습 6 — 강사 공식 L1 / H01 원본 비교 | 실제 증거·미검증 구분표 |
| 21:40–21:50 | 실습 7 — 계획·제어·보호 계층 역할 | 주행제어 책임 표 |
| 21:50–22:00 | 실습 8 — 제출과 30초 설명 | 원본 로그와 회고 |

**학습 목표 1:** 사람을 동적 장애물로 처리하는 회피제어 구조 이해.  
**학습 목표 2:** 사람 회피 로직 및 주행제어 실습 — 이번 학생 과제는 *읽기 전용* 경로 판단과 실제 주행제어 증거 구분까지이다. **실제 H01 회피 주행 성공이 아님.**

## 준비 — 학생 터미널 S 하나만 열기

Ubuntu 24.04 또는 Python 3.12 사용 환경에서 **학생 저장소 전용 디렉터리**를 사용한다. 다른 D04~D06 폴더는 지우거나 초기화하지 않는다.

```bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d07_student_lab"
  BRANCH="docs/d07-3h-classroom-20261114"

  if [[ -e "$ROOT" && ! -d "$ROOT/.git" ]]; then
    echo "D07_ROOT_ALREADY_EXISTS_BUT_NOT_GIT — 다른 폴더 사용"; exit 2
  fi
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone --single-branch --branch "$BRANCH" \
      https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi

  cd "$ROOT"
  if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
    echo "D07_WRONG_BRANCH — 기존 작업 보존, 자동 reset 금지"; exit 3
  fi
  test -f block_B/day07/route_todo.py
  test -f block_B/day07/fixtures/routes.json

  mkdir -p "$HOME/axia_d07_student_evidence"
  git rev-parse HEAD | tee "$HOME/axia_d07_student_evidence/source_sha.txt"
  python3 --version
  if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
  .venv/bin/python -m pip install -q "pytest==8.3.5"
  .venv/bin/python -m compileall -q block_B/day07
  echo "D07_STUDENT_SETUP_OK_NO_ROS_NO_GOAL"
)
```

**예상:** Git SHA 40자리, Python 버전, `D07_STUDENT_SETUP_OK_NO_ROS_NO_GOAL` 표시. `venv`가 없는 경우 `python3-venv` 설치가 필요한지 먼저 확인한다. 설치 실패를 Python 소스 오류로 오판하지 않는다. 학생 터미널 S에서 ROS·Gazebo·Nav2 프로세스를 실행하지 않는다.

## 실습 2 — 합성 경로를 눈으로 확인하기

`block_B/day07/fixtures/routes.json`의 실제 좌표:

- 사람 대체 위치 `person_xy=(0.8,0)`m, 보호 buffer `0.35`m
- 원래 경로 `path_before`: `(0,0)`에서 `(1.5,0)`로 이어지는 7개 점
- 대체 경로 `path_detour`: `(0.25,0.25)`, `(0.75,0.55)`, `(1.25,0.3)` 등을 지나는 7개 점
- 기대 최소 이격: 원래 경로 약 `0.000`m (**BLOCKED**), 대체 경로 약 `0.515`m (**CLEAR**)

**작성 활동:** 두 경로와 buffer 원을 그림에 표시한 뒤, **경로 점이 아니라 연속 두 점이 만드는 선분**으로 거리를 재야 하는 이유를 한 문장으로 설명한다.

독립적인 fixture 스키마 확인:

```bash
cd "$HOME/axia_d07_student_lab"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
  block_B/day07/tests/test_d07_public.py::test_fixture_schema
```

**예상 출력:** `1 passed`. 실패하면 먼저 파일 경로, JSON 스키마, 저장소 브랜치를 확인한다.

## 실습 3 — RED: 구현하기 전에 실패 원인을 기록

`route_todo.py`를 수정하기 전에 공개 테스트를 실행한다. 이 테스트 실패는 의도된 학습 과정이다.

```bash
cd "$HOME/axia_d07_student_lab"
EVIDENCE="$HOME/axia_d07_student_evidence"
RC=0
(
  set -o pipefail
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
    block_B/day07/tests/test_d07_public.py 2>&1 \
    | tee "$EVIDENCE/d07_RED.log"
) || RC=$?
echo "D07_STUDENT_RED_RC=$RC" | tee "$EVIDENCE/red_rc.txt"
```

**초기 학생 TODO 예상:** `1 passed, 3 failed`, `NotImplementedError`, `D07_STUDENT_RED_RC`는 0이 아니다. 이미 두 함수를 구현한 학생은 실패하지 않을 수 있으니 코드를 억지로 삭제하지 말고 현재 상태를 기록한다. 테스트 자체를 고쳐 GREEN처럼 보이게 해서는 안 된다.

**문제 찾기:** 최초 실패 함수 이름, 호출한 인자, 반환되어야 할 결과, 왜 아직 실패하는지를 기록한다.

## 실습 4 — GREEN: 허용된 TODO 두 개만 작성

수정 허용 파일: `block_B/day07/route_todo.py` **단 하나**.

1. `route_obstacle_status(path, person_xy, valid, age_s, max_age_s=0.5, buffer_radius_m=0.35)`  
   입력 검증 → 각 선분과 사람 점의 최단 거리 계산 → `BLOCKED`/`CLEAR`/`UNKNOWN`. 경로가 비어 있거나 센서가 유효하지 않으면 **UNKNOWN**.
2. `assess_replan(path_before, path_after, person_xy, ...)`  
   이전 경로 `BLOCKED`, 새 경로 `CLEAR`일 때에만 `REPLAN_EVIDENCED`. 반환 결과의 `robot_moved`, `collision_free_verified`, `safety_certified`는 모두 **False**.

**알고리즘 힌트(정답 소스 아님):** 점 P를 선분 AB에 정사영한 비율을 0~1로 제한해 가장 가까운 위치를 구한다. 선분 길이가 0인 경우는 A까지의 거리로 계산한다. 모든 선분 거리 중 최솟값이 buffer 반경 이하이면 BLOCKED이다. **A*·Controller·속도 publisher·NavigateToPose 구현은 과제 범위 밖이다.**

구현 후 같은 테스트:

```bash
cd "$HOME/axia_d07_student_lab"
EVIDENCE="$HOME/axia_d07_student_evidence"
RC=0
(
  set -o pipefail
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
    block_B/day07/tests/test_d07_public.py 2>&1 \
    | tee "$EVIDENCE/d07_GREEN.log"
) || RC=$?
echo "D07_STUDENT_GREEN_RC=$RC" | tee "$EVIDENCE/green_rc.txt"
```

**정상 구현 시 예상:** `4 passed`, `D07_STUDENT_GREEN_RC=0`. 미통과하면 최소 한 반례를 고쳐 다시 실행한다. 출력만 보고 임의로 PASS로 기록하지 않는다.

## 실습 5 — UNKNOWN 반례를 직접 구성

| 조건 | 기대 결과 | 이유 |
|---|---|---|
| `person_xy=None` 또는 NaN | `UNKNOWN` | 물체 좌표가 유효하지 않음 |
| `age_s=0.51` (최대 0.5) | `UNKNOWN` | 합성 센서 데이터가 오래됨 |
| `age_s=0.50` | 경로에 따른 판정 | 허용된 경계값 |
| 경로 길이 0~1 또는 좌표 형식 오류 | `UNKNOWN` | 선분 거리 계산 불가 |
| 두 경로 모두 BLOCKED | `REPLAN_EVIDENCED` 금지 | 안전한 우회 경로 증거 없음 |

수업의 `max_age_s=0.5`는 **학생 Python 데이터 유효성 조건**이며 H01 실제 Scan/CM/Guard 안전 TTL을 검증한 값이 아니다. 반례 1개를 `unknown_case.md`에 입력·기대값·실제값·설명으로 제출한다.

## 실습 6~7 — 강사 데모와 연결하여 주행제어 증거 구분

[학생 데모 가이드](D07_STUDENT_DEMO_GUIDE_20261117_KO.md)의 실제 CI 원본 링크를 열고 아래를 기입한다.

| 단계 | 학생이 확인할 사실 | 실제 운동 증거 |
|---|---|---|
| L0 합성 fixture | `BLOCKED → CLEAR` 후보를 계산 | **없음** |
| L1 공식 Nav2 | Costmap `0→101→0`, Path `58→74→58` | **없음** |
| L2 H01 물리 장애물 | 실제 Scan과 공식 Nav2 우회 경로 약 0.573m 변경 | **없음: 주행 NOT_RUN** |
| Controller / Guard | `FollowPath`→최종 `/cmd_vel`→`/odom`이 실제 증거로 필요한 이유 | H01 미검증 |

**주행제어 판단 질문:** “Planner가 이동 가능한 후보 경로를 만들었는데 Collision Monitor가 소프트웨어 STOP을 요구한다면 어떤 동작을 성공이라고 말할 수 있는가?” 실제 장애물 회피 성공이 아님을 확인한다. SW 정지와 인증된 물리 E-Stop은 구별한다.

## 제출 확인표 및 실습 종료

```bash
cd "$HOME/axia_d07_student_lab"
EVIDENCE="$HOME/axia_d07_student_evidence"
git rev-parse HEAD
git diff -- block_B/day07/route_todo.py
ls -lh "$EVIDENCE"
```

제출: `source_sha.txt`, 수정한 `route_todo.py`, `d07_RED.log` 및 `red_rc.txt`, `d07_GREEN.log` 및 `green_rc.txt`, `route_diagram.md/png`, `route_comparison.md`, `unknown_case.md`, `evidence_scope.md`. 필요하면 `git diff`도 제출한다. **비공개 파일·접근 토큰·강사 정답은 제출하지 않는다.**

**종료:** 학생 터미널 **S**만 `exit`하여 닫는다. 강사의 ROS/Gazebo 실행 터미널은 학생이 종료하지 않는다. 새 H01 주행 시연 허가가 나오기 전에는 `/odom` 실제 이동과 `NavigateToPose` Goal 성공을 수업 성공 조건으로 채점하지 않는다.
