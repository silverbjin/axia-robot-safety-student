# AXIA DAY 3 — 실제 G07 MVP 시나리오 활용 가이드/원샷 L0 QA

- 작성일: 2026-11-26
- 범위: 공개 학생용 문서, 정적 증거 카드, 기존 Python replay 호출, Git SHA/Blob 검증.
- 절대 미실행: ROS 2 노드, Gazebo, 실제 Nav2 Moving Goal, Fault Injection, Owner WSL2 L3.

## 1. 실제 소스 및 사건 고정

| 원본 | PIN | 비고 |
|---|---|---|
| DAY 3 학생용 기본 소스 | `release/day02-dual-mvp-full-source-build-20261126` · `96be43164fab3f15025edd59279bcfd50b6232cd` | 성공/실패 런타임 두 벌 포함 |
| DAY 2 교육용 시나리오 실행기 | `feat/day02-g07-scenario-demo-20261126` · `f43df3132c8c1dac29f7c980274cd85bcdda02fc` | 정적 리플레이 코드 SHA 잠금 |
| Python Replay Git blob | `7c40f7a51b1ff6504be7bd4f16acbead185ebf55` | 실제 구현 그대로 재사용 |
| 보고서 발췌 JSON Git blob | `4a6212555ba58d93e06a165477ad1f973dc8992d` | 원본 rosbag 아님 |
| 성공 L2 Run | `44965035965` | 2/2 PASS; 성공 Student `f7edb2d126502eeeed58ae014adadc7a2096d41b` |
| 실패 L2 Run | `44914827138` | 0/2 FAIL; 실패 Student `a04f9a7da8d54bbd9f944d05388792cb706adf28` |
| Owner 사후 보고서 | `c2c4f66c532be2a41855239860b9a9f5d60c4586` | `PASS_SCOPED` + 원본 자동 HOLD 보존 |

## 2. 실제 수행한 로컬 검사

```bash
bash -n scripts/day03_g07_scenario_once.sh
bash scripts/day03_g07_scenario_once.sh --doctor
bash scripts/day03_g07_scenario_once.sh --run
python3 -m unittest discover -s tests -v
```

원본 출력 요약:

```text
DAY3_SCENARIO_DOCTOR_L0_PASS NO_NETWORK_NO_ROS_NO_GAZEBO_NO_GOAL
DAY3_SCENARIO_PIN=f43df3132c8c1dac29f7c980274cd85bcdda02fc
DAY3_SCENARIO_USAGE=--doctor|--success|--failed|--compare [--json-out NEW_PATH]
invalid_rc=2
Ran 7 tests in 0.025s
OK
```

`--run`은 명시적으로 **차단되는 음성 테스트**이며, 실제 ROS/Gazebo를 실행한 것이 아닙니다.

## 3. 공개 GitHub Actions 실제 검증

- GREEN Push Run: [#45842995298](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/45842995298), SHA `be107db511e2fefeda2e1a38a9a148925a4a3741`, **success**.
- 실행된 단계: 원본 전체 MVP Tree 무결성, 학생용 시나리오 Unit Test 7/7, 원본 시나리오 Python+JSON Blob SHA 검증, 원본 데이터에 대한 `--compare` 정적 리플레이, JSON 증거 등급 검증.

실제 CI 출력 발췌:

```text
DUAL_G07_SOURCE_CUSTODY_L0_PASS
test_default_stays_doctor ... ok
test_doctor_is_offline_and_never_runs_goal ... ok
test_guide_has_sources_safety_and_unit_mapping ... ok
test_no_moving_goal_mode ... ok
test_non_git_cache_fails_closed_without_network ... ok
test_shell_syntax ... ok
test_source_is_sha_and_blob_pinned ... ok
Ran 7 tests in 0.014s
OK
DAY3_SCENARIO_UPSTREAM_PIN_OK=f43df3132c8c1dac29f7c980274cd85bcdda02fc case=compare
DAY3_SCENARIO_SCOPE=HISTORIC_EVIDENCE_REPLAY_L0_ONLY NEW_L2_L3=NOT_RUN
HISTORICAL_EVIDENCE_REPLAY_NO_ROS_NO_GOAL
NEW_L2_L3_NOT_RUN  CERTIFIED_ESTOP=false
DAY3_PINNED_REPLAY_L0_PASS new_l2_l3=NOT_RUN
```

## 4. 비공개 정보 유출과 시연 정확성 점검

- 공개 학생용 가이드는 이미 공개된 SHA, CI Run URL, 정적 측정값만 참조합니다.
- 원본 Owner rosbag·TAR/ZIP·개인 경로·강사 정답·hidden tests를 포함하지 않습니다.
- `/scan`과 `/safety/scan`, RMW source/receive, Observer callback, Guard 내부 CM age를 독립 경계로 설명했습니다.
- S01~S06과 F01~F04의 수치를 **서로 다른 실행**임을 표시하고 공통 사건 시간축을 만들지 않았습니다.
- 인증된 E-Stop을 주장하지 않습니다.
- 강사 실제 Gazebo NO_GOAL 및 Owner Moving 데모는 **기존 실행기만** 안내합니다. 새 시연 실행기로 발행/조작하지 않습니다.

## 5. 검증 수준 / 미검증 / Git 상태

| 항목 | 결과 |
|---|---|
| 문서·Script 정적 분석 | PASS |
| Python L0 7개 검사 | PASS |
| GitHub 공개 CI: 원본 PIN과 역사적 비교 카드 | PASS |
| 학생 WSL2 직접 원샷 실행 | NOT_RUN |
| 신규 ROS 2 Jazzy colcon L1 빌드 | NOT_RUN |
| 신규 실제 Gazebo L2 | NOT_RUN |
| 신규 Owner WSL2 L3 | NOT_RUN |
| 정식 하드웨어 안전 인증 | NOT_CLAIMED |

학생용 작업 브랜치: `feat/day03-g07-scenario-use-guide-20261126`. `main` 병합: **NOT_MERGED** (별도 승인 필요). 이번 작업은 공개 CI 문서/코드 검증이지 실제 로봇 인수의 재검증이 아닙니다.
