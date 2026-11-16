# D07 학생용 데모 가이드 — 사람 회피 구조와 주행제어 증거 읽기

> 수업: 2026-11-17(화) 19:00~22:00 · 이론 60분 + 실습 120분 · **읽기 전용 데모 및 Python TDD**  
> 수업용 PPT: AXIA D07 V3 학생용 24장(강사가 제공). 단계별 전체 절차는 [D07 3시간 가이드](D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md)를 따른다.  
> **안전 범위:** 학생은 ROS Goal, 최종 속도 `/cmd_vel`, Gazebo 물리 모델을 직접 조작하지 않는다. H01 실제 회피 주행 성공이 아님.

## 학습 목표

1. **사람을 동적 장애물로 처리하는 회피제어 구조 이해** — `LaserScan → ObstacleLayer/InflationLayer → Costmap → Planner`가 무엇을 입출력하는지 설명한다.
2. **사람 회피 로직 및 주행제어 실습** — 기록된 두 경로의 BLOCKED/CLEAR를 계산하고, Nav2 Planner·Controller·Collision Monitor·Base Guard의 책임과 **실제 주행의 필요 증거**를 구분한다.

## 데모를 보기 전에: 증거 수준을 먼저 구분

| 데모 | 입력과 시험 위치 | 검증된 사실 | 검증하지 않은 사실 |
|---|---|---|---|
| **L0** 학생 `routes.json` | 합성 2D 경로와 사람 proxy | 구현 전 RED, 구현 후 경로 판정 | 실제 ROS, 센서, 로봇 이동 |
| **L1** 공식 Nav2 | ROS 2 Jazzy, 합성 LaserScan, 실제 PlannerServer | Costmap lethal **0→101→0**, Path **58→74→58** | Gazebo 물리·Controller 이동 |
| **L2** D07-**H01** | Gazebo Harmonic 물리 장애물, 실제 Waffle LaserScan, 공식 Nav2 경로 질의 | 최신 검증된 경로 변화 **0.3659m**, 신규 lethal cell 92→0, Before/Intrusion/Restored Path 52점씩 | Controller 경로 추종, Contact·안전 TTL 인수 |
| **L3** Owner WSL2 GUI | WSLg의 Gazebo 3D·Entity Tree / RViz2 실제 화면 | 사용자 육안 + 무결성 검증 XWD에서 **화면 복원 확인** | 자동 Owner L3 수락은 **VISUAL_HOLD**, 실제 주행 인수 아님 |

**현재 강사 시연 기준선(2026-11-16):** `D07_H01_GUI_SCENE_RESTORED_OWNER_20261116`. 실제 공개 Gazebo L2 [#43866354976](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43866354976)는 성공했고, Owner `d07-h01-owner-SFvdvtvH`에서는 3D 월드·로봇과 RViz2 경로가 화면에서 확인되었다. **그러나 자동 Owner L3는 `D07_H01_OWNER_GUI_VISUAL_HOLD`, 전체 AXIA는 `AXIA_MVP_DEMO_ACCEPTED=HOLD`이다.** `NavigateToPose` 이동 Goal 및 실제 회피 주행은 수행하지 않았다. 과거 `POST_RESTORE_COSTMAP_DRIFT` 실패는 아래에서 학습용 사례로만 보존한다.

## 1단계 — 학생 터미널 S: 합성 경로만 관찰 (5분)

[학생 실습 가이드](D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md)의 환경 준비가 끝난 뒤 새 터미널을 추가하지 않고 같은 S에서 확인한다.

```bash
cd "$HOME/axia_d07_student_lab"
.venv/bin/python - <<'PY'
import json
from pathlib import Path
f=Path("block_B/day07/fixtures/routes.json")
d=json.loads(f.read_text(encoding="utf-8"))
print("D07_DEMO_SOURCE=",d["source"])
print("D07_DEMO_PERSON_XY=",d["person_xy"])
print("D07_DEMO_BUFFER_M=",d["buffer_radius_m"])
print("D07_DEMO_BEFORE_POINTS=",len(d["path_before"]))
print("D07_DEMO_DETOUR_POINTS=",len(d["path_detour"]))
PY
```

**예상(합성 파일에서 계산):** proxy 좌표 `[0.8, 0]`, 반경 `0.35`m, before 7개 점, detour 7개 점. 전방 직선은 원의 중심을 지나므로 최소 거리 0m이고, 우회 후보는 약 0.515m이다. **반경 0.35m와 실제 Costmap inflation_radius를 같은 값으로 생각하지 않는다.**

학생은 종이에 두 경로를 겹쳐 그린 뒤 물체 중심에서 경로 **선분**까지 거리를 표시한다. 경로점만 검사하면 중간 충돌을 놓칠 수 있다.

## 2단계 — 공식 Nav2 L1: 강사가 과거 CI 증거를 화면에 표시 (5~7분)

**원본 공개 CI:** https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42661513782

강사 화면에서 로그의 `D07_REAL_NAV2_STAGE`와 `D07_NAV2_L1_VERDICT`를 찾는다. 학생은 **브라우저로 읽기만** 하며 기존 L1을 재실행할 필요가 없다.

| 순서 | 실제 공식 Nav2 관측 | 설명 |
|---|---|---|
| `clear_before` | lethal 0, path 58점 | 사람 proxy 없음 |
| `person_blocking` | lethal 101, path 74점 | Scan 물체 marking, 우회 계획 |
| `person_cleared` | lethal 0, path 58점 | clearing 뒤 경로 후보 복원 |

실제 토픽·액션 관계:

```text
합성 LaserScan /axia/d07/test/scan
  → ObstacleLayer / InflationLayer
  → /global_costmap/costmap
  → 공식 PlannerServer (/compute_path_to_pose: ComputePathToPose)
  → 경로(Path) 비교
```

**ComputePathToPose는 계획 질의, NavigateToPose는 이동 요청**이다. L1에서는 `actual_robot_cmd_publishers=0`이었다. `/odom` 주행 궤적도 없으므로 경로 변경은 실제 이동의 증거가 아니다.

## 3단계 — 실제 H01 공식 경로 시연 및 과거 실패 비교 (5~7분)

**현재 공개 L2:** https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43866354976

강사가 준비한 화면 또는 검증된 증거에서 Gazebo 물리 원통 장애물의 Before → Intrusion → Restored 시퀀스를 본다. 실제 Waffle `/scan` → Nav2 Costmap → 공식 `ComputePathToPose` → RViz2 Path(읽기 전용) 흐름을 확인한다.

- 공식 Path는 세 단계에서 각각 **52 poses**이고, RViz DDS subscriber 수는 매 단계 **1**이었다.
- Intrusion에서 신규 lethal cells **92개**, Restored에서 신규 lethal cells **0개**, 경로 차이 `path_delta_m=0.3659`로 기록되었다.
- Owner 화면에서 Gazebo 3D 월드·로봇·Entity Tree와 RViz2 Costmap/Path가 확인되었다. 자동 Owner L3는 정책상 `VISUAL_HOLD`를 유지한다.
- **무주행:** `robot_moved=false`, `goal_sent=false`. 경로 변화만으로 Controller 주행·안전 정지·접촉 회피 성공을 증명하지 않는다.

**과거 실패 사례(현재 최신 판정 아님):** 공개 CI https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43581522872 에서는 `POST_RESTORE_COSTMAP_DRIFT`로 차단되었고 당시 경로 변화 약 0.5732m, Costmap lethal 개수 41→121→41만 복원되었다. 최초 실패와 이후 복원 성공을 비교하는 교육용 증거다.

```text
실제 Gazebo 장애물 → Waffle LaserScan → 공식 Costmap → ComputePathToPose
                                       ↓
                               RViz2 계획 경로 표시
                 (Planner 경로 질의: 실제 주행 명령 아님)

 Controller → /cmd_vel → /odom → Contact / 안전 TTL
                 (H01에서 증명하지 않은 별도 계층)
```

## 4단계 — 학생이 수행하는 주행제어 판단 (5분)

아래의 각 상황에 대해 **증거가 있으면 O, 없으면 X**, 다음 담당 노드를 적는다.

| 관측 | 계획 변경 | 실제 경로 추종 | 다음 확인해야 할 증거 |
|---|---|---|---|
| 합성 `path_before`와 `path_detour` 비교 | 학생 판정 후보 | X | Controller 입력/출력 |
| 공식 L1 `58→74→58` | O | X | `NavigateToPose`, 실제 `/odom` |
| 최신 물리 H01 경로 편차 0.3659m | O | X | Controller, 최종 `/cmd_vel`, `/odom`, Contact |
| 실제 근접 보호 정지 | 계획과 별개 | 성공 주행 아님 | Collision Monitor/Guard 안전 상태 |

**토의 질문:** “Nav2 Planner에서 경로가 바뀌었는데 로봇의 `/odom`이 변하지 않았다면, 어떤 주행제어 증거가 빠진 것인가?” **답은 학생이 증거표를 통해 설명한다.**

## 데모 종료와 수업 연계

- 학생은 하나의 터미널 **S**만 사용한다. 강사의 ROS 2·Gazebo 프로세스에는 접근하지 않는다.
- 학생 코드 구현은 [실습 가이드](D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md)의 RED→GREEN으로 이어진다.
- 제출할 것: 두 경로 그림, `BLOCKED/CLEAR/UNKNOWN` 분석, L1·H01의 *증명된 것/미검증 항목* 비교표.
- **학생 터미널 S 종료:** 실습 파일·로그를 보존한 뒤 `exit`. 강사 측 시험을 종료하지 않는다.

**인수 경계:** 학생 데모는 L0 판정과 기존 L1/L2 원본 증거 해석 교육이다. 실제 Controller 주행과 인증된 HW E-Stop의 시연·검증이 아니다.
