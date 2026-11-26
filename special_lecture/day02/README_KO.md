# AXIA DAY 02 — 완성된 G07 안전 MVP · 학생용 릴리스

**추가 시나리오 활용 자료:** [G07 S01~S06 및 실패 심화 라이브/리플레이 운영 가이드](scenarios/SCENARIO_OPERATION_GUIDE_KO.md), [읽기 전용 실제 원본 보고서 수치 리플레이](scripts/g07_scenario_replay.py), [학생 장면별 기록지](evidence_templates/SCENARIO_STUDENT_OBSERVATION_KO.md). 본 프로그램은 ROS/Gazebo/Goal을 새로 실행하지 않습니다.

**DAY02 v4 듀얼 MVP:** 성공본은 이 릴리스이며, 실증 0/2 실패본은 [별도 학생 브랜치](https://github.com/silverbjin/axia-robot-safety-student/tree/release/day02-g07-failed-l2-20261126)에 있습니다. [v4 기획](workbook/DUAL_MVP_WORKBOOK_PLAN_v4_KO.md), [Master Prompt](workbook/MASTER_PROMPT_DAY02_DUAL_MVP_KO.txt)를 참조하고 `bash special_lecture/day02/scripts/prepare_dual_mvp.sh "$HOME/axia-day02-failed"`로 별도 Worktree를 만드십시오. **Goal/Gazebo 자동 실행 없음.**

**실행 가능한 완성형 G07 런타임을 그대로 보존하고 학생은 구조·데이터 파이프라인·검증 증거를 탐색합니다.** 본 릴리스의 실습 검사기는 **오프라인 L0**, ROS·Gazebo·Goal을 실행하지 않습니다.

## 고정된 검증 이력

| 구분 | 검증 수준·정확한 출처 |
|---|---|
| 기존 학생 MVP 소스 | `f7edb2d126502eeeed58ae014adadc7a2096d41b` (완성 코드, 공개 브랜치) |
| 실제 공개 Native Gazebo Moving | [Run 44965035965](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44965035965), 정확 Public `64ba0161e66126b4743b4b12a859f4a5349ae58a`, **2/2 PASS** |
| 강사 WSL2 사후 원본 검수 | [11월 22일 RAW 보고서](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/c2c4f66c532be2a41855239860b9a9f5d60c4586/docs/operations/AXIA_G07_OWNER_WSL2_L3_POSTRUN_RAW_EVIDENCE_REVIEW_20261122_KO.md), **L3 PASS_SCOPED** |
| 자동 원본 판정 | `HOLD_RAW_REVIEW_AND_VISUAL_PENDING` **그대로 보존**; 이는 별도 수동 사후 수치·종료 검수와 구별 |

## Ubuntu 24.04 / WSL2에서 한 번에 실행할 오프라인 L0

```bash
cd ~
git clone --single-branch --branch release/day02-g07-accepted-20261126 \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-day02-mvp
cd ~/axia-day02-mvp
git rev-parse HEAD
python3 special_lecture/day02/scripts/verify_release.py \
  --out /tmp/axia-day02-release/release_result.json
python3 -m unittest discover -s special_lecture/day02/tests -p 'test_*.py' -v
```

**예상 결과:** `L0_RELEASE_CONTRACT_PASS` 및 5 tests OK. 런타임 8개 대표 소스 Git blob SHA가 2026-11-22 성공 소스와 동일함을 확인합니다. **실제 ROS 2·Gazebo 실행 성공을 새로 증명하지 않습니다.** `git rev-parse HEAD`는 문서·검증 코드가 추가된 릴리스 커밋이므로 고정된 원본 소스 SHA와 다릅니다.

## 실제 제어 데이터 경로 (교육용 논리 구조)

```mermaid
flowchart TD
 A[Gazebo Waffle /scan] --> B[Fault Injector /safety/scan]
 A --> C[Official Nav2 + Velocity Smoother]
 C --> D[/cmd_vel_smoothed]
 D --> E[Safety Supervisor]
 B --> E
 B --> F[Official Collision Monitor]
 E --> G[/cmd_vel_supervised]
 G --> F
 F --> H[/cmd_vel_pre_guard]
 H --> I[Base Guard]
 I --> J[/cmd_vel to Gazebo]
 J --> K[/odom: 실제 이동 확인]
 K --> L[Verifier / evidence]
```

- `block_B/day07/h01_runtime/ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py`: Nav2와 자체 패키지 연결
- `.../axia_safety_supervisor/p2_supervisor_node.py`: FSM, Goal, Command Gate
- `.../axia_safety_supervisor/p2_base_guard_policy.py`: CM TTL 및 최종 명령 보호
- `block_B/day07/h01_runtime/tools/p2_g07_ci_moving_goal.py`: 실제 Goal/STOP/odom 검증 경로
- `block_B/day07/h01_runtime/tools/p2_g07_ordered_shutdown.py`: Navigation 및 Localization ACK
- `.../axia_safety_supervisor/p2_shutdown_context.py`: 종료 Context 예외의 정확한 경계

## 180분 실습 흐름

기존 결과 관찰(15) → Git·SHA·패키지 확인(20) → 아키텍처·토픽 추적(25) → AI 코드 분석(20) → 휴식(10) → 실제 함수·Goal·종료 관계(25) → 읽기 전용 L0·반례 점검(25) → 리뷰·보고서(25) → 결과 발표(15) = 180분.

**학생 성취물:** 실제 코드 구조도, 토픽-함수 연결표, AI 응답 검토표, 해시 검증 출력, 개인 Git SHA. 임의로 운영 Safety 코드·TTL·ROS Launch를 변경하지 않습니다. 실습 보고서는 `evidence_templates/STUDENT_EVIDENCE_TEMPLATE_KO.md`를 사용합니다.

## 안전·배포 범위

소프트웨어 정지는 **인증된 하드웨어 E-Stop이 아닙니다**. 장기 반복 안정성, FastDDS/RMW 지연 근본원인 및 시각 화면 내용의 독립 검증은 CLAIM하지 않습니다. 강사용 비공개 정답·숨김 테스트·WSL2 raw TAR/ZIP·rosbag을 이 브랜치에 게시하지 않습니다. `main` 통합은 별도 사용자 승인 이후에만 수행합니다.
