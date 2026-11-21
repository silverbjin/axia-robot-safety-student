# AXIA BLOCK_D — D13~D15 학생용 통합 실습 실행 가이드 (최종 배포)

**대상:** ROS 2·Python 초심자 포함 / Ubuntu 24.04 또는 WSL2 Ubuntu 24.04 / Python 3.12 표준 라이브러리.  
**구성:** D13 (4시간) · D14 (3시간) · D15 (3시간). PPTX·슬라이드 파일은 범위 밖입니다.  
**검증 계약:** `BLOCK_D_RELEASE_STUDENT_CONTRACT_PASS` — *세 실습 패키지가 올바르게 제공되었다는 L0 배포 검사*. Nav2 Goal, Gazebo, 로봇 센서나 인증 E-Stop의 새로운 실행을 뜻하지 않습니다.

## 0. 배우는 흐름: 미래 예측 → 정책 판단 → 실제 기록 검증

| 실습 | 질문 | 바꿔서 제출할 것 | 실습의 증거 수준 |
|---|---|---|---|
| **D13** G09 Reachability | "같은 장소에 **같은 시간**에 있는가?" | `block_D/day13/reachability_student.py`의 TODO | 합성 16시점, 8사례, 오프라인 L0 |
| **D14** G09→LIMITED 위험정책 | "위험을 발견했는데 N 한 번으로 제한을 풀어도 되는가?" | `block_D/day14/risk_policy_student.py`의 TODO | 합성 사건 16개 + G10 15사건, 오프라인 L0 |
| **D15** G07 증거 검증 | "STOP 명령과 실제 정지 유지가 같은 증거인가?" | 수치 분석 워크시트·평가표 (운영코드 수정 없음) | 이미 인정된 `jrCIgoGl` 공개 *파생 수치*를 읽는 L0 |

**D13·D14 초기 테스트 FAIL은 정상입니다.** 학생이 직접 채울 TODO를 강사 정답으로 대체해 배포하지 않습니다. D15는 학생이 기존 증거를 해설하는 완성된 읽기 전용 실행기입니다.

## 1. 수업 준비 — GitHub main에서 시작

터미널 1개만 열고, **기존 학습 파일을 덮어쓰지 않는 새 폴더**를 사용합니다.

```bash
cd ~
git clone --depth 1 --branch main \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-block-d-student
cd ~/axia-block-d-student
python3 --version
git rev-parse HEAD
```

강사가 안내한 최종 SHA와 `git rev-parse HEAD`를 비교합니다. Ubuntu 24.04의 Python 3.12 외에 Gazebo·ROS 2 설치는 이 **오프라인 학습검증**에 필수 사항이 아닙니다. 기존 G07 시연 원본을 자동 실행하지 않으므로 Goal 승인이나 로봇 동작이 발생하지 않습니다.

## 2. 통합 원샷: 배포 파일·테스트·Replay 모두 점검

```bash
python3 block_D/tools/verify_student_release.py \
  --out /tmp/axia-block-d-final
```

출력의 세 줄과 최종 줄을 확인하세요.

```text
BLOCK_D_D13_STARTER_L0_PASS tests=10 intended_red=2 cli_rc=2
BLOCK_D_D14_STARTER_L0_PASS tests=20 intended_red=11 cli_rc=2
BLOCK_D_D15_STARTER_L0_PASS tests=18 intended_red=0 cli_rc=0
BLOCK_D_RELEASE_STUDENT_CONTRACT_PASS=1 ROS_GAZEBO_OWNER_GOAL_NOT_RUN=1
```

**중요:** D13/D14의 `intended_red`는 학생 TODO가 아직 미완성이라는 의미입니다. 위 검증기의 **최종 종료 코드 0**은 *학생 프로그램 완성*이 아니라 **학생 패키지 배포 상태 정상**을 뜻합니다. 작업 중 자신의 TODO를 완성한 학생은 통합 배포 검사 대신 해당 요일 테스트를 실행해 GREEN을 확인하세요.

생성 파일:
- `/tmp/axia-block-d-final/BLOCK_D_RELEASE_RESULT.json` — 3일 배포 계약 요약·검증 범위
- `/tmp/axia-block-d-final/d13/` — 8개 합성 예측 사례·HTML·unittest 출력
- `/tmp/axia-block-d-final/d14/` — 16개 정책 사례·15개 G10 사건·HTML·unittest 출력
- `/tmp/axia-block-d-final/d15/` — G07 공개 파생 증거 해설·HTML·5개 수치 변조·unittest 출력

이 폴더에는 **별도 강사 정답, raw rosbag, 사진, 개인 환경 로그**를 수집하지 않습니다.

## 3. D13 — 시간 인덱스 Reachability

상세 교재: `block_D/day13/STUDENT_LAB_GUIDE_KO.md`  
워크시트: `block_D/day13/STUDENT_WORKSHEET_KO.md`

```bash
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
```

처음에는 **10개 테스트 중 2개 P/N 판정 실패**, runner 종료 코드 2가 정상입니다. `reachability_student.py`의 입력 유효성·16개 같은 시각 샘플·사람 등속도 예측·P/N/U 집계를 구현하고, 테스트 10개가 모두 `OK`가 될 때까지 고칩니다.

- P: 미래 동일 시점 원형 점유영역 중첩.
- N: 모든 유효한 동일 시점에서 비중첩 (다른 보호센서 없이 무조건 운행 허가 아님).
- U: stale/future/low confidence/시간 누락 등 판정 불가.
- 프레임 불일치는 별도 교육용 CLI 사전검사 U입니다. 원본 G09 함수의 TF 자동 변환 주장이 아닙니다.

## 4. D14 — 위험정책 NORMAL → LIMITED_REQUEST

상세 교재: `block_D/day14/STUDENT_LAB_GUIDE_KO.md`  
워크시트: `block_D/day14/STUDENT_WORKSHEET_KO.md`

```bash
python3 -m unittest discover -s block_D/day14/tests -p 'test_*.py' -v
python3 block_D/day14/run_lab.py --out /tmp/axia-d14
```

처음에는 **20개 테스트 중 11개 정책 TODO 실패**가 정상입니다. `risk_policy_student.py`의 `apply_verdict()`와 `expired_verdict()`를 구현합니다.

- P/U → LIMITED **요청**, 첫 정상 N → 제한 요청 없음.
- 이미 제한된 뒤 N → 제한 자동 해제 **금지**.
- 중복 seq/역행, 출처 위조, stale(호스트 수신 TTL 0.5초), 낮은 신뢰성 → 보수적 제한 또는 메시지 거부.
- `NORMAL_POLICY`와 `LIMITED_REQUEST`는 합성 정책 **표시**이며 실제 Supervisor FSM 상태 또는 `/cmd_vel` 발행이 아닙니다.
- G10 사건은 실제 Fault Injector나 Owner Reset을 작동시키지 않는 15개의 교육용 합성 사건입니다.

## 5. D15 — G07 수치 증거를 읽는 최종 실습

상세 교재: `block_D/day15/STUDENT_LAB_GUIDE_KO.md`  
분석지: `block_D/day15/STUDENT_EVIDENCE_WORKSHEET_KO.md`  
평가표: `block_D/day15/FINAL_EVALUATION_RUBRIC_KO.md`

```bash
python3 -m unittest discover -s block_D/day15/tests -p 'test_*.py' -v
python3 block_D/day15/run_lab.py --out /tmp/axia-d15
```

읽기 전용 프로그램은 **18/18 테스트 PASS**가 정상입니다. 7개 숫자 스냅샷은 CLEAR→SLOW→STOP, 동일 Goal CANCELED(5), odom ZERO 유지, 타이밍 최대치, G09/G10 증거 출처 구분을 순서대로 보여 줍니다. 생성된 `d15_offline_replay.html`은 실제 Gazebo 영상이나 원본 rosbag 실시간 재생이 아닙니다.

- 공개 Owner `jrCIgoGl` 수치: CLEAR 전방 2.024826m, SLOW 0.662775m, STOP 0.384303m, odom ZERO 1.029446s.
- 최대 관측 간격: Scan 253.822/300ms, CM source 68.093/120ms, CM Observer 70.981/120ms, Guard 내부 age 47.653/150ms, Guard status 72.352/150ms.
- **다섯 수치 변조 반례**는 실제 현장 장애 기록이 아니라 교육용 반례입니다.
- D13/G09 P/N/U·D14 합성 위험정책과 G07 Owner의 실제 사람 검출을 하나의 실제 실행으로 합치지 않습니다.

## 6. HTML 출력이 필요한 경우 (선택)

WSL2에서 Windows 브라우저를 쓰는 경우:

```bash
explorer.exe "$(wslpath -w /tmp/axia-block-d-final/d15/d15_offline_replay.html)"
```

화면이 안 열려도 `BLOCK_D_RELEASE_RESULT.json`과 각 요일의 `runner.log`, 결과 JSON으로 수업을 진행할 수 있습니다. HTML 파일 **생성 검증**은 CI에서 수행했지만 현장 브라우저 렌더링 품질은 별도 검증입니다.

## 7. 자주 묻는 오류와 원인

| 증상 | 먼저 점검할 항목 | 처리 |
|---|---|---|
| D13 test 2개 FAIL | `reachability_student.py`가 `return "U"`인가? | 정상 시작 상태. 학생 TODO 직접 구현 |
| D14 test 11개 FAIL | `risk_policy_student.py`가 `D14_TODO_NOT_IMPLEMENTED`인가? | 정상 시작 상태. 정책 구현 |
| D15 예전 SHA/MANIFEST FAIL | `git rev-parse HEAD`, 원본 파일 변경 여부 | 배포 main 새 클론과 비교하고 교재 원본 되돌리기 |
| 통합 검사 후 학생 TODO를 완성했는데 통합 검사 FAIL | 통합 검사는 **배포 당시 starter 상태**를 기대 | 요일별 unittest로 학습 완료 검사 |
| HTML 브라우저 빈 화면 | HTML 파일 존재/브라우저 로컬 파일 읽기 | JSON 결과로 수업 대체; 시각 검증 NOT_RUN 명시 |
| Safety STOP = E-Stop 주장 | `certified_estop=false` | 시뮬레이션 SW STOP과 인증 E-Stop 분리 |
| Scan 간격 301ms가 실제 현장 오류라는 주장 | 반례 `synthetic_mutation` 필드 | D15 테스트 변조값. 실제 `jrCIgoGl` 최대는 253.822ms |

## 8. 제출·보존·최종 실습 채점

D13은 수정한 TODO 함수·10개 GREEN 로그·워크시트, D14는 위험정책 TODO·20개 GREEN 로그·상태 전이표, D15는 공개 수치 분석 워크시트·5개 수치 변조 탐지·3~5분 발표·최종 평가표를 제출합니다.

**배포 검사 PASS ≠ 학생 TODO 완성 PASS ≠ 실제 Gazebo/정식 안전 인수.** 기존 교육용 `jrCIgoGl` Baseline은 원본 기능·수치 범위에서 ACCEPTED이나 원본 기계 판정은 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, 형식적 안전 타이밍 인증은 NOT_CLAIMED, 인증 E-Stop은 false입니다. 과거 Guard >150ms 오류 [Issue #157](https://github.com/silverbjin/axia-robot-safety-ci-public/issues/157)는 별도로 관리합니다.
