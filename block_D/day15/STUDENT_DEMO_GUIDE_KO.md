# AXIA D15 — 학생용 38장 연계 데모·Replay 따라하기 (초심자용)

**몰입형 라이브 데모(신규):** [Evidence Theater 학생용 12분 따라하기](STUDENT_EVIDENCE_THEATER_LIVE_GUIDE_KO.md) — 먼저 예측하고 공개 파생 숫자를 확인하며 5개 합성 실패 게이트를 판정하는 단일 오프라인 HTML. 7장면·JSON 2개·원본 HOLD·SW Stop≠인증 E-Stop은 그대로 유지합니다.  

**대상:** Ubuntu 24.04 / WSL2 Ubuntu 24.04, Python 3 / ROS 2 경험이 없어도 진행 가능  
**초심자용 더 자세한 설명:** [D15 16단계 따라하기 핸드북](STUDENT_BEGINNER_HANDS_ON_GUIDE_KO.md)에서 clone·명령 의미·예상 출력·코드 해설·TTL 수치 계산·워크시트·1페이지 보고서·오류 대체를 먼저 읽을 수 있다.  
**공개 범위:** 학생용 공개 데모와 워크시트만 제공한다. 강사용 비공개 정답·원본 rosbag·인수 자료는 포함하지 않는다.  
**학습주제:** ① Human-aware Safety AMR 통합 MVP 구현 *구조 이해* ② 통합 안전제어 시나리오 검증·결과정리  
**실행 범위:** 기존 `jrCIgoGl` 공개 **파생 집계 자료를 오프라인으로 읽는 L0**. 새 ROS 2·Gazebo·Nav2 Goal·Fault Injector·모터 구동을 실행하지 않는다.

## 0. 화면을 보기 전 — 실제·합성 자료는 같은 세션이 아니다

- **실제 과거 G07:** LiDAR→Nav2→Safety Supervisor→Collision Monitor→Base Guard→최종 `/cmd_vel` 및 독립 Goal/odom 기록. 이번 데모는 그 실행의 공개 **파생 JSON**만 읽는다.
- **D13:** 합성 궤적으로 시간·공간 중첩 P/N/U를 판정하는 미완성 학생 TODO.
- **D14:** 합성 P/N/U 입력에서 제한을 요청하는 정책 TODO, 별도 G10 합성 사건 15개.
- **별도 S04:** 실제 Gazebo에서 합성 P/N/U를 기존 안전계층과 연결한 **다른 세션**(공개 CI #43455456960).
- 어느 자료도 `jrCIgoGl`에 **실제 사람 카메라 검출**이 들어갔다는 증거가 아니다. SW Stop은 인증된 E-Stop이 아니다.

### 읽기 전용 시스템·데이터 파이프라인

~~~text
G07 이전 실제 실행:  Gazebo LiDAR -> ROS /scan -> Nav2 및 CM
Nav2 controller -> Supervisor(/cmd_vel_supervised) -> Collision Monitor
Collision Monitor(/cmd_vel_pre_guard) -> Base Guard -> /cmd_vel -> 로봇
                        + Nav2 Action Goal 취소 / odom 독립 증거
                                      |
                      이전 실행의 공개 파생 숫자 JSON (원본 rosbag 아님)
                                      v
    D15 load_evidence() -> review_baseline() -> negative_counterexamples()
                                      v
                  7단계 HTML + d15_evidence_review.json
~~~

## 1. Windows Terminal의 **Ubuntu 탭**에서 GitHub 클론

PowerShell 프롬프트가 아니라 **Ubuntu 터미널**에 다음을 붙여넣는다. 기존 실습 폴더는 삭제하지 않는다. 이름이 충돌하면 `axia-d15-student-2`처럼 바꾼다.

~~~bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-d15-classroom
cd ~/axia-d15-classroom
pwd
python3 --version
git rev-parse HEAD
ls -l block_D/day15/run_lab.py block_D/day15/evidence_review.py
~~~

**예상:** `pwd` 끝이 `axia-d15-classroom`이고, SHA 40자·Python 버전·두 파일 목록이 나온다. 클론 실패 시 인터넷과 저장소 주소를 확인하고, 이미 존재하는 디렉터리에 강제로 덮어쓰지 않는다. **강사 정답 저장소는 클론하지 않는다.**

## 2. 안전한 단위 테스트(기존 18개) 실행

~~~bash
cd ~/axia-d15-classroom
python3 -m unittest discover -s block_D/day15/tests -p 'test_*.py' -v
echo "D15_UNITTEST_RC=$?"
~~~

**기존 배포본 예상:** `Ran 24 tests`, `OK`, `D15_UNITTEST_RC=0`. 이 출력은 **학습용 파생 자료 계약**의 PASS로서 실제 로봇 테스트가 아니다. 실제 실패할 경우 최신 로그의 **첫 AssertionError/ValueError**를 기록하며 임계값을 높이지 않는다.

## 3. 리플레이와 분석 파일 생성

~~~bash
python3 block_D/day15/run_lab.py --out /tmp/axia-d15
echo "D15_RUN_RC=$?"
ls -lh /tmp/axia-d15/
~~~

**기존 배포본 예상 출력(학생 자신의 PC에서 재관측할 것):**

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
D15_RUN_RC=0
~~~

생성물 3개: `d15_evidence_review.json`(7개 스냅샷과 판정), `d15_counterexamples.json`(5개 교육용 변조), `d15_offline_replay.html`(단일 오프라인 화면). **HTML은 실제 Gazebo 영상, 원본 rosbag Replay 또는 사건별 시각 자료가 아니다.**

## 4. 화면 데모 7장면 — 한 장면씩 질문하고 기록하기

Windows WSL2라면 Ubuntu 터미널에서 다음을 실행한다.

~~~bash
explorer.exe "$(wslpath -w /tmp/axia-d15/d15_offline_replay.html)"
~~~

HTML에서 `다음 증거` 버튼을 누르거나 슬라이더를 이동한다. 각 장면을 보고 `block_D/day15/STUDENT_EVIDENCE_WORKSHEET_KO.md` **A 표**에 실제 필드명을 2개 이상 기록한다.

| 순서 | 화면 | 필드·기존 파생값 예시 | 질문 |
|---|---|---|---|
| 1 | CLEAR | `clear_front_m≈2.024826`, `clear_odom_travel_m≈0.120132` | 장애물과 얼마나 떨어졌는가? |
| 2 | SLOW | `slow_front_m≈0.662775`, `slow_supervised_vx_mps≈0.045759`, `slow_final_vx_mps≈0.014534` | Supervisor와 Guard final 속도를 왜 구분할까? |
| 3 | STOP | `stop_front_m≈0.384303`, `stop_final_vx_mps=0` | 0속도 **명령**만으로 실제 정지를 증명할 수 있나? |
| 4 | CANCEL | `goal_cancel_status=5`, 동일 Goal UUID 취소 | Goal 종료와 바퀴 정지가 같은 기록인가? |
| 5 | ODOM_DWELL | `zero_dwell_sec≈1.029446` | 1초 이상 ZERO 유지의 독립적인 의미는? |
| 6 | SAFETY_TTL | Scan `253.822/300ms`, CM·Guard 각각 별도 기준 | 어느 **채널**의 관측 최대값인가? |
| 7 | PNU_AND_SCOPE | `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, `certified_estop=false` | 합성 P/N/U를 실제 G07 사람 인식이라고 말해도 되는가? |

`다음 증거` 버튼으로 이동하는 순서는 **교육 목차**이지 원본 동작의 정밀한 사건 시간순서가 아니다. 학생이 말한 답을 토론한 뒤에 다음 장면을 보여준다.

## 5. 실제 JSON 확인 — 화면이 없어도 같은 수업 가능

~~~bash
python3 -m json.tool /tmp/axia-d15/d15_evidence_review.json | head -90
python3 -m json.tool /tmp/axia-d15/d15_counterexamples.json | head -100
~~~

`first_violation_timestamp: null`은 **원본 집계에 시각이 없어서 알 수 없다**는 정직한 결과다. 없는 시각을 만들어 적지 않는다. HTML이 비어도 JSON으로 계속 진행하고 `HTML_BROWSER_NOT_RUN` 또는 `HTML_BROWSER_FAILED`를 기재한다.

## 6. 실무 반례 5개 — *실제 고장 주입이 아니라 숫자 변조*

`d15_counterexamples.json`에서 각 `case`의 `expected_failed_gate`, `detected`, `not_accepted`, `synthetic_mutation`을 읽고 워크시트 **F 표**를 채운다.

| case | 변조된 값 | 기대 실패 게이트 |
|---|---|---|
| SCAN_301MS | 301ms (기준 300ms) | `scan_gap_max_ms` |
| GUARD_151MS | 151ms (기준 150ms) | `guard_internal_cm_age_max_ms` |
| GOAL_WRONG | Goal 취소 플래그 거짓 | `goal_cancel` |
| DWELL_0_5S | ZERO 유지 0.5s | `odom_zero_dwell` |
| FALSE_CERTIFICATION | 인증 E-Stop 플래그 위조 | `scope_preserved` |

`detected=true`와 `not_accepted=true` **5/5**를 확인한다. fixture 원본을 직접 고쳐서 테스트하지 않는다. 첫 **실패 검증 게이트**는 알 수 있지만, 실제 최초 **안전 상태 전이·타이밍 위반 발생 시각**은 집계값만으로 알 수 없다.

## 7. 코드 읽기 — 입력 → 처리 → 출력

`block_D/day15/run_lab.py`의 `run()`은 `load_evidence()`로 공개 파생 fixture를 읽고, `review_baseline()`으로 원본 출처 SHA·Goal 취소·odom·안전 TTL·HOLD 상태를 검증한다. `validate_g09_g10_separation()`은 D13/D14 합성 출처가 G07 사람 검출과 다르다는 사실을 검사한다. `negative_counterexamples()`은 **복사한 자료**에만 실패 사례를 만들어 원본을 보존한다. 마지막으로 `ordered_snapshots()`가 HTML용 7개 장면을 구성한다.

**실제 G07 런타임 코드 읽기:** `block_B/day07/h01_runtime/ros2_ws/src/axia_safety_supervisor/axia_safety_supervisor/p2_supervisor_node.py`와 `p2_base_guard_node.py`는 **읽기 전용 참조**이다. 전자는 기존 Supervisor FSM·한정된 합성 정책 어댑터, 후자는 `/cmd_vel_pre_guard` 입력을 검사해 최종 `/cmd_vel`을 발행한다. 이 수업에서 이를 실행·수정하거나 보호 STOP을 강제 해제하지 않는다.

## 8. 실패했을 때 — 처음 실패한 경계부터

| 증상 | 첫 확인 | 수업 대체 |
|---|---|---|
| `fatal: destination path ... already exists` | `pwd`·폴더 충돌 | 다른 새 클론 이름 사용 |
| `ModuleNotFoundError` | 저장소 루트 `pwd` | `cd ~/axia-d15-classroom` 뒤 재실행 |
| `D15_DERIVED_FIXTURE_BLOB_SHA_MISMATCH` | 원본 파일의 SHA 변경 | 새 정상 클론, 원본 덮어쓰기·임계 완화 금지 |
| `EDUCATION_NUMERIC_GATE=NOT_ACCEPTED` | `failed_gates` 최초 항목 | 로컬 자료 비교·강사에게 기록 제출 |
| HTML 브라우저 실패 | 파일 존재·Windows `explorer.exe` | `python3 -m json.tool` 대체; `NOT_RUN`/`FAILED` 기록 |
| 수신 주기 불안정이 실제 문제로 보고됨 | 실물 원본 센서→RMW→Observer→Guard 첫 위반 | D15 L0와 분리하여 CI 회귀 먼저 |
| `SW Stop=E-Stop` 주장 | `certified_estop=false` | 소프트웨어 보호 정지와 인증 HW E-Stop 구분 |

## 9. 제출 방법·채점 전 확인

1. 본인이 실제 실행한 `git rev-parse HEAD`, `python3 --version`, unittest 로그(24/24 또는 실패 원본)를 기록한다.
2. `/tmp/axia-d15/d15_evidence_review.json`과 `d15_counterexamples.json` 파일을 보존한다.
3. `STUDENT_EVIDENCE_WORKSHEET_KO.md`의 **A~H**를 채운다. 숫자마다 출처와 **그 숫자로 주장할 수 없는 것**을 한 문장 적는다.
4. 팀 발표 **3~5분**: CLEAR→SLOW→STOP, Goal/odom, TTL, 반례, 합성/실물 출처와 원본 HOLD 순서로 설명한다.
5. `FINAL_EVALUATION_RUBRIC_KO.md` 100점 항목을 확인한다. 정식 안전 인수나 신규 실물 Gazebo 성공으로 주장하면 안 된다.

참고: [ROS 2 Jazzy QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) · [Nav2 Collision Monitor](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html) · [Nav2 NavigateToPose](https://api.nav2.org/actions/jazzy/navigatetopose.html).
