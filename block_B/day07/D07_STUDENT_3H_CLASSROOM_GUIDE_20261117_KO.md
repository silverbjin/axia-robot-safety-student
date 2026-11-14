# AXIA Block B D07 — 학생 3시간 실습 가이드

- **2026-11-17(화) 19:00–22:00**, **이론 60분** + **실습 120분**
- 주제: **정지와 경로 재계획은 무엇이 다른가?**
- student 독립 저장소: https://github.com/silverbjin/axia-robot-safety-student
- 실습 위치: block_B/day07/
- 범위: Python 합성 경로 평가. 실제 /cmd_vel 발행·주행 Goal·Gazebo 물리 검증 없음.

## 1. 학습 목표와 종료 증거

**LO1 — Costmap/Planner의 증거 읽기.** LaserScan→ObstacleLayer(mark/clear)→InflationLayer→Costmap→PlannerServer/Navfn 경로를 설명하고, 합성 두 경로와 공식 ROS L1 세 단계 결과를 비교한다. 제출: before/detour 2D 그림, 장애물 buffer 거리 판단표, 공식 L1 수치 의미.

**LO2 — 정지 vs 재계획 구분.** Planner(경로 계산), Controller(주행 명령), Collision Monitor(근접 감속/정지), Supervisor/Guard(보호 체인)를 구분한다. route_obstacle_status()와 assess_replan()를 RED→GREEN으로 작성한다. 제출: TODO 구현, 실제 RED/GREEN 로그와 반환코드, UNKNOWN 독립 반례, 미검증 내역.

**중요:** ComputePathToPose는 경로 **계산 액션 요청**이며 NavigateToPose는 이동 액션이다. 공식 Planner L1에서 계산 요청 세 번은 있었지만 로봇 이동 Goal과 /cmd_vel publisher는 없었다. 명령 0은 odom 실제 정지 또는 인증된 E-Stop 근거가 아니다.

## 2. 시간표 (총 180분)

| 시간 | 구간 | 산출 |
|---|---|---|
| 19:00–20:00 | 이론 60분 | 정지/우회 비교, Costmap/Planner Action, 공식 ROS L1 해설 |
| 20:00–20:10 | L1 환경 | 저장소·SHA·Python/pytest 기록 |
| 20:10–20:25 | L2 fixture | 원본 경로/회피 후보와 점-선분 거리 스케치 |
| 20:25–20:45 | L3 RED | 최초 NotImplementedError 및 RED_RC |
| 20:45–21:10 | L4 GREEN | TODO 2함수만 완성, GREEN_RC |
| 21:10–21:25 | L5 반례 | None, NaN, age>0.5, invalid→UNKNOWN |
| 21:25–21:40 | L6 강사 L1 | 과거 공식 Nav2 Costmap/Planner 증거 해설 |
| 21:40–21:50 | L7 리뷰 | Planner/Controller/CM/Guard 책임 구분 |
| 21:50–22:00 | L8 제출 | 6종 증거+30초 해설 |

## 3. 학생 터미널 S — 수업 시작 1회

D04–D06 폴더를 초기화하거나 덮어쓰지 않는다. **이번 새 자료는 Draft PR #20의 브랜치에만 존재한다.** Owner main 병합 승인 전에는 main에서 받지 않는다. 이미 만든 개인 D07 코드가 있으면 새로 초기화하지 않는다.

    (
      set -Eeuo pipefail
      ROOT="$HOME/axia_d07_student_lab"
      BRANCH="docs/d07-3h-classroom-20261114"
      if [[ ! -e "$ROOT" ]]; then
        git clone --single-branch --branch "$BRANCH" \
          https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
      fi
      cd "$ROOT"
      if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
        echo "D07_WRONG_BRANCH: existing work preserved"; exit 2
      fi
      test -f block_B/day07/route_todo.py
      test -f block_B/day07/D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md
      mkdir -p "$HOME/axia_d07_student_evidence"
      echo "D07_STUDENT_SOURCE_SHA=$(git rev-parse HEAD)" \
        | tee "$HOME/axia_d07_student_evidence/source_sha.txt"
      python3 --version
      if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
      .venv/bin/python -m pip install -q "pytest==8.3.5"
      .venv/bin/python -m compileall -q block_B/day07
    )

**예상(현장 실행 보증 아님):** Git SHA 40자리·Python 3.12.x·컴파일 정상. 오류가 나면 네트워크/가상환경/잘못된 브랜치부터 확인한다. 별도 Gazebo나 ROS는 학생 터미널 S에서 실행하지 않는다.

## 4. L2 — 합성 fixture 분석

파일: block_B/day07/fixtures/routes.json.

- 사람을 의미하는 **합성** proxy=(0.8,0.0)m, **buffer_radius_m=0.35**m.
- path_before: 직진 경로, 기대 판정 **BLOCKED**.
- path_detour: 외곽 우회 후보 경로, 기대 판정 **CLEAR**.
- 학생 판정 대상은 점 하나의 거리만이 아니라 **모든 경로 선분에서 proxy 점까지의 최단 거리**다. 점 사이에 장애물이 끼면 단순 점 비교는 위험하다.
- 두 경로를 비교해 REPLAN_EVIDENCED로 판단하더라도, 외부에서 주어진 합성 경로 비교일 뿐 로봇이 이동했거나 공식 Planner를 실행했다는 증거는 아니다.

학생은 좌표축, proxy buffer 원, 두 경로를 겹쳐 그리고 장애물과 가장 가까운 선분을 표시한다.

## 5. L3 — RED (20분)

먼저 fixture만 확인한다.

    cd "$HOME/axia_d07_student_lab"
    export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
    .venv/bin/python -m pytest -q \
      block_B/day07/tests/test_d07_public.py::test_fixture_schema

**기존 공개 학생 source의 예상:** fixture **1 passed**. 그 후 전체 테스트:

    EVIDENCE="$HOME/axia_d07_student_evidence"
    if (
      set -o pipefail
      PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
        block_B/day07/tests/test_d07_public.py | tee "$EVIDENCE/d07_RED.log"
    ); then
      RC=0
    else
      RC=$?
    fi
    echo "D07_STUDENT_RED_RC=$RC" | tee "$EVIDENCE/red_rc.txt"

아직 두 TODO 함수를 구현하지 않았다면 보통 **1 passed, 3 failed**, NotImplementedError, RC≠0이다. 첫 예외를 찾고 왜 발생했는지 적는다. 학생이 이미 구현했으면 실패가 안 날 수 있으므로 임의 reset 금지. 공개 테스트를 바꾸거나 지워 GREEN처럼 꾸미지 않는다.

## 6. L4 — GREEN (25분)

**변경 허용은 block_B/day07/route_todo.py의 함수 두 개뿐.**

1. route_obstacle_status(path, person_xy, valid, age_s, max_age_s=0.5, buffer_radius_m=0.35): 2D 좌표/시간/경로 유효성을 검사한 뒤 전체 선분 최소거리로 CLEAR/BLOCKED/UNKNOWN 판정.
2. assess_replan(path_before, path_after, person_xy, ...): before BLOCKED + after CLEAR에 한해 REPLAN_EVIDENCED. robot_moved=False, collision_free_verified=False, safety_certified=False 유지.

새로운 A*/Planner/Controller/ROS publisher를 구현하지 않는다. 실제 속도 명령이나 Nav2 Goal을 보내지 않는다.

    cd "$HOME/axia_d07_student_lab"
    EVIDENCE="$HOME/axia_d07_student_evidence"
    if (
      set -o pipefail
      PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q \
        block_B/day07/tests/test_d07_public.py | tee "$EVIDENCE/d07_GREEN.log"
    ); then
      RC=0
    else
      RC=$?
    fi
    echo "D07_STUDENT_GREEN_RC=$RC" | tee "$EVIDENCE/green_rc.txt"
    test "$RC" -eq 0

학생이 정상 구현했다면 **4 passed** 예상. 이는 Python 합성 데이터 **L0** 통과일 뿐이다. tee 반환코드만으로 pytest 성공을 판단하지 않도록 set -o pipefail을 사용한다.

## 7. L5 — UNKNOWN 독립 반례 (15분)

| 입력 | 교육용 판정 |
|---|---|
| person_xy=None / NaN | UNKNOWN |
| age_s=0.51, max_age_s=0.5 | UNKNOWN |
| age_s=0.50 (다른 입력 유효) | 유효 경계, 경로에 따라 결과 |
| 비어 있거나 잘못된 path | UNKNOWN |
| before와 after 모두 BLOCKED | REPLAN_EVIDENCED 금지 |

합성 함수의 max_age_s=0.5는 실제 센서·CM·Guard의 안전 TTL을 검증한 것이 아니다. 독립 반례 1개에서 기대값·실제 출력·위험한 이유를 설명한다. UNKNOWN≠CLEAR.

## 8. L6 — 공식 Nav2 ROS L1 강사 시연 15분

강사 기본 모드는 **이미 인수한 원본 증거** 해설이며 학생은 읽기만 한다.

- 기존 공개 Actions: https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42661513782
- 강사 WSL2 공식 L1: 2026-11-10 실제 인수, 새 수업 실측으로 주장하지 않음.
- **기존 L1 실제 출력:** clear_before lethal cells **0**/path **58**, person_blocking lethal **101**/path **74**, person_cleared lethal **0**/path **58**.
- 공식 Nav2 PlannerServer+Costmap이 synthetic LaserScan 장애물 proxy를 처리한 결과이며, actual_robot_cmd_publishers=0.
- **NOT_RUN:** NavigateToPose 실제 주행, Gazebo 물리 contact, /odom 실제 이동, D04 YOLO→Nav2 실시간 결합, 인증된 HW E-Stop.

강사 **터미널 A**는 기존 공식 L1 원샷을 선택적으로 구동할 때만 사용한다. **B**는 A의 실제 ROS_DOMAIN_ID 확인 후 읽기 전용 모니터, **학생 S**는 Python 실습. 현장 L1 실패시 동일 증상을 반복 재시도하지 않고 기존 원본으로 설명하고 최초 문제/타이밍 위반을 기록해 공개 CI 회귀로 인계한다. D06 새 Gazebo+RViz2 동시 시연은 WSL2 미인수이며 D07 PASS로 승격하지 않는다.

## 9. L7 리뷰 (10분)

| 계층 | 핵심 책임 |
|---|---|
| PlannerServer | 현재 비용 지도에 맞는 경로 계산 |
| ControllerServer | 경로 추종 속도 계산 (D07 L1은 미실행) |
| Collision Monitor | 가까운 장애물에 대한 소프트웨어 감속/정지 (별도 D06 L1) |
| Safety Supervisor / Base Guard | 안전 상태와 최종 명령 전달 경계 |

SW 정지 출력, 물리 /odom 정지, 인증 Hardware E-Stop은 서로 다르다. ROS 계획 결과가 있다고 로봇에게 자동 재출발 권한이 생기지 않는다.

## 10. L8 제출 및 100점 평가 (10분)

student 제출 폴더: ~/axia_d07_student_evidence/. 개인 route_todo.py, source_sha.txt, d07_RED.log+red_rc.txt, d07_GREEN.log+green_rc.txt, route_diagram.md/png, route_comparison.md, unknown_case.md, evidence_scope.md를 포함한다. 비공개 소스·토큰은 제출하지 않는다.

| 제출·평가 증거 | 점수 |
|---|---:|
| 두 경로 그림/선분거리 근거 | 20 |
| TODO 두 함수 구현(read-only) | 20 |
| 실제 RED/GREEN 로그·종료코드 | 20 |
| UNKNOWN 독립 반례 | 15 |
| 공식 L1 증거+4계층 역할표 | 15 |
| SHA·미검증·30초 해설 | 10 |
| **합계** | **100** |

**30초 Exit Ticket:** “Planner가 path 74점을 계산했으면 실제 로봇이 사람을 피해 갔다고 말할 수 있는가? ComputePathToPose와 NavigateToPose는 무엇이 다르고, 왜 Collision Monitor가 여전히 필요한가?”

수업 종료 시 학생 S만 닫는다. 강사의 ROS/WSL2/Gazebo 프로세스는 변경하거나 강제 종료하지 않는다. 이 가이드를 통해 새 ROS/Gazebo 실행 성공을 주장하지 않는다.

---

## 11. 두 원래 주제와 실습 경계

**1. 사람을 동적 장애물로 처리하는 회피제어 구조 이해**: 공식 Nav2의 LaserScan→Costmap→Planner와 시간에 따른 장애물 등장·제거를 설명한다.

**2. 사람 회피 로직 및 주행제어 실습**: 합성 경로의 BLOCKED/CLEAR 판정과 제어 계층의 의사결정 워크시트를 작성한다.

**주행제어 실습의 검증 경계**: 본 수업의 필수 코드는 읽기 전용 경로 분석이다. **실제 주행제어는 미실행**이다. 실제 ControllerServer, 주행 Goal, /cmd_vel, /odom, contact를 이용한 Gazebo 물리 회피는 별도 인수 전까지 NOT_RUN이다. G07 감속·정지 시연은 회피 주행 성공을 증명하지 않는다.
## 12. 전체 시스템 아키텍처 — 실제 이동 시스템의 개념도

다음은 공식 Nav2의 계획/추종과 AXIA 보호 체인을 설명하기 위한 **개념도**다. 이번 D07 L1에서 ControllerServer와 BT Navigator를 모두 기동한 것이 아니다.

~~~mermaid
flowchart TD
 H[사람/장애물] --> S[LiDAR /scan]
 S --> G[Global Costmap - ObstacleLayer + InflationLayer]
 G --> P[PlannerServer - NavfnPlanner]
 N[BT Navigator - NavigateToPose] -->|ComputePathToPose| P
 P -->|Path 계획 결과| N
 S --> L[Local Costmap]
 L --> C[ControllerServer - FollowPath]
 N -->|경로 추종 요청| C
 C --> SUP[AXIA Safety Supervisor]
 SUP --> CM[공식 Collision Monitor]
 S --> CM
 CM -->|/cmd_vel_pre_guard| GUARD[AXIA Base Guard]
 GUARD -->|/cmd_vel| BASE[Robot Base]
 BASE --> O[/odom]
~~~

PlannerServer는 경로를 계획하지만 속도 명령을 직접 구동하지 않는다. ControllerServer가 경로를 추종할 때 속도 명령을 계산하고, Collision Monitor는 근접 물체를 독립적으로 검사해 감속·소프트웨어 정지할 수 있다. 기존 G07의 /cmd_vel_pre_guard는 CM 이후/Guard 이전 관측 토픽이다. D04 YOLO 및 D05 RGB-D 실제 데이터는 아래 D07 L1 합성 LaserScan과 연결되지 않았다.

## 13. 실제 D07 ROS L1 데이터 파이프라인 — 이미 검증된 격리 경로

~~~mermaid
flowchart LR
 SC[_scan synthetic LaserScan] -->|/axia/d07/test/scan| OL[Official ObstacleLayer + InflationLayer]
 OL -->|/global_costmap/costmap| GRID[_run_stage lethal grid count]
 OL --> PL[Official PlannerServer / NavfnPlanner]
 REQ[_request_path] -->|/compute_path_to_pose Action| PL
 PL -->|nav_msgs/Path result| ROUTE[Path points and clearance]
 GRID --> V[verdict.json]
 ROUTE --> V
~~~

**실제 실행한 순서:** 정적 TF map→base_footprint → synthetic LaserScan → ObstacleLayer marking/clearing → InflationLayer → /global_costmap/costmap 실제 수신 → /compute_path_to_pose 계획 Action 질의 → nav_msgs/Path 결과 검증 → verdict.json/SHA256SUMS 저장. 이 격리 실험에서는 최종 /cmd_vel publisher 수 0개를 확인했다.

**동적 장애물의 시간 변화:** 이 시험은 실제 사람이 걸어 다니는 좌표 추적이 아니다. 같은 위치에 proxy가 **없음→나타남→사라짐**으로 시간 변화하는 시나리오이다.

| 시간/단계 | 합성 장애물 | 기존 공식 ROS L1 lethal cells | 기존 공식 ROS L1 Path 점 수 |
|---|---|---:|---:|
| t0 clear_before | 없음 | 0 | 58 |
| t1 person_blocking | 전방 0.8m proxy | 101 | 74 |
| t2 person_cleared | 제거 | 0 | 58 |

위 0→101→0, 58→74→58은 이전 공개 Actions #42661513782 및 2026-11-10 강사 WSL2 L1의 실측 사례이며 이번 문서 수정의 새로운 ROS PASS가 아니다.
