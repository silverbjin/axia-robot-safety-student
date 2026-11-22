# AXIA BLOCK_D D15 — 초심자용 단계별 실습 핸드북

**학생용 공개 문서 · 강의실/자가학습 · Ubuntu 24.04 및 WSL2 Ubuntu 24.04**  
**수업:** 2026-11-27(금) 19:00–22:00, 180분. 강사 제공 38장 PPTX의 코드를 설명하는 실습서.  
**오늘은 과거 G07 실주행의 공개 파생 집계 자료를 Python 오프라인 L0로 분석한다.** 새 ROS 2, Gazebo, Nav2 Goal, Fault Injector, 모터 제어를 실행하지 않는다. 소프트웨어 STOP은 인증된 E-Stop이 아니다.

이 문서는 [기존 학생 실습 가이드](STUDENT_LAB_GUIDE_KO.md), [학생 데모 가이드](STUDENT_DEMO_GUIDE_KO.md), [증거 워크시트 A~H](STUDENT_EVIDENCE_WORKSHEET_KO.md), [100점 평가표](FINAL_EVALUATION_RUBRIC_KO.md)를 보충한다. 강사용 비공개 정답과 원본 rosbag은 포함하지 않는다.

## 0. 두 학습 주제와 오늘 수행하는 일 (10분)

1. **Human-aware Safety AMR 통합 MVP 구현:** 기존 센서·Nav2·Supervisor·Collision Monitor·Guard와 합성 사람 위험 예측의 **구조와 코드 입출력**을 배운다. D13·D14 P/N/U는 합성 데이터이므로 이번 G07에서 인간을 실제 검출했다고 주장하지 않는다.
2. **통합 안전제어 시나리오 검증 및 결과정리:** 이전 G07 공개 파생 증거에서 CLEAR→SLOW→STOP, Nav2 Action Goal 취소, odom 정지 유지, 5개 TTL과 수치 반례, 인수 제한사항을 분석한다.

**이야기:** 서비스 로봇이 목표점으로 향하던 중 전방 물체에 접근했다. 누군가 “화면에서 멈췄으니 안전합니다”라고 말한다. 개발자는 화면만 믿지 않고 **센서값, 속도 명령, Action 결과, 실제 움직임, 전달 타이밍**을 독립적으로 확인해야 한다.

### 자료의 진짜 출처

| 자료 | 출처 | 이번 수업에서 의미하는 것 |
|---|---|---|
| G07 `jrCIgoGl` | 과거 강사 WSL2 실제 Moving Goal 실행을 정리한 **공개 파생 JSON** | 기존 실행에 보고된 수치만 L0 검증 |
| D13 G09 P/N/U | 합성 사람·로봇 궤적/16개 시간점 | 위험 여부 판단을 구현하는 별도 학생 TODO |
| D14 G09/G10 | 합성 위험정책 16사례, 합성 G10 15사건 | 제한 요청·안전 정책 개념 학습 |
| S04 Gazebo L2 | 별도 실제 Gazebo CI #43455456960 | 합성 정책 입력을 기존 안전 계층에 연결한 **다른 실행** |

이 자료들을 한 번의 사람 회피 E2E 성공으로 합치지 않는다. L0는 문서·Python·fixture 계약 검증, L2는 별도 Gazebo 기능 실행, Owner L3는 별도 현장 원본 인수 범위다. **오늘 실행은 L0뿐이다.**

### 0-1. 시스템 아키텍처: 실제 G07과 합성 사람 위험 경로를 분리하자

~~~text
[이전 G07 실제 시뮬레이션]
Gazebo LiDAR -- Gazebo Transport --> ros_gz_bridge --> ROS /scan(LaserScan)
                                                        |              |
                                                        v              v
                                                 Nav2 Costmap     Collision Monitor
                                                 /Controller          ^
                                                      |                |
                                              기존 속도 명령           |
                                                      v                |
                                                AXIA Supervisor -------+
                                                      |
                                              /cmd_vel_supervised
                                                      v
                                               Collision Monitor
                                                      |
                                               /cmd_vel_pre_guard
                                                      v
                                                  Base Guard
                                                      |
                                                   /cmd_vel
                                                      v
                                                  Robot / odom
                                  + Nav2 NavigateToPose Goal Action 결과 (독립)

[D13 합성 P/N/U] --> [D14 합성 Risk Policy] --> [별도 S04 L2]
  (위 G07 Owner의 실제 사람 검출·동일 세션이라는 증거가 아님)

[과거 실주행 원본] --> [공개 파생 집계 JSON] --> [D15 Python]
                                          --> [7장면 HTML + JSON 2개]
~~~

**용어 설명:** Topic은 Publisher가 발행한 메시지를 Subscriber가 받는 경로다. `/scan`은 `sensor_msgs/msg/LaserScan`, 속도 `/cmd_vel`은 `geometry_msgs/msg/Twist`다. `NavigateToPose`는 오래 걸리는 Goal을 다루는 **Action**이며 단순 Topic이 아니다. odom은 명령과 구별되는 이동 추정 정보다. Guard의 최종 ZERO 명령은 물리 정지 시간 자체를 증명하지 않는다.

### 0-2. 180분 수업에서 작성할 것

| 시간 | 실습 및 학습 내용 | 워크시트 |
|---|---|---|
| 19:00–19:20 | 시스템 용어, 자료 출처, 아키텍처 | A·E |
| 19:20–20:00 | 클론→18개 테스트→Replay→CLEAR/SLOW/STOP·Goal/odom | A·B·C |
| 20:00–20:10 | 휴식 | |
| 20:10–20:45 | 채널별 TTL 값과 5개 수치 반례 | D·F |
| 20:45–21:15 | D13/D14/G10/S04/G07 세션 분리와 원본 HOLD | E·G |
| 21:15–21:25 | 휴식 | |
| 21:25–21:50 | HTML/JSON 발표, 보고서 작성 | H |
| 21:50–22:00 | 100점 평가표·미검증 항목·제출 | A~H |

## 1. 지금 Ubuntu 터미널에 있는지 확인하자

**Windows Terminal의 Ubuntu 탭** 또는 Ubuntu 터미널에 입력한다. Windows PowerShell에 입력하는 명령이 아니다.

~~~bash
pwd
uname -s
python3 --version
git --version
~~~

**예상:** `uname -s`가 `Linux`, Python·Git 버전이 출력된다. Ubuntu 24.04는 일반적으로 Python 3.12를 제공하지만 실제 출력이 기준이다. 오류 `python3: command not found`, `git: command not found`이면 인터넷이 연결된 Ubuntu에서 `sudo apt update`, `sudo apt install -y python3 git`으로 필요한 두 프로그램만 설치한다. ROS 2·Gazebo 설치는 필요 없다.

**왜 하는가?** 잘못된 터미널에서 명령을 실행하면 기능 문제가 아닌데도 “프로그램 오류”로 오해하기 쉽기 때문이다.

## 2. GitHub에서 학생용 소스 클론하기

~~~bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d15-classroom
cd ~/axia-d15-classroom
pwd
git rev-parse HEAD
git status --short
ls -l block_D/day15/
~~~

**명령의 의미:** `cd ~`는 홈 디렉터리 이동, `git clone`은 공개 저장소 복사, `--branch main`은 배포 브랜치 선택, `--depth 1`은 최근 커밋만 내려받기다. `git rev-parse HEAD`는 **내가 내려받은 커밋 버전(SHA 40자)**을 알려준다. `git status --short`가 아무것도 출력하지 않으면 변경 파일이 없는 정상 상태다.

**예상:** 작업 경로 끝에 `axia-d15-classroom`, 파일 `run_lab.py`·`evidence_review.py`·`fixtures/`·`tests/`가 존재한다.

**실패 대체:** `destination path ... already exists`가 나오면 기존 폴더를 삭제하거나 덮어쓰지 말고 `axia-d15-classroom2`처럼 다른 새 디렉터리명을 사용한다. 그 이후 `cd`도 동일하게 바꾼다.

## 3. 원본 데이터가 맞는지 SHA 확인하기

~~~bash
cd ~/axia-d15-classroom
ls -l block_D/day15/run_lab.py
ls -l block_D/day15/evidence_review.py
ls -l block_D/day15/fixtures/jrcigogl_public_derived.json
git hash-object block_D/day15/fixtures/jrcigogl_public_derived.json
~~~

**기존 공개 파생 fixture의 Git blob SHA-1 기대값:**

~~~text
ae7d594b5452d96cc8802bc53bc8ad578fe99fb7
~~~

**왜 하는가?** 결과를 믿기 전에 *어떤 원본 파일*을 분석했는지 증명해야 한다. `git rev-parse HEAD`는 저장소 버전, `git hash-object`는 개별 파일의 내용을 식별한다. 수치 반례를 배우겠다고 이 JSON을 직접 바꾸면 원본 증거가 훼손된다.

| 파일 | 역할 | 학생의 변경 가능 여부 |
|---|---|---|
| `fixtures/jrcigogl_public_derived.json` | 과거 실제 실행의 공개 파생 집계 | 변경 금지 |
| `evidence_review.py` | SHA·거리·Goal·odom·5 TTL·HOLD 검사 | 읽기 전용 |
| `run_lab.py` | 분석 결과 7장면·HTML 생성 | 읽기 전용 |
| `STUDENT_EVIDENCE_WORKSHEET_KO.md` | A~H 증거 분석지 | 제출용 사본 작성 |

## 4. 18개 테스트가 무엇을 검증하는지 보기

~~~bash
cd ~/axia-d15-classroom
python3 -m unittest discover -s block_D/day15/tests -p 'test_*.py' -v
echo "UNITTEST_EXIT=$?"
~~~

**기존 배포본에서 예상:** `Ran 18 tests`, `OK`, `UNITTEST_EXIT=0`. 실패하면 자신의 실제 원본 로그를 기록한다.

- `-m unittest`: 파이썬 표준 테스트 실행기.
- `discover`: 폴더에서 테스트 자동 검색.
- `-s`: 테스트 폴더 지정.
- `-p`: 테스트 파일 이름 규칙.
- `-v`: 각각의 성공/실패 이유 표시.

**18개 PASS의 뜻:** D15 공개 파생 JSON과 **분석기의 L0 계약**이 일치한다는 것이다. 새로운 ROS 2·Gazebo·인증 E-Stop을 시험한 것은 아니다. D13·D14의 초기 TODO에는 별도의 의도된 RED가 있을 수 있으나 D15는 완성된 읽기 전용 분석기여서 18개 GREEN이 정상이다.

## 5. 7개 숫자 장면을 생성하는 프로그램 실행

~~~bash
cd ~/axia-d15-classroom
python3 block_D/day15/run_lab.py --out /tmp/axia-d15
echo "RUN_EXIT=$?"
ls -lh /tmp/axia-d15/
~~~

`--out`은 결과 저장 위치다. 기존 코드는 다음 장면 순서를 출력한다.

~~~text
D15_STEP=CLEAR kind=actual_reported_snapshot
D15_STEP=SLOW kind=actual_reported_snapshot
D15_STEP=STOP kind=actual_reported_snapshot
D15_STEP=CANCEL kind=derived_action_claim
D15_STEP=ODOM_DWELL kind=derived_odom_claim
D15_STEP=SAFETY_TTL kind=aggregated_maxima_no_event_timestamps
D15_STEP=PNU_AND_SCOPE kind=separate_educational_evidence
D15_EDUCATION_NUMERIC_GATE=EDUCATION_NUMERIC_ACCEPTED
D15_SYNTHETIC_NEGATIVE_DETECTION=5/5
D15_G09_G10_SOURCE_SEPARATE=True
D15_REPLAY_SCOPE=AGGREGATED_PUBLIC_EVIDENCE_ONLY_NO_NEW_ROS_GAZEBO
RUN_EXIT=0
~~~

**생성 파일 3개:**

- `/tmp/axia-d15/d15_evidence_review.json`: 7개 스냅샷 및 상태 검증 결과.
- `/tmp/axia-d15/d15_counterexamples.json`: 교육용 5개 숫자 변조·실패 게이트.
- `/tmp/axia-d15/d15_offline_replay.html`: 7단계를 버튼으로 넘기는 **숫자 설명 화면**.

**주의:** 이 HTML은 실제 영상·rosbag Replay·로봇 실시간 타임라인이 아니다. 화면의 순서는 학생이 읽을 **목차 순서**다.

## 6. 화면을 열고 7단계 관찰하기

WSL2 Ubuntu에서는:

~~~bash
explorer.exe "$(wslpath -w /tmp/axia-d15/d15_offline_replay.html)"
~~~

`wslpath -w`는 Ubuntu 경로를 Windows용 경로로 바꾼다. `explorer.exe`는 Windows가 해당 파일을 열도록 요청한다. 순수 Ubuntu나 headless 서버에서는 `HTML_BROWSER_NOT_RUN`으로 기록하고 바로 다음 JSON 읽기 단계로 이동한다.

| 번호 | 화면 | 공개 파생 수치 예시 | 학생 질문 |
|---|---|---|---|
| 1 | CLEAR | `clear_front_m≈2.024826m`, `clear_odom_travel_m≈0.120132m` | 전방거리와 실제 이동거리가 왜 다른가? |
| 2 | SLOW | `slow_front_m≈0.662775m`, supervised `0.045759m/s`, final `0.014534m/s` | 왜 앞단과 최종 명령 속도가 다른가? |
| 3 | STOP | `stop_front_m≈0.384303m`, `stop_final_vx_mps=0` | 명령 0만으로 물리 정지가 증명되는가? |
| 4 | CANCEL | UUID `80e9482161224ddd8916931e7b42569e`, `goal_cancel_status=5` | Goal 성공과 취소는 어떻게 다른가? |
| 5 | ODOM_DWELL | `zero_dwell_sec≈1.029446s`, `odom_movement_m≈0.137285m` | 이동 누계와 정지 유지 시간은 다른가? |
| 6 | SAFETY_TTL | Scan·CM source·CM Observer·Guard age·status | 다섯 지표의 기준이 왜 각각 다른가? |
| 7 | PNU_AND_SCOPE | `raw_machine_status=HOLD_RAW_REVIEW_AND_VISUAL_PENDING` | 왜 숫자 PASS인데 최종 인수는 HOLD인가? |

**학생 활동:** [워크시트 A](STUDENT_EVIDENCE_WORKSHEET_KO.md)에 각 단계의 데이터 필드와 근거 두 개 이상, 그리고 이 데이터만으로 **주장할 수 없는 내용**을 적는다.

## 7. 화면 없이 JSON 읽는 법

~~~bash
python3 -m json.tool /tmp/axia-d15/d15_evidence_review.json | head -90
~~~

`JSON`은 키·값을 기록하는 구조다. 화면에서 `null`은 “시각 정보 없음”이고 Python에서는 `None`으로 나온다. 아래 코드는 **파일을 수정하지 않고 읽기만 한다**.

~~~bash
python3 - <<'PY'
import json
from pathlib import Path
r=json.loads(Path("/tmp/axia-d15/d15_evidence_review.json").read_text(encoding="utf-8"))
print("evidence_source =",r["evidence_source"])
print("new_gazebo_or_wsl2_executed =",r["new_gazebo_or_wsl2_executed"])
print("numeric_gate =",r["baseline"]["numeric_gate"])
print("raw_machine_status =",r["baseline"]["raw_machine_status"])
print("first_violation_timestamp =",r["baseline"]["first_violation_timestamp"])
for step in r["snapshots"]:
    print("STEP",step["id"],"kind =",step["kind"])
PY
~~~

**기존 코드 예상 핵심값:** `PUBLIC_DERIVED_NUMERIC_NOT_RAW`, `False`, `EDUCATION_NUMERIC_ACCEPTED`, `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, `None`, `STEP CLEAR ... STEP PNU_AND_SCOPE`.

**해설:** `first_violation_timestamp=None`은 버그가 아니다. 집계 최대값에는 실제 메시지 이벤트 시각이 없으므로 최초 안전 상태 전이나 타이밍 위반 시각을 역산할 수 없다. 
