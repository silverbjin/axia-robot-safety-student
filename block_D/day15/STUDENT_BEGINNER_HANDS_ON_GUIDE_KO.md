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


---

## 8. 코드 읽기: 입력 → 처리 → 출력의 여섯 함수

초심자는 전체 코드를 외우지 말고 **어떤 입력을 받아 어떤 검사를 거쳐 어떤 파일을 생성하는가**를 먼저 이해한다.

~~~bash
cd ~/axia-d15-classroom
grep -nE '^def (run|ordered_snapshots|load_evidence|review_baseline|negative_counterexamples|validate_g09_g10_separation)' \
  block_D/day15/run_lab.py block_D/day15/evidence_review.py
~~~

~~~text
입력: fixtures/jrcigogl_public_derived.json
  | load_evidence()                 Git blob SHA 검증, JSON 읽기
  | review_baseline()              거리·속도·Goal·odom·5 TTL·HOLD 검사
  | validate_g09_g10_separation()  D13/D14 합성과 G07 출처 분리
  | negative_counterexamples()     deepcopy 복사본에 5개 수치 변조
  | ordered_snapshots()            교육용 7단계 화면/순서 구성
  | run()                          전체 수행 및 결과 파일 작성
  v
d15_evidence_review.json + d15_counterexamples.json + d15_offline_replay.html
~~~

| 함수 | 입력 | 처리 | 출력 및 의미 |
|---|---|---|---|
| `load_evidence()` | 공개 파생 fixture 파일 | bytes의 Git blob SHA-1 검사 후 JSON 읽기 | 불일치 시 `D15_DERIVED_FIXTURE_BLOB_SHA_MISMATCH` |
| `review_baseline(data)` | Python 사전(dict) | 주행·Goal UUID·odom ≥1초·다섯 TTL·원본 HOLD | `numeric_gate`, `failed_gates`, `first_violation_timestamp=None` |
| `validate_g09_g10_separation()` | D13·D14 합성 fixture | N/P/U 3라벨, 정책 16사례, G10 15사건·별도 S04 구분 | `safe_separation=True`, G07 실제 사람 검출 `False` |
| `negative_counterexamples(data)` | 원본을 읽은 dict | `copy.deepcopy`를 통해 복사본에만 수치/플래그 변조 | 5개 사례 `detected=true`, `not_accepted=true` |
| `ordered_snapshots(data)` | 7개 단계 필드 설정과 JSON | 시각을 만들지 않고 설명 순서 지정 | `CLEAR`부터 `PNU_AND_SCOPE`까지 |
| `run()` | 검증·반례·순서 결과 | JSON 2개와 HTML 1개 저장 | `D15_EDUCATION_NUMERIC_GATE=...` |

**실제 로봇의 코드 읽기 대상:** `block_B/day07/h01_runtime/ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_supervisor_node.py`는 기존 Supervisor FSM 및 기본 비활성 합성 G09 어댑터, 같은 패키지의 `p2_base_guard_node.py`는 `/cmd_vel_pre_guard` 수신·신선도 검사와 최종 `/cmd_vel` 발행을 다룬다. **코드 수정·노드 실행·안전 임계 완화는 이 실습에 포함되지 않는다.**

**생각할 질문:** 왜 `negative_counterexamples()`는 원본 JSON을 직접 수정하지 않을까? → 증거 파일은 불변으로 보존하고 반례만 복사본에서 검증하기 위해서다.

## 9. 숫자 실습 ① 감속 명령·Goal 취소·odom 정지의 차이

SLOW 구간의 **이전 실주행에서 보고된 값**:

- Supervisor 명령 = 0.045758649706840515m/s
- Guard final 명령 = 0.0145335104316473m/s

~~~bash
python3 - <<'PY'
supervised=0.045758649706840515
final=0.0145335104316473
print("final/supervised =", round(final/supervised*100,1), "%")
print("명령 차이 =", round(supervised-final,6), "m/s")
PY
~~~

**예상:** 최종 명령은 앞단 명령의 약 **31.8%**, 차이는 약 **0.031225m/s**다. 이 사실만으로 특정 내부 함수가 몇 퍼센트를 감속했는지나 실제 바퀴 속도를 단정할 수 없다.

| 기록 | 직접적으로 확인하는 것 | 추가 증거가 필요한 것 |
|---|---|---|
| `stop_final_vx_mps=0` | final 속도 **명령** 0 | 실제 휠 속도 및 정지 유지 |
| `goal_cancel_status=5` | 정확한 `Goal UUID`가 `CANCELED`로 종료 | 실제 물리 정지 |
| `zero_dwell_sec=1.0294455669998115` | 독립 odom ZERO 유지 ≥1초 | 다른 모든 환경의 인증 안전 성능 |
| `odom_movement_m=0.13728483165125352` | 해당 실행의 이동 누계 | 마지막 STOP 구간의 속도 ZERO |

**Goal UUID:** `80e9482161224ddd8916931e7b42569e`. `CANCELED(5)`와 `SUCCEEDED`는 다른 결과다. 다른 Goal의 취소를 가져오지 않도록 `exact_goal_uuid_cancelled=true`도 검사해야 한다.

**워크시트 A/B/C:** CLEAR/SLOW/STOP의 전방 LiDAR 거리 2.024826→0.662775→0.384303m는 로봇이 이동한 누적 odom 거리와 다른 측정이다.

## 10. 숫자 실습 ② Scan·CM·Guard의 서로 다른 TTL 5개

TTL(Time To Live)은 메시지 **신선도를 제한하는 애플리케이션의 시간 기준**이다. ROS 2 QoS Deadline과 Guard 내부 수신 나이 감시는 서로 관련되지만 **동일한 검사 기능이 아니다**.

| 경계 | 이전 한 실행 최대(ms) | 기준(ms) | 남은 여유(ms) |
|---|---:|---:|---:|
| Scan 수신 간격 | 253.822 | 300 | 46.178 |
| CM source 발행 간격 | 68.093 | 120 | 51.907 |
| CM Observer 수신 간격 | 70.981 | 120 | 49.019 |
| Guard 내부 CM age | 47.653 | 150 | 102.347 |
| Guard status 수신 간격 | 72.352 | 150 | 77.648 |

**계산:** `여유 = 한계 - 측정 최대`. 양수면 **이전 해당 실행에서 보고된 값**이 기준 내에 있다는 뜻이다. 모든 후속 실행의 안정성을 뜻하지는 않는다.

다음은 **기존 공개 fixture**에서 숫자를 읽는 계산 연습이다. **새 센서를 실행하지 않는다.**

~~~bash
cd ~/axia-d15-classroom
python3 - <<'PY'
import json
from pathlib import Path
d=json.loads(Path("block_D/day15/fixtures/jrcigogl_public_derived.json").read_text(encoding="utf-8"))
limits={"scan_gap_max_ms":300,
        "cm_source_gap_max_ms":120,
        "cm_observer_gap_max_ms":120,
        "guard_internal_cm_age_max_ms":150,
        "guard_status_gap_max_ms":150}
for name,limit in limits.items():
    observed=d[name]
    result="WITHIN" if observed<=limit else "EXCEEDED"
    print(f"{name}: max={observed:.3f}ms, limit={limit}ms, margin={limit-observed:.3f}ms, {result}")
PY
~~~

**기존 fixture 예상:** 다섯 항목 모두 `WITHIN`.

### 실제 업무 사례: 발행은 정상인데 수신이 지연된다면?

별도 공개 CI에서 CM source 간격 **41.774807ms**, RMW 수신 간격 **349.246577ms**, 독립 CM Observer 수신 간격 **354.356252ms**가 보고됐다([G07 Issue #157](https://github.com/silverbjin/axia-robot-safety-ci-public/issues/157)).

~~~text
CM source 연속 발행 41.775ms
  └─ ROS RMW / 스케줄링 / 수신 경계
       ├─ 수신 간격 349.247ms
       └─ 독립 Observer 간격 354.356ms
~~~

이 자료는 `jrCIgoGl`의 위 표와 **다른 실행**이다. “Gazebo LiDAR가 349ms마다 발행했다”는 추론은 틀리다. 실제 첫 위반 시각은 원본 메시지 타임스탬프와 첫 안전 상태 전이를 분석해야 확인할 수 있다. 원인 미확정 상태에서 WSL2 현장 재시도만 반복하지 않는다.

## 11. 5개 합성 반례로 안전 검사 배우기

오늘은 실제 Fault Injector나 STOP/RESET 명령을 보내지 않고 **복사된 숫자**를 변경해 검증기가 거부하는지 확인한다.

~~~bash
python3 -m json.tool /tmp/axia-d15/d15_counterexamples.json | head -110
~~~

| 사례 | 바뀐 필드·값 | 예상 실패 게이트 | 왜 중요한가? |
|---|---|---|---|
| `SCAN_301MS` | `scan_gap_max_ms=301` (>300) | `scan_gap_max_ms` | Scan 전달 간격 경계 초과 |
| `GUARD_151MS` | `guard_internal_cm_age_max_ms=151` (>150) | `guard_internal_cm_age_max_ms` | Guard 신선도 경계 초과 |
| `GOAL_WRONG` | `exact_goal_uuid_cancelled=false` | `goal_cancel` | 잘못된 Goal 취소 주장 방지 |
| `DWELL_0_5S` | `zero_dwell_sec=0.5` | `odom_zero_dwell` | 요구 정지 유지시간 부족 |
| `FALSE_CERTIFICATION` | `certified_estop=true` 위조 | `scope_preserved` | 인증되지 않은 안전 주장 거부 |

JSON 키 `case`, `synthetic_mutation`, `expected_failed_gate`, `detected`, `not_accepted`를 확인한다. **5/5**가 `detected=true`·`not_accepted=true`인 기존 예상이다. 이는 현장에서 실제로 발생한 고장 다섯 건이 아니라 *교육용 반례*다.

**구별:** 별도 과거 CI의 실제 Guard first latch **188.578ms > 150ms**는 `GUARD_151MS` 합성 반례와 다른 증거다.

## 12. 워크시트 A~H를 빈칸부터 채우는 방법

[학생용 워크시트](STUDENT_EVIDENCE_WORKSHEET_KO.md) 사본을 열고 아래 순서로 작성한다.

- **A — 7장면:** CLEAR·SLOW·STOP·CANCEL·ODOM_DWELL·SAFETY_TTL·PNU_AND_SCOPE마다 실제 필드값 두 개 이상과 **그 값으로 주장할 수 없는 것**을 적는다.
- **B — 속도:** `slow_supervised_vx_mps`와 `slow_final_vx_mps`를 옮겨 적고 `final/supervised×100`을 계산한다. 두 값이 **같은 물리 측정**이 아님을 설명한다.
- **C — Goal·odom:** 실제 UUID, `5(CANCELED)`, `zero_dwell_sec`, 이동 누계를 적어 서로 다른 역할을 설명한다.
- **D — TTL:** 위 표를 다시 적고 `first_violation_timestamp=null`이 집계 자료의 정상적인 한계인 이유를 쓴다.
- **E — 출처:** D13·D14·G10은 합성, S04는 별도 실제 Gazebo, G07은 이전 실제 실행 공개 파생 증거임을 구분한다.
- **F — 반례:** 5개 사례별 거부 게이트를 적고 “실제 현장 사건인가?”에 **아니오**라고 답한다.
- **G — 인수 범위:** `raw_machine_status=HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, `visual_content_verified=false`, `formal_safety_timing_accepted=false`, `certified_estop=false`를 옮겨 적는다.
- **H — 발표:** 관찰(1분) → Goal/odom(1분) → TTL·반례(1분) → 출처·미검증(1분)으로 **3~5분** 구성한다.

### 좋은 결과 보고 문장

“이전 실제 G07 공개 파생 수치에서 STOP 최종 명령 0m/s와 독립 odom ZERO 약 1.029초가 보고된다. 그러나 이번에는 실제 Gazebo·WSL2·rosbag을 새로 실행하지 않았고 자동 원본 상태는 HOLD다.”

## 13. 그대로 채우는 실무형 1페이지 보고서

~~~text
AXIA D15 학습자 안전 증거 분석 보고서
팀/이름: ________   날짜: ________
OS/Python: ________   git HEAD SHA: ________

[실행 증거]
unittest 결과: ____ / 18, PASS|FAIL, 첫 오류: ______
run_lab.py 종료 코드: ____ ; JSON 2개/HTML 1개 생성: ____
브라우저: OK | HTML_BROWSER_FAILED | HTML_BROWSER_NOT_RUN

[이전 G07 공개 파생 수치]
CLEAR/SLOW/STOP 거리: ______ / ______ / ______ m
Supervisor/final 속도: ______ / ______ m/s
동일 Goal UUID·CANCELED(5): ______
odom ZERO 유지: ______ s

[시간·반례]
Scan/CM source/CM Observer/Guard age/Guard status 최대: ______
합성 수치 반례 탐지: ____ / 5
실제 최초 위반 시각: 제공되지 않음 / 근거: ______

[증거 수준]
D13/D14 P/N/U·G10: 합성
G07 jrCIgoGl: 이전 실행의 공개 파생 집계
이번 실제 Gazebo/ROS/Goal: NOT_RUN
raw_machine_status: HOLD_RAW_REVIEW_AND_VISUAL_PENDING
formal safety: NOT_CLAIMED ; certified E-Stop: false

[최종 결론 2~4문장]
________________________________________________
~~~

기존 [100점 루브릭](FINAL_EVALUATION_RUBRIC_KO.md)은 출처 15, 거리·속도 20, Goal·odom 20, TTL 20, P/N/U 세션 구분 15, 반례·발표 10점이다. CI PASS를 학생 자동 만점으로 처리하지 않는다.

## 14. 임시 출력 파일을 제출 폴더에 보관하기

`/tmp`는 나중에 삭제될 수 있다. 자신의 홈에 **결과 파일만** 복사한다.

~~~bash
mkdir -p "$HOME/axia-d15-submission"
cd ~/axia-d15-classroom
git rev-parse HEAD > "$HOME/axia-d15-submission/git_head.txt"
python3 --version > "$HOME/axia-d15-submission/python_version.txt" 2>&1
cp /tmp/axia-d15/d15_evidence_review.json "$HOME/axia-d15-submission/"
cp /tmp/axia-d15/d15_counterexamples.json "$HOME/axia-d15-submission/"
ls -lh "$HOME/axia-d15-submission/"
~~~

본인이 쓴 **워크시트, 보고서, 실제 테스트 출력**을 추가한다. 비공개 강사 정답, 개인 원본 rosbag/TAR/ZIP, GitHub 자격증명을 제출하지 않는다.

## 15. 문제 발생 시 처음 실패한 곳을 먼저 본다

| 최초 오류 | 우선 확인 | 안전한 처리 |
|---|---|---|
| `python3` / `git` 없음 | Ubuntu 탭, 버전 출력 | 해당 기본 프로그램만 설치 |
| `destination path already exists` | 기존 클론 디렉터리 | 삭제 대신 새 폴더 이름으로 클론 |
| `ModuleNotFoundError` | `pwd`와 루트 경로 | `cd ~/axia-d15-classroom` 후 가이드 명령 재실행 |
| `D15_DERIVED_FIXTURE_BLOB_SHA_MISMATCH` | `git hash-object`와 고정 blob 비교 | 값 덮어쓰기 말고 새 깨끗한 클론으로 재검 |
| `EDUCATION_NUMERIC_GATE=NOT_ACCEPTED` | `failed_gates` 항목 | 실패 증거 기록, TTL 임계 완화 금지 |
| HTML 빈 화면 | HTML 파일 존재·Windows 브라우저 정책 | JSON 대체, `HTML_BROWSER_FAILED` 표시 |
| 실제 CM/RMW 데이터 지연 | **첫 안전 상태 전이·첫 시간 경계 위반** | 별도 CI 재현·RED→GREEN, 현장 재시도만 반복 금지 |
| “STOP=E-Stop” | `certified_estop=false` | SW STOP과 인증 E-Stop 구별 |
| “G07 Human-aware E2E 완료” | D13/D14 합성·S04 분리 | 원본 세션 구분, 근거 없는 인수 승격 금지 |

## 16. 마지막 점검 — 두 원래 학습 주제를 내 말로 설명하기

- [ ] **Human-aware Safety AMR 통합 MVP 구현:** 센서→브리지→Nav2→Supervisor→Collision Monitor→Base Guard→`/cmd_vel`→odom의 역할을 설명한다.
- [ ] 사람 위험 판단 D13 P/N/U와 D14 LIMITED_REQUEST는 **합성 교육 데이터**이며 G07 사람 검출 E2E 실증이 아님을 설명한다.
- [ ] `load_evidence()`, `review_baseline()`, `negative_counterexamples()`, `validate_g09_g10_separation()`, `ordered_snapshots()`, `run()`의 입력·처리·출력을 설명한다.
- [ ] **통합 안전제어 시나리오 검증 및 결과정리:** D15 18개 테스트, 7장면, Goal/odom 독립 증거, 5 TTL, 5 반례, 보고서를 본인 실행 결과로 제시한다.
- [ ] 원본 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, `first_violation_timestamp=null`, 인증 E-Stop=false, 신규 Gazebo·WSL2 `NOT_RUN`을 구별한다.

**최종 정리:** 이미 구현된 안전 AMR **구조를 학습**하고, 이전 G07 실주행의 공개 **파생 수치**로 제한된 시나리오 검증을 수행했다. 실제 사람 검출 E2E·반복 안전 타이밍·정식 E-Stop 인증까지 새로 완료했다는 뜻은 아니다.

### 참고 자료
[ROS 2 Jazzy Topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html) · [ROS 2 Jazzy QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) · [Nav2 Collision Monitor](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html) · [Nav2 NavigateToPose](https://api.nav2.org/actions/jazzy/navigatetopose.html) · [Gazebo Harmonic ROS 2 연동](https://gazebosim.org/docs/harmonic/ros2_integration/).
