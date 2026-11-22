# AXIA D15 — Evidence Theater 몰입형 라이브 데모 사용 가이드 (학생용)

**학습 목표:** 이미 구현된 Human-aware Safety AMR의 구성 요소를 설명하고, 기존 G07 실주행의 공개 파생 증거에서 CLEAR/SLOW/STOP·Goal/odom·안전 TTL을 독립적으로 해석한다.  
**범위:** 오프라인 HTML에서 **교육용 예측·증거 공개·합성 Fault Challenge**. 오늘 신규 ROS 2/Gazebo/Nav2 Goal·실제 사람 검출 E2E·Fault Injector는 실행하지 않는다.

## 1. 설치: Windows Terminal → Ubuntu 24.04 탭

Python 3·Git만 필요하다. 이미 저장소가 있다면 기존 파일을 덮어쓰거나 삭제하지 말고 다른 이름으로 클론한다.

~~~bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d15-theater
cd ~/axia-d15-theater
pwd
python3 --version
git rev-parse HEAD
git hash-object block_D/day15/fixtures/jrcigogl_public_derived.json
~~~

고정된 공개 **파생 fixture Git blob**의 정상 ID: `ae7d594b5452d96cc8802bc53bc8ad578fe99fb7`. SHA가 다르면 강제로 맞추지 않고 다른 깨끗한 클론에서 확인한다.

## 2. 테스트·실행·화면 열기 — 터미널 한 세션

~~~bash
cd ~/axia-d15-theater
python3 -m unittest discover -s block_D/day15/tests -p 'test_*.py' -v
python3 block_D/day15/run_lab.py --out /tmp/axia-d15
ls -lh /tmp/axia-d15/
explorer.exe "$(wslpath -w /tmp/axia-d15/d15_offline_replay.html)"
~~~

**기대 출력:** D15 24개 unittest 모두 `OK`(기존 18개 + Theater 6개), `D15_EDUCATION_NUMERIC_GATE=EDUCATION_NUMERIC_ACCEPTED`, `D15_SYNTHETIC_NEGATIVE_DETECTION=5/5`, `D15_G09_G10_SOURCE_SEPARATE=True`, `D15_REPLAY_SCOPE=AGGREGATED_PUBLIC_EVIDENCE_ONLY_NO_NEW_ROS_GAZEBO`.

생성물은 이전과 **동일한 세 파일**이다.

- `/tmp/axia-d15/d15_offline_replay.html` — 업그레이드된 EVIDENCE THEATER.
- `/tmp/axia-d15/d15_evidence_review.json` — 7단계 및 원본 판정, TTL, 출처.
- `/tmp/axia-d15/d15_counterexamples.json` — 실패 게이트 5개, 전부 합성 수치 변조.

**Windows 없이 Ubuntu만 사용 중이면** 파일 관리자로 HTML을 열거나 `python3 -m json.tool`로 JSON 분석을 대신한다. 브라우저를 열지 못했다면 `HTML_BROWSER_FAILED` 또는 `HTML_BROWSER_NOT_RUN`으로 기록한다.

## 3. 수업 중 화면 이용 방법

1. **상단의 노란 범위 안내를 먼저 읽는다.** G07 이전 실주행 공개 파생 수치와 D13/D14 합성 입력은 다른 실행이다. 교육용 도형은 실제 Gazebo 영상도 시간순 로봇 궤적도 아니다.
2. **01 로봇·장애물 도식:** 수치는 처음 숨겨져 있다. 장애물과 로봇 그림은 개념도이므로 실제 위치·가속·시간을 추측하지 않는다.
3. **02 학생 예측:** CLEAR, SLOW, STOP, CANCEL, ODOM_DWELL, SAFETY_TTL, PNU_AND_SCOPE 중 순서대로 이동한다. 질문의 선택지를 먼저 고른 뒤 **증거 공개** 버튼을 누른다. 예상 답과 파생 수치를 함께 확인한다.
4. **거리·속도 계기판:** CLEAR/SLOW/STOP일 때만 해당 거리 수치를 표시하고 SLOW/STOP일 때만 해당 최종 명령 속도를 보인다. 다른 단계에서는 **새 거리 측정 없음**이라고 표시한다. 임의 보간한 이동이나 실시간 속도는 없다.
5. **03 FAULT CHALLENGE:** `SCAN_301MS` 등 5개 사례 중 하나를 선택한 뒤 `실패 게이트`를 예측한다. `판정`을 눌러 `expected_failed_gate`, `detected` 및 `not_accepted`를 확인한다. **원본 fixture, 임계값 또는 로봇에 변화가 생기지 않는다.**
6. **04 안전 범위:** EDUCATION_NUMERIC_ACCEPTED와 원본 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`는 동시에 참이다. `first_violation_timestamp=null`은 공개 집계에 원본 사건 시각이 없다는 뜻이다.
7. **제출:** [STUDENT_EVIDENCE_WORKSHEET_KO.md](STUDENT_EVIDENCE_WORKSHEET_KO.md)의 A~H 작성과 JSON 2개 제출. [상세 초심자 핸드북](STUDENT_BEGINNER_HANDS_ON_GUIDE_KO.md) 및 [100점 루브릭](FINAL_EVALUATION_RUBRIC_KO.md) 참조.

**상호작용:** 7개 단계 버튼, 이전/다음, 슬라이더로 이동. 키보드 ←/→는 입력 선택창에 포커스가 없을 때 단계 이동에 사용한다. 자동 재생이나 실제 이벤트 시간 표시 기능은 의도적으로 넣지 않았다.

## 4. 실습·발문: 12분 대화형 데모

| 시간 | 강사 질문 | 학생이 확인할 내용 |
|---|---|---|
| 0~2분 | “어떤 기록이 로봇의 안전 정지를 증명하나?” | 센서/명령/Goal/odom 출처 분리 |
| 2~4분 | “장애물 0.66m일 때 무엇을 볼까?” | SLOW: 0.045759m/s supervised vs 0.014534m/s final |
| 4~6분 | “Goal 취소와 정지는 같은가?” | CANCELED(5), final ZERO, odom dwell ≥1초 독립 확인 |
| 6~9분 | “Scan 301ms, Guard age 151ms이면?” | 5개 합성 반례가 올바른 게이트에서 실패 |
| 9~11분 | “P/N/U가 G07 실제 사람 검출인가?” | D13/D14 synthetic, 별도 S04, G07 이전 파생 구별 |
| 11~12분 | “숫자 합격인데 원본 HOLD인 이유는?” | UI·반복 안정성·형식 안전 인수 미검증 |

## 5. 문제 발생 시 JSON 대체

~~~bash
cd ~/axia-d15-theater
python3 -m json.tool /tmp/axia-d15/d15_evidence_review.json | head -90
python3 -m json.tool /tmp/axia-d15/d15_counterexamples.json | head -110
~~~

- **HTML 안 열림:** JSON 두 파일이 정상인지 먼저 확인하고 수업은 계속한다.
- **`ModuleNotFoundError`:** 저장소 루트에서 위 명령을 그대로 재실행한다.
- **`D15_DERIVED_FIXTURE_BLOB_SHA_MISMATCH`:** 변경된 자료로 PASS를 꾸미지 않고 새 클론의 원본을 확인한다.
- **테스트 실패:** 마지막 exit code보다 **최초 실패 테스트와 데이터 경계**를 기록한다. 신규 실제 Gazebo/WSL2 결함이라면 CI 재현 가능한 영역부터 RED→GREEN한다.
- **화면 1920×1080:** 브라우저 F11로 전체화면, 확대 100%, 교육생에게 앞뒤로 7장면 이동을 요청한다. 글씨가 잘리면 브라우저 확대를 90%로 바꿔 비교한다.

**제출 판정 경계:** 이 실습은 *교육용 오프라인 L0*이다. 실제 ROS/Gazebo/Nav2 제어, 원본 rosbag의 시간순 재생, 실제 사람 인식·사람 회피 통합 인수, 인증 E-Stop의 성공을 주장하면 안 된다.
