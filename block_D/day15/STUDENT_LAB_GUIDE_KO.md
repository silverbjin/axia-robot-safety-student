# AXIA Block D D15 — G07 MVP 증거 분석·최종 발표 실습

**수업:** 2026-11-27(금) 19:00–22:00 / 3시간. **PPTX 제작 제외.**  
**범위:** 이미 인수된 `AXIA-G07-T04-DEMO-BASELINE-20261120-jrCIgoGl`의 공개 파생 수치 *읽기·분석·Replay·평가*. **새 Goal/ROS/Gazebo/실제 Fault/WSL2를 수행하지 않습니다.**

## 1. 중요한 두 가지 사실

1. G07 `jrCIgoGl`은 강사 WSL2에서 실제 Moving Goal, CLEAR→SLOW→STOP, 동일 UUID 취소, odom 1.029446초 ZERO 유지 등의 **교육용 기능 및 수치**가 인수되었습니다. 공개 CI 실물 2-cycle [#44653465671](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44653465671)과 현장 원본 검수 보고서를 참조합니다.
2. 자동 원본 `task04_owner_verdict.json`의 판정은 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, `owner_moving_l3_accepted=false`, `visual_content_verified=false`입니다. 강사가 파생 자료를 교육용으로 인수한 것과 **정식 안전·원본 기계 인수는 구분**합니다. Software Stop은 인증된 E-Stop이 아닙니다.

**G09 P/N/U는 이 Owner 주행의 실제 사람 검출 결과가 아닙니다.** D13의 합성 시간 인덱스 P/N/U, D14의 합성 정책과 별도 S04 실 Gazebo 검증 [#43455456960](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43455456960)을 서로 연결해서 설명하되, 기록을 한 세션의 E2E 사람 회피 성공으로 합치지 않습니다.

## 2. 오늘의 발표 스토리

"로봇이 목적지를 향하다 장애물에 접근했다면, *어느 센서 숫자가 감속을 말해주고, 어느 독립 기록이 실제 정지를 증명할까요?*"

- **CLEAR:** 전방 LiDAR 2.024826m, CLEAR 구간 odom 이동 0.120132m
- **SLOW:** 전방 0.662775m, Supervisor 0.045759m/s와 Guard 최종 0.014534m/s — 수치상 두 안전 계층의 감속을 구분
- **STOP:** 전방 0.384303m, 최종 `/cmd_vel=0`; 별도 odom ZERO 지속 **1.029446s**
- **Goal 취소:** 실제 실행 중인 Nav2 Goal UUID `80e9482161224ddd8916931e7b42569e`의 상태 **5(CANCELED)**; 새 Goal 출발/성공으로 표현하지 않기
- **최대 전달 간격:** Scan 253.822ms/300ms, CM source 68.093ms/120ms, CM Observer 70.981ms/120ms, Guard internal CM age 47.653ms/150ms, Guard status 72.352ms/150ms
- **주의:** 과거 별도 CI에서 Guard first latch 나이 **188.578ms > 150ms** (#157 미해결). 이번 1회 수치 성공으로 모든 실행의 안전성을 보증하지 않습니다.

## 3. 시간표 (총 180분)

| 시각 | 실습 | 제출 |
|---|---|---|
| 19:00–19:20 | 원본/파생/합성 증거와 L0·L2·L3의 차이 | 증거 출처표 |
| 19:20–20:00 | CLEAR→SLOW→STOP, 속도 계층, Goal 취소, odom 정지 유지 증명 | 실제 숫자 설명 |
| 20:00–20:10 | 휴식 | |
| 20:10–20:45 | 전달 간격·TTL 경계 및 오류 주입 **수치 반례** 실습 | 위반 게이트 5개 |
| 20:45–21:15 | G09 P/N/U·S04와 G10의 **서로 다른 검증 실행** 구분 | 증거 연결도 |
| 21:15–21:25 | 휴식 | |
| 21:25–21:50 | 오프라인 Replay 또는 강사 기존 검증 영상, 발표 및 팀별 설명 | 3~5분 발표 |
| 21:50–22:00 | 평가표 제출·정리 | 워크시트·결과 JSON |

## 4. 설치·최초 실행 (WSL2 Ubuntu 24.04/Python 3)

```bash
cd ~
git clone --branch main \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d15-student
cd ~/axia-d15-student
git rev-parse HEAD
python3 -m unittest discover -s block_D/day15/tests -p 'test_*.py' -v
python3 block_D/day15/run_lab.py --out /tmp/axia-d15
ls -lh /tmp/axia-d15/
```

**D15는 Student `main`에 배포된 읽기 전용 증거 분석 실습입니다.** `git rev-parse HEAD`가 강사가 공지한 최종 배포 SHA와 일치하는지 확인합니다. ROS 2, Nav2, Gazebo 없이도 실행됩니다.

예상 출력:

```text
D15_EDUCATION_NUMERIC_GATE=EDUCATION_NUMERIC_ACCEPTED
D15_SYNTHETIC_NEGATIVE_DETECTION=5/5
D15_G09_G10_SOURCE_SEPARATE=True
D15_REPLAY_SCOPE=AGGREGATED_PUBLIC_EVIDENCE_ONLY_NO_NEW_ROS_GAZEBO
```

**파일:** `/tmp/axia-d15/d15_evidence_review.json`, `d15_counterexamples.json`, `d15_offline_replay.html`. 출력은 기존 성공 공개 파생 JSON `fixtures/jrcigogl_public_derived.json`의 **Git blob SHA-1 `ae7d594b5452d96cc8802bc53bc8ad578fe99fb7`**를 먼저 확인해 생성합니다. 개인 원본 TAR/ZIP/rosbag은 포함되지 않습니다.

WSL2 Windows 브라우저(선택):

```bash
explorer.exe "$(wslpath -w /tmp/axia-d15/d15_offline_replay.html)"
```

이 화면의 '이전 증거/다음 증거'는 원본 연속 영상이 아닌 **7단계 공개 숫자 스냅샷 순서**입니다. 실제 t=0/5/10초 같은 가상 시각은 추가하지 않았습니다. 브라우저를 열지 못하면 JSON/CLI만으로 수업을 진행합니다.

## 5. 테스트에서 반드시 구분할 것

- **실제 원본 증거 vs 공개 파생 값:** 본 도구는 파생 JSON 일치·계약을 확인할 뿐 원본 rosbag 메시지를 재계산하지 않습니다.
- **보고된 Scan/CM/Guard 최대치 vs 최초 위반 시점:** 파생 JSON에 타임스탬프가 없으므로 `first_violation_timestamp=null`입니다. '어느 순간 처음 위반'은 이 파일만으로 추측하면 안 됩니다.
- **`scan_gap_max_ms` 301ms / `guard_internal_cm_age_max_ms` 151ms**는 실제 현장 위반이 아니라 **학생용 수치 변조 테스트**입니다. 기준을 절대 300/150 위로 변경하지 않습니다.
- **Goal CANCELED vs odom ZERO:** ActionStatus 취소와 로봇의 별도 움직임 정지 유지 두 증거를 혼동하지 않습니다.
- **실제 감속 vs 화면 가독성:** Gazebo/RViz 창 발견은 참이지만 스크린샷·녹화 원본이 없어서 실제 화면 내용은 미검증.
- **자동 판정 HOLD vs 교육용 Accepted:** `visual_content_verified`·`raw_machine_l3_accepted`·`formal_safety_timing_accepted`·`certified_estop`을 true로 바꾸지 않습니다.

## 6. 팀 실습

1. `STUDENT_EVIDENCE_WORKSHEET_KO.md`의 '출처·수치·게이트·증거 수준'을 작성합니다.
2. `d15_offline_replay.html`에서 **CLEAR/SLOW/STOP/CANCEL/ODOM/TTL/PNU_SCOPE** 7단계를 차례로 읽어 팀원이 서로 설명합니다.
3. `d15_counterexamples.json`의 수치만 변조된 5개 사례에서 각각 최초 **실패 계약(게이트)**를 찾습니다. 실제 사건 타임스탬프가 아니므로 '최초 시간'이라고 표현하지 않습니다.
4. 별도 D13·D14 fixture 및 기존 S04 L2가 실제 G07 Owner보다 다른 세션인 이유를 설명합니다.
5. `FINAL_EVALUATION_RUBRIC_KO.md`의 기준에 따라 팀 자체 평가를 제출합니다.

## 7. 자주 발생하는 문제

- `D15_DERIVED_FIXTURE_BLOB_SHA_MISMATCH`: 공유 fixture를 수정했다는 뜻. 교육용 반례는 원본 JSON을 편집하지 않고, 테스트의 `dict(...)` 복사본으로 검증합니다.
- `EDUCATION_NUMERIC_GATE=NOT_ACCEPTED`: `failed_gates`의 첫 항목부터 확인하고 원본 데이터 조작/중단을 분리합니다. 숫자를 완화하지 않습니다.
- `ModuleNotFoundError`: 저장소 루트에서 실행하거나 파일 경로를 확인합니다.
- 화면이 없지만 JSON이 존재: HTML 브라우저 렌더링은 미검증입니다. CLI/JSON을 이용하세요.
- 'G09가 실제 사람을 감지했어요': D13/D14의 합성 P/N/U와 G07 실제 이동을 동일한 실험이라고 혼동한 것입니다.
- 'Stop했으니 E-Stop입니다': 인증된 하드웨어 E-Stop이 아니라 시뮬레이션 SW 정지입니다.

## 8. 제출

`STUDENT_EVIDENCE_WORKSHEET_KO.md` + `d15_evidence_review.json` + `d15_counterexamples.json` + 발표 3~5분 + 수행 환경 Python 버전/수정이 없는 Git SHA.

실습 성공 기준은 **기존 Baseline 실행 계약을 그대로 읽고, 범위 한계를 지키며 합성 반례가 올바르게 실패하는지 공개 CI L0로 확인**하는 것입니다. 신규 ROS·Gazebo·WSL2 실제 시연 성공을 주장하지 않습니다.
