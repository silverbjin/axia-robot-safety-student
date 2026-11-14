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
| **L2** D07-**H01** | Gazebo Harmonic 물리 장애물, 실제 Waffle LaserScan, 공식 Nav2 경로 질의 | 장애물 침입에 따른 **계획 경로 변경 약 0.573m** | Controller가 경로를 실제 추종한 결과, Contact·TTL 인수 |
| **L3** Owner WSL2 | 강사 PC 실제 통합 주행 | **NOT_RUN** (H01 범위) | H01 최종 인수 완료 |

H01 최신 실제 물리 경로 시험은 **전체 인수 BLOCKED**이다. Costmap lethal *개수* `41→121→41`만 복원되었으며, 공간 비용 차이와 최초 `POST_RESTORE_COSTMAP_DRIFT` 차단이 남았다. **H01 NavigateToPose 실제 이동 Goal은 NOT_RUN**이다.

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

## 3단계 — 실제 H01 물리 경로 증거 분석 (5~7분)

**원본 공개 CI:** https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43581522872

강사가 해당 실행의 실제 로그에서 `D07_H01`, `ROUTE_CANDIDATE_NOT_MOTION`, `FIRST_DRIFT_BOUNDARY` 또는 `POST_RESTORE_COSTMAP_DRIFT`를 검색해 보여 준다.

- Gazebo Harmonic의 실제 충돌체를 정지 상태에서 침입시키고 Waffle LaserScan으로 관측했다.
- 기존 공식 Nav2 경로와 침입 후 경로의 편차는 **약 0.5732m**였다.
- 경로 최소 이격 약 **0.55m**는 *계획 경로* 측정이며 실제 로봇 주행 이격이 아니다.
- 복원 단계의 lethal 개수 `41→121→41`은 전체 Costmap 복원과 다르다. 비용 값에 설명되지 않은 **323개 셀**이 남은 것으로 분류됐다.
- **H01 상태: BLOCKED / 실제 NavigateToPose 주행 NOT_RUN / Contact Ground Truth 미검증 / 안전 TTL 미검증.** 시연 성공으로 발표하지 않는다.

```text
Gazebo 물리 장애물 → 실제 /scan → 실제 Costmap → Nav2 Planner Path
                      [실제로 증명된 단계]
                                             ×
         Controller → Guard /cmd_vel → /odom → Goal SUCCEEDED
                      [H01에서 아직 증명하지 못한 단계]
```

## 4단계 — 학생이 수행하는 주행제어 판단 (5분)

아래의 각 상황에 대해 **증거가 있으면 O, 없으면 X**, 다음 담당 노드를 적는다.

| 관측 | 계획 변경 | 실제 경로 추종 | 다음 확인해야 할 증거 |
|---|---|---|---|
| 합성 `path_before`와 `path_detour` 비교 | 학생 판정 후보 | X | Controller 입력/출력 |
| 공식 L1 `58→74→58` | O | X | `NavigateToPose`, 실제 `/odom` |
| 물리 H01 경로 편차 0.5732m | O | X | Controller, 최종 `/cmd_vel`, `/odom`, Contact |
| 실제 근접 보호 정지 | 계획과 별개 | 성공 주행 아님 | Collision Monitor/Guard 안전 상태 |

**토의 질문:** “Nav2 Planner에서 경로가 바뀌었는데 로봇의 `/odom`이 변하지 않았다면, 어떤 주행제어 증거가 빠진 것인가?” **답은 학생이 증거표를 통해 설명한다.**

## 데모 종료와 수업 연계

- 학생은 하나의 터미널 **S**만 사용한다. 강사의 ROS 2·Gazebo 프로세스에는 접근하지 않는다.
- 학생 코드 구현은 [실습 가이드](D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md)의 RED→GREEN으로 이어진다.
- 제출할 것: 두 경로 그림, `BLOCKED/CLEAR/UNKNOWN` 분석, L1·H01의 *증명된 것/미검증 항목* 비교표.
- **학생 터미널 S 종료:** 실습 파일·로그를 보존한 뒤 `exit`. 강사 측 시험을 종료하지 않는다.

**인수 경계:** 학생 데모는 L0 판정과 기존 L1/L2 원본 증거 해석 교육이다. 실제 Controller 주행과 인증된 HW E-Stop의 시연·검증이 아니다.
