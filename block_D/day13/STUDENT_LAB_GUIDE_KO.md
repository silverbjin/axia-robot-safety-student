# AXIA D13 학생용 상세 실습 가이드 — 시간별 Reachability와 충돌 판정

**일시:** 2026-11-25(수), 19:00–23:00 (교육 220분 + 휴식 20분)  
**실행 환경:** Ubuntu 24.04 / WSL2 Ubuntu 24.04, Python 3.12 표준 라이브러리, Git. ROS 2·Gazebo·Nav2·pip 설치 불필요.  
**학습 범위:** (1) Reachability 기반 사람 이동 가능 영역 계산 구조 이해 (2) 공간예측 및 경로 충돌 판정 실습. 합성 오프라인 L0만 수행하며 /cmd_vel, Nav2 Goal, SW 정지, 인증 E-Stop은 실행하지 않습니다.

## 0. 도달 목표와 강의 시간표

수업 후 학생은 ① 16개 시점·8개 합성 사례의 의미를 설명하고 ② 사람의 등속도 예상 위치와 로봇 원의 겹침을 계산하고 ③ 무효 관측을 U로 분류하고 ④ 학생 공개 테스트 10개를 자신의 코드로 GREEN 처리할 수 있어야 합니다.

| 시각 | 활동 | 증거 |
|---|---|---|
| 19:00–19:30 | 복도의 두 이동체·P/N/U 스토리 | 예상판정 |
| 19:30–20:10 | Reachability·시스템 개념도·데이터 파이프라인·수치 | 워크시트 |
| 20:10–20:20 | 휴식 | |
| 20:20–21:20 | RED→GREEN TODO 개발 | unittest |
| 21:20–21:30 | 휴식 | |
| 21:30–22:30 | 8사례 HTML Replay·U 반례 | 결과 JSON |
| 22:30–23:00 | 디버깅·발표·제출 | 평가표 |

## 1. 저장소 클론 — 새 폴더에서 처음부터 실행

터미널 1개에서 아래 명령을 순서대로 입력합니다. 기존 실습 폴더는 삭제·덮어쓰지 않습니다.

```bash
cd ~
git --version
python3 --version
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  axia-d13-student
cd ~/axia-d13-student
pwd
git rev-parse HEAD
ls block_D/day13
```

`axia-d13-student`가 이미 존재하면 새 디렉터리 이름을 정하고 해당 디렉터리로 이동하십시오. `pwd`가 저장소 루트를 가리켜야 합니다. 공지한 배포 SHA와 `git rev-parse HEAD`를 비교하세요.

## 2. 실습 파일과 역할 먼저 확인

| 경로 | 역할·수정 여부 |
|---|---|
| `block_D/day13/fixtures/robot_trajectory.csv` | 16개 로봇 위치, 읽기 전용 |
| `block_D/day13/fixtures/cases.json` | 사람 관측·8개 사례, 읽기 전용 |
| `block_D/day13/reachability_student.py` | **학생이 수정할 유일한 TODO 파일** |
| `block_D/day13/run_lab.py` | CLI·JSON·HTML 생성, 수정 금지 |
| `block_D/day13/tests/test_d13_public.py` | 판정/무결성 검증, 수정 금지 |
| `block_D/day13/tests/test_d13_runner.py` | fixture·프레임·HTML 검증, 수정 금지 |
| `block_D/day13/STUDENT_DEMO_GUIDE_KO.md` | 발표용 시연·실패 대체 가이드 |
| `block_D/day13/STUDENT_WORKSHEET_KO.md` | 손계산 및 제출지 |

## 3. 동작 구조와 Reachability 의미

**실제 로봇 개념 구조(이번 실행에서는 NOT_RUN):** 센서 → 사람 추적 → 위치·속도 추정 → 미래 점유영역 예측 → 위험 정책 → 별도 Supervisor/CM/Guard 보호.

**실제로 실행하는 D13 데이터 파이프라인:**

```text
robot_trajectory.csv (16시점) ─┐
                                ├─ load_cases() ─ evaluate_case()
cases.json (8사례) ──────────────┘                     │
                                           ┌ frame 다름 → U
                                           └ frame 같음 → classify_time_indexed()
                                                              │
                                                  P/N/U → CLI/JSON/HTML
test_d13_public.py + test_d13_runner.py ─────── 별도 unittest 검증 경로
```

일반 Reachability는 미래에 **도달 가능한 위치들의 집합**입니다. D13은 그 일반 문제를 전부 풀지 않고, **등속도 중심 위치 + 고정 원형 반경**으로 표현한 교육용 축약 모델입니다. 가속·급회전·불확실성 확장이나 실제 안전 보증을 구현하지 않습니다. `evaluate_case()`의 frame mismatch는 **교육용 CLI 사전검사 U**이며, 원본 G09 오라클이 TF를 변환하는 것은 아닙니다.

## 4. 수치 예제 — 필기 후 fixture 대조

`now_sec=10.1`, `dt_sec=0.2`, `horizon_sec=3.0`이므로 `3.0/0.2 + 1 = 16`개(10.1, 10.3, …, 13.1초). **0.2초는 예측 샘플 간격이며 실제 LiDAR 발행/수신 주기가 아닙니다.**

```text
person_x(t) = x + vx × (t - observed_sec)
person_y(t) = y + vy × (t - observed_sec)
d(t) = hypot(robot_x(t)-person_x(t), robot_y(t)-person_y(t))
겹침 = d(t) <= robot_radius(t) + person_radius
```

- P 예: 사람 관측 `x=2.1m`, `vx=-1m/s`, `observed_sec=10.0s`. 시각 `11.1s`의 사람 x=1.0m, 로봇 x=1.0m ⇒ 중심 거리 **0.0m** ≤ 반경 합 **0.35m**.
- N 예: 사람 관측 `x=0.9m`, `vx=+1m/s`. 같은 시각의 사람 x=2.0m, 로봇 x=1.0m ⇒ **1.0m > 0.35m**. 최종 N은 해당 시점 하나가 아닌 **전체 16개 유효 시점 비중첩**을 확인한 결과입니다.
- U 예: 지금 10.1초인데 마지막 관측 9.5초면 나이 **0.6초 > 0.5초**. 관측 10.2초는 미래. confidence 0.05는 최소 0.5 미만입니다.

`P`는 전 구간 검증 후 하나 이상 동시간 중첩, `N`은 전 구간 유효·비중첩, `U`는 무효·불확실성입니다. N을 실제 주행 허가로 사용하지 않습니다.

## 5. 최초 RED 확인 (실습 시작 시 의도된 실패)

```bash
cd ~/axia-d13-student
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
```

배포 당시 TODO 기준의 **예상 출력 발췌**:

```text
test_N_same_path_different_time ... FAIL
test_P_same_time_overlap ... FAIL
Ran 10 tests
FAILED (failures=2)
student_tests_rc=1
```

10개는 테스트 메서드 개수입니다. 처음 코드가 `return "U"`이므로 P와 N의 실패가 정상입니다. 강사 정답을 공개 저장소에 복사하여 GREEN으로 만들지 않습니다.

## 6. TODO 4단계 구현 — 한 파일만 수정

```bash
nano block_D/day13/reachability_student.py
```

함수 이름과 매개변수는 그대로 두고 내부를 구현합니다.

1. **입력 무결성:** 숫자 타입·유한성, `dt_sec/horizon_sec/stale_sec > 0`, confidence 범위, 사람의 반경, `0 <= now_sec - observed_sec <= stale_sec`를 검사합니다. invalid라면 U.
2. **로봇 경로 16개:** `count = round(horizon_sec/dt_sec)+1`, 모든 `t_sec = now_sec + index*dt_sec`, x/y/radius 유효성·비음수 반경. 시간축·길이 불일치면 U.
3. **같은 시각 사람 투영:** 각 로봇 `t_sec`에서 사람의 x/y를 등속도 투영하고 `math.hypot` 거리와 반경 합을 비교합니다.
4. **최종 P/N:** 겹침을 발견해도 즉시 P로 반환하지 말고 **마지막 샘플까지** 검증합니다. 도중에 NaN이 있으면 U, 모든 샘플이 유효하면 겹침 여부로 P/N.

아래는 **의사코드**입니다. 학생용 완성 구현이 아닙니다.

```python
# if 입력/사람 관측 invalid: return "U"
# for index, robot_point in enumerate(robot_trajectory):
#     if 해당 시점 invalid: return "U"
#     # 같은 t의 human_x/human_y를 계산하고 겹침 여부 기록
# # 전 구간 유효 -> overlap이면 "P", 아니면 "N"
```

## 7. 8사례 실행과 예상 결과 확인

```bash
python3 block_D/day13/run_lab.py --list --out /tmp/axia-d13
python3 block_D/day13/run_lab.py --case P_same_time_overlap --out /tmp/axia-d13
echo "single_rc=$?"
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
python3 -m json.tool /tmp/axia-d13/d13_results.json | head -55
ls -lh /tmp/axia-d13
```

`--list`는 **사례 이름만 출력하고 HTML을 만들지 않습니다**. `--case` 실행은 결과 JSON을 해당 한 사례 결과로 갱신하므로, **전체 실행을 마지막에** 해야 8개 결과가 남습니다.

| 사례 ID | 기대 결과 | 확인할 첫 조건 |
|---|---|---|
| `P_same_time_overlap` | P | 같은 시각 중심거리 0m |
| `N_same_route_different_time` | N | 같은 시각 중심거리 1m, 전 구간 비중첩 |
| `U_stale_track` | U | 관측 age 0.6초 |
| `U_future_stamp` | U | 관측 10.2 > 현재 10.1 |
| `U_low_confidence` | U | 0.05 < 0.5 |
| `U_frame_mismatch` | U | map과 odom 다름(어댑터 U) |
| `U_missing_last_sample` | U | 15개 경로 점 |
| `U_time_jump` | U | 시간 index 7에서 +0.04초 |

**초기 TODO 예상:** `D13_STUDENT_RESULT=RED_EXPECTED_TODO`, `runner_rc=2`, 8사례 중 P/N 2개 불일치, U 6개 일치. 그래도 HTML 8개와 JSON은 생성됩니다. **학생 구현 완료 목표:** unittest `Ran 10 tests ... OK` (exit 0), runner `D13_STUDENT_RESULT=GREEN` (exit 0), 8/8 일치. 학생 개인 GREEN은 제출한 실제 로그를 근거로 판단합니다.

## 8. HTML 데모와 화면 불능 대체

WSL2에서 Windows 브라우저 이용 시:

```bash
explorer.exe "$(wslpath -w /tmp/axia-d13/P_same_time_overlap.html)"
explorer.exe "$(wslpath -w /tmp/axia-d13/N_same_route_different_time.html)"
```

슬라이더를 11.1초로 맞추어 로봇 원(파랑)과 사람 원(빨강)을 비교합니다. **화면의 기하학적 겹침 YES**는 해당 시점의 계산이며 **학생 알고리즘의 actual=P를 증명하지 않습니다.** 브라우저가 안 열리면 `python3 -m json.tool /tmp/axia-d13/d13_results.json`과 CLI 사례 출력을 읽고 GUI 검증을 NOT_RUN으로 표시합니다.

## 9. 오류가 났을 때

| 현상 | 최초 확인 | 대체/수정 |
|---|---|---|
| `ModuleNotFoundError` | `pwd`가 클론 루트인가 | `cd ~/axia-d13-student` |
| P/N이 U | TODO 미완성/유효성 조건 | now/observed/NaN·시간축 점검 |
| N인데 P | 공간만 보고 시간 무시 | 동일 `t_sec`끼리 비교 |
| U인데 N | stale·future·confidence·끝점 누락 | 최초 무효 timestamp부터 추적 |
| 초반 overlap 발견 후 뒤에 NaN | 조기 return P | 전체 16개 유효성 검사 |
| HTML 빈 화면 | 파일 존재·로컬 브라우저 JS | CLI·JSON 분석으로 진행 |
| Gazebo가 켜지지 않음 | 이번 D13에서 실행 대상 아님 | 오류로 분류하지 않음 |

## 10. 제출과 평가 (100점)

`STUDENT_WORKSHEET_KO.md`, 수정한 `reachability_student.py`, unittest 로그, `d13_results.json`, 대표 P/N/U 화면 또는 JSON 대체 해설, `git diff --name-only`, `git rev-parse HEAD`를 제출합니다. 25점 입력 유효성, 30점 동시간 P/N, 20점 U 반례, 15점 시각화·표, 10점 안전 한계 설명입니다.

**안전 경계:** D13 P/N/U는 실제 G07 Owner 사람 검출이나 로봇 정지 증거가 아닙니다. SW Stop과 인증 하드웨어 E-Stop은 별개입니다.
