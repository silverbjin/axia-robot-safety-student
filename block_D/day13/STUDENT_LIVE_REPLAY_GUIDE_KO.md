# AXIA D13 — TIME × SPACE Live Replay 초심자용 실행·참여 가이드

**대상:** ROS·Python 입문자 포함 / 2026-11-25(수) 19:00–23:00 수업의 S07–S09, S17–S21  
**실행 범위:** 합성 데이터 기반 오프라인 L0. ROS 2, Gazebo, Nav2 Goal, /cmd_vel, 실제 안전 정지, 인증 E-Stop **미실행**.  
**학습 목표:** 경로가 교차한다는 사실과 **같은 시각의 점유원 겹침**을 구분하고, P/N/U와 불확실 입력의 최초 위반 이유를 말로 설명한다.

## 0. 무엇이 새로 생겼나요?

기존 `run_lab.py`는 사례별 HTML 8개와 `d13_results.json`을 생성합니다. 새 `live_replay.py`는 **동일한 8개 fixture와 수정하지 않은 학생 판정 함수를 재사용**하여, 강의 화면 1장 `axia_d13_live_replay.html`과 데이터 증거 `live_replay_manifest.json`을 만듭니다. 외부 URL·CDN·설치형 웹서버는 필요하지 않습니다.

```text
robot_trajectory.csv (16시점) ─┐
                               ├─ 기존 load_cases() ── 기존 evaluate_case()
cases.json (P1 N1 U6) ─────────┘                             │
                                             학생 TODO의 actual P/N/U
                                                           │
                              live_replay.py ────────────────┘
                               ├─ live_replay_manifest.json (입력·기대/실제값)
                               └─ axia_d13_live_replay.html
                                   ├─ 장면 A/B 동기 재생
                                   ├─ 학생 투표 → 기대값·실제값 별도 공개
                                   └─ U 6개 fixture 입력 최초 위반 설명
```

**중요:** Live Replay가 예상 결과의 P/N/U를 계산하는 새 알고리즘이 아닙니다. 기존 실행기와 학생 TODO의 값을 **읽어 표시하는 보조 화면**입니다. 정답 레이블을 가린 후 학생이 먼저 판단하도록 구성했습니다.

## 1. 내 컴퓨터에 공개 Student 저장소 클론

WSL2 Ubuntu 24.04의 터미널을 엽니다. 기존 과제를 지우거나 덮어쓰지 않습니다. `git`이나 `python3` 명령이 없으면 강사에게 개발환경 설치를 요청합니다.

```bash
cd ~
git --version
python3 --version
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d13-student-live
cd ~/axia-d13-student-live
pwd
git rev-parse HEAD
ls block_D/day13/live_replay*
```

**기대:** 저장소 루트가 `~/axia-d13-student-live`이며 `live_replay.py`와 `live_replay_template.html` 두 파일이 보입니다. 위 폴더가 이미 있다면 다른 이름으로 클론하고 이후 명령의 `cd` 경로를 맞춥니다. `git rev-parse HEAD`는 학습자의 버전을 기록하기 위한 것입니다.

## 2. 새 HTML 파일 만들기 — 생성 명령은 단 한 줄

```bash
cd ~/axia-d13-student-live
python3 block_D/day13/live_replay.py --out /tmp/axia-d13-live
echo "live_generator_rc=$?"
ls -lh /tmp/axia-d13-live/
```

**예상 출력(배포 초기 TODO 기준):**

```text
D13_LIVE_REPLAY_L0_PASS cases=8 timepoints=16 expected=P1_N1_U6
D13_LIVE_LEARNER_GREEN=0
D13_LIVE_HTML=/tmp/axia-d13-live/axia_d13_live_replay.html
D13_LIVE_MANIFEST=/tmp/axia-d13-live/live_replay_manifest.json
D13_LIVE_SCOPE=OFFLINE_SYNTHETIC_L0_NO_ROBOT_CONTROL NO_ROS_GAZEBO_GOAL
live_generator_rc=0
```

생성기 종료코드 0은 **HTML·JSON 파일을 생성했다는 의미**이며 학생 알고리즘이 GREEN이라는 뜻이 아닙니다. 초기 학생 TODO는 P/N 판정이 미완성이므로 `D13_LIVE_LEARNER_GREEN=0`입니다. 다른 값이 나오면 자신의 코드 변경 여부부터 확인합니다.

**파일 확인:** `/tmp/axia-d13-live/axia_d13_live_replay.html` (독립 로컬 화면), `/tmp/axia-d13-live/live_replay_manifest.json` (검증 가능한 입력 요약). 기존 `run_lab.py`가 생성하는 `d13_results.json`이나 8개 HTML 파일을 대체하지 않습니다.

## 3. 브라우저에서 열기

WSL2 터미널에서는 다음 한 줄을 입력합니다.

```bash
explorer.exe "$(wslpath -w /tmp/axia-d13-live/axia_d13_live_replay.html)"
```

Windows 탐색기에서 파일이 열리면 Edge 또는 Chrome 등 HTML을 지원하는 브라우저를 선택하세요. Ubuntu 데스크톱이라면 파일을 일반 브라우저에서 직접 열어도 됩니다. 이 파일은 인터넷 접속이나 ROS 2 실행이 필요하지 않습니다.

강의실 1920×1080 프로젝터에서는 브라우저 최대화 후 `F11` 전체 화면 모드를 활용합니다. 창 폭이 좁으면 두 장면이 위아래로 재배열되며, 그때는 브라우저 전체화면으로 비교하세요. 현재 환경에서 Windows 브라우저 동작은 사용자 WSL2에서 확인해야 하는 **현장 검증**입니다.

## 4. 재생 버튼과 조작 방법

| 버튼·항목 | 기능 | 학생이 확인할 것 |
|---|---|---|
| `▶ 자동 재생` | 0.65초마다 시간점 한 칸 전진 | 파란 로봇과 빨간 사람이 서로 다른 속도로 이동 |
| `Ⅱ 일시정지` | 현재 시각에서 멈춤 | 두 장면을 **같은 시간**에 비교 |
| `← 이전 시점` / `다음 시점 →` | 0.2초씩 이동 | 16개 점으로 이루어진 예측 시간표 |
| `↺ 처음부터` | 10.1초로 돌아감 | 모든 샘플을 다시 비교 |
| `★ 11.1초 비교` | 여섯 번째 점(인덱스 5)으로 이동 | 두 원의 중심거리 0.0m/1.0m |
| 시간 슬라이더 | 원하는 인덱스를 지정 | 10.1부터 13.1초, **16개 시점** |

**기억할 수치:** 반경 합 `0.15 + 0.20 = 0.35 m`. 장면 A의 11.1초 중심거리는 `0.0 m`, 장면 B는 `1.0 m`입니다. 기하학적 겹침은 `거리 <= 반경 합`으로 판단하되 **이것만으로 최종 N을 결정하지 않습니다**. 나머지 시점의 데이터까지 검증해야 합니다.

두 장면은 좌표 축척을 공유하고 모든 원형 점유영역이 보이도록 화면 범위를 계산합니다. 화면의 YES/NO는 **그 시각의 기하학적 원 비교**입니다.

## 5. 먼저 투표하고 정답 공개 — 학생에게 꼭 시키는 순서

1. 강사가 먼저 `▶ 자동 재생`으로 P/N 장면을 보여 줍니다. 학생은 무엇이 위험한지 토론합니다.
2. 11.1초에서 멈추고 표의 계산 결과를 비교합니다.
3. **장면 A 예상 결과**와 **장면 B 예상 결과**를 각각 `P` / `N` / `U` 중 선택합니다.
4. `예측 제출 · 정답 공개`를 누릅니다.
5. 출력된 **내 예상 / fixture 기대 / 학생 코드 actual**의 세 값을 따로 읽습니다.
6. `답 가리기`로 다시 처음의 교육 퀴즈 상태로 돌아갑니다.

**P/N/U의 뜻:** P는 전체 입력이 유효하면서 적어도 하나의 **동일 시각** 점유원이 중첩, N은 전체 입력이 유효하고 모든 시점에서 비중첩, U는 관측값·시간격자·프레임 등에 결함이 있어 판단 불가입니다.

첫 실습에서 fixture 기대값은 A=P, B=N이지만 학생 함수의 실제 판정은 둘 다 U일 수 있습니다. **그림에서 겹친다는 것과 내가 작성한 판단 함수가 P를 반환한다는 것은 다릅니다.** 이 차이를 말로 설명해야 합니다.

## 6. U 사건 조사 — 여섯 가지 최초 입력 위반

`② U 사건 조사`의 선택 메뉴에서 한 사례를 고르면 **교육용 fixture 입력의 최초 위반**이 나타납니다. 중요한 제한: 이것은 발표용 설명이며 **학생 알고리즘이 해당 오류를 실제로 발견했다고 주장하지 않습니다.**

| 사례 | 첫 입력 결함 | 교실에서 할 질문 |
|---|---|---|
| `U_stale_track` | 현재 10.1, 관측 9.5 → 나이 **0.6초 > 0.5초** | “오래된 관측을 N으로 바꾸면?” |
| `U_future_stamp` | 관측 10.2 > 현재 10.1 | “미래 데이터를 지금의 사실로 써도 될까?” |
| `U_low_confidence` | confidence **0.05 < 0.50** | “정확하지 않은 추적이라면?” |
| `U_frame_mismatch` | 로봇 `map` / 사람 `odom` | “좌표 원점을 맞추지 않고 빼도 될까?” |
| `U_missing_last_sample` | **15개** 점 / 필요 16개 | “마지막 데이터를 확인하지 않으면?” |
| `U_time_jump` | index 7 시각 **11.54초** / 기대 11.50초 | “최초 타이밍 위반은 언제?” |

`frame mismatch`는 기존 `evaluate_case()`의 교육용 어댑터가 U로 처리합니다. TF 변환을 수행하는 기능이 아닙니다.

## 7. 실제 학생 코드 GREEN 여부는 별도 검사

Live Replay의 화면이 잘 열렸다고 학생 TODO가 완료된 것은 아닙니다. 학생은 **실습 가이드에서 안내한 TODO 네 단계를 직접 구현**한 뒤 아래 명령을 실행합니다.

```bash
cd ~/axia-d13-student-live
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "original_runner_rc=$?"
```

**초기 Starter 예상:** `Ran 10 tests`, `FAILED (failures=2)`, 테스트 rc=1, 기존 runner rc=2, `D13_STUDENT_RESULT=RED_EXPECTED_TODO`. 학습 완료 목표는 본인 코드에서 10/10 unittest OK + 기존 runner 8/8 GREEN, 각각 종료코드 0입니다.

학생이 코드를 고쳤다면 **다시** `python3 block_D/day13/live_replay.py --out /tmp/axia-d13-live`를 실행하고 브라우저에서 새로고침해야 실제 학생 verdict가 화면에 반영됩니다. UI에서 답을 고르는 동작은 학생 코드 파일을 수정하지 않습니다.

## 8. 장애 상황에서도 수업을 계속하는 방법

| 증상 | 최초 확인 | 조치 |
|---|---|---|
| `ModuleNotFoundError` | `pwd`, 파일 경로 | 저장소 루트에서 실행 |
| `--out` 경로 권한 오류 | `ls -ld /tmp` | 본인 홈의 새 출력 폴더 사용 (`--out "$HOME/axia-d13-live-output"`) |
| 화면이 열리지 않음 | HTML 생성 확인 | 기존 사례별 HTML 또는 `json.tool`로 대체 |
| 버튼이 안 움직임 | 브라우저에서 JavaScript 허용 여부 | 다른 로컬 브라우저 사용, 그래도 안 되면 기존 슬라이더 화면으로 복귀 |
| 학생 실제값이 U | 학생 TODO 미완성 가능성 | 공개 unittest와 기존 runner 로그 확인 |
| U 사례 표시가 P처럼 보임 | U 선택은 fixture 진단, P/N 화면은 별개 | 예상/실제/순간 기하 3층 구분 |
| “ROS topic이 없다” | 이 실습은 파일 기반 오프라인 | 정상. Gazebo·Nav2 실행하지 않음 |

**60초 대체 명령:**

```bash
python3 -m json.tool /tmp/axia-d13-live/live_replay_manifest.json | head -90
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "original_runner_rc=$?"
python3 -m json.tool /tmp/axia-d13/d13_results.json | head -80
```

브라우저 화면을 실제 확인하지 못했다면 기록에 `HTML_BROWSER_NOT_RUN`을 적습니다. CI의 정적 HTML 생성 성공은 현장의 GUI 성공과 다릅니다.

## 9. 제출하는 증거와 평가

- 내 Git SHA: `git rev-parse HEAD`
- 코드 수정 목록: `git diff --name-only` (TODO만 수정했는지)
- 기존 공개 unittest 10개 실제 출력, 기존 `d13_results.json` 8사례
- Live Replay 사용 사진/화면 캡처 또는 GUI NOT_RUN + JSON 대체
- **11.1초 P/N 중심거리 0.0m와 1.0m 계산 근거**, U 첫 위반 사례 하나
- 교육용 분류/실제 로봇 SW 정지/인증 E-Stop의 차이 해설

**안전 경계:** 이 화면은 교육용 모션 표현입니다. 실제 ROS/Gazebo 센서, Supervisor/Collision Monitor/Guard의 주기·TTL, Nav2 또는 인증 하드웨어 E-Stop을 새로 실행·인수하지 않습니다. P/N/U로 로봇 동작을 명령하지 않습니다.
