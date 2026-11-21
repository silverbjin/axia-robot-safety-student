# AXIA D13 학생용 데모 가이드 — 16시점·8사례 라이브 Replay

**대상:** 2026-11-25 19:00–23:00 · Python 초심자  
**목표:** 같은 공간을 다른 시간에 지나는 두 이동체의 P/N/U를 설명하고, 10개 공개 테스트를 활용하여 자기 구현을 검증한다. 본 문서는 **합성 오프라인 L0** 전용이며 ROS/Gazebo/Nav2/Goal/모터 명령을 실행하지 않는다.

## 1. 왜 이 데모를 하는가?

복도에서 로봇과 사람이 **같은 지점**을 지나가도 **같은 순간에 겹치는 것은 아닙니다**. 등속도 예측으로 각 시각의 사람 위치를 계산하고, 같은 시각에 로봇 점유 원과 중첩되는지 봅니다. 오늘의 Reachability는 사람의 모든 가능한 경로를 보장하는 일반 도달가능집합이 아니라 **고정 속도 중심 + 원 반경**을 사용하는 교육 모델입니다.

```text
robot_trajectory.csv (16개) ─┐
                              ├─ load_cases() ─ evaluate_case()
cases.json (8개) ─────────────┘                ├─ map/odom 다름 → U
                                               └─ 같음 → classify_time_indexed() [학생 TODO]
                                                             ├─ P / N / U → JSON + CLI
                                                             └─ render_html() → SVG 시간 슬라이더
```

HTML 원의 겹침은 매 시점의 **기하학적 지표**이고, 학생 코드의 최종 P/N/U 및 제어 허가는 아닙니다.

## 2. 클론·환경 확인

```bash
cd ~
git clone --branch main --depth 1 \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-d13-student
cd ~/axia-d13-student
python3 --version
git rev-parse HEAD
ls block_D/day13/fixtures
```

클론 폴더가 이미 있으면 다른 이름을 선택해 과거 제출물을 보존하세요. Ubuntu 24.04/Python 3.12 표준 라이브러리 외에 추가 설치는 없습니다.

## 3. 장면 준비 — ID와 최초 RED

```bash
python3 block_D/day13/run_lab.py --list --out /tmp/axia-d13
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "test_rc=$?"
```

`--list`는 ID 8개를 출력하고 종료합니다. 미완성 TODO인 경우 **예상 출력**: `Ran 10 tests`, `FAILED (failures=2)`, `test_rc=1`. 이는 P/N의 의도된 RED이고, 학생 배포 실패가 아닙니다.

## 4. 단일 P 장면으로 원의 겹침 확인

```bash
python3 block_D/day13/run_lab.py \
  --case P_same_time_overlap --out /tmp/axia-d13
echo "single_case_rc=$?"
```

초기 TODO라면 `D13_CASE=P_same_time_overlap expected=P actual=U status=RED_EXPECTED_TODO`와 `single_case_rc=2`가 예상됩니다. HTML은 생성됩니다. 이 시점의 **화면과 알고리즘 판정이 다를 수 있다는 점**을 먼저 설명하세요.

```bash
explorer.exe "$(wslpath -w /tmp/axia-d13/P_same_time_overlap.html)"
```

WSL2가 아니면 HTML 파일을 일반 브라우저에서 여세요. 슬라이더를 **11.1초**로 옮겨 로봇 x=1.0m, 사람 x=1.0m, 중심거리 0m, 반경 합 0.35m를 확인합니다.

## 5. 전체 8사례와 N 장면 비교

```bash
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
python3 -m json.tool /tmp/axia-d13/d13_results.json | head -60
explorer.exe "$(wslpath -w /tmp/axia-d13/N_same_route_different_time.html)"
```

단일 `--case`는 같은 폴더의 `d13_results.json`을 **한 사례 결과로 덮어씁니다**. 따라서 전체 `--out` 실행을 **마지막**에 수행해 8사례 전체 결과를 남기세요. 초기 TODO 예상: `D13_STUDENT_RESULT=RED_EXPECTED_TODO`, `runner_rc=2`, U 6사례 기대값 일치 + P/N 2사례 불일치. 완료 후 목표: `D13_STUDENT_RESULT=GREEN`, `runner_rc=0`, 8/8.

N 장면의 11.1초: 로봇 x=1.0m, 사람 x=2.0m, 거리 1.0m > 0.35m. **같은 시각**을 비교해야 합니다.

## 6. U 6사례의 최초 무효 원인 설명

| 사례 | 실제 합성 데이터 | 해설 |
|---|---|---|
| `U_stale_track` | now=10.1, observed=9.5 | 관측 나이 0.6초 > 0.5초 |
| `U_future_stamp` | observed=10.2 | 현재보다 미래 |
| `U_low_confidence` | confidence=0.05 | 최소 0.5 미달 |
| `U_frame_mismatch` | robot=map, person=odom | CLI 사전검사 U. TF 변환 아님 |
| `U_missing_last_sample` | 15점 | 마지막 시점 누락 |
| `U_time_jump` | index 7 시간 +0.04초 | 0.2초 시간그리드 위반 |

**한 장면의 겹침으로 즉시 P를 반환하면 안 됩니다.** 경로 뒷부분에 NaN이 존재할 수 있어 먼저 모든 입력을 검증해야 합니다.

## 7. 자기 코드 구현 후 GREEN으로 데모 마감

학생이 `block_D/day13/reachability_student.py`의 TODO 4단계(무결성→시간그리드→등속도 투영→전체 판정)를 작성한 뒤 실행합니다.

```bash
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "test_rc=$?"
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
git diff --name-only
```

**개인 구현 완료 조건:** `Ran 10 tests ... OK`, `test_rc=0`, `D13_STUDENT_RESULT=GREEN`, `runner_rc=0`. 실제 성공 여부는 본인이 캡처한 출력으로 확인합니다. 기존 통합 출고 검사 `verify_student_release.py`는 **원래 미완성 TODO 상태를 기대**하므로, 학습 후 개인 코드 검증에는 사용하지 마세요.

## 8. GUI가 안 될 때 1분 대체 데모

```bash
test -f /tmp/axia-d13/d13_results.json && echo JSON_PRESENT
python3 -m json.tool /tmp/axia-d13/d13_results.json | head -80
```

CLI의 `D13_CASE`, JSON의 `expected`·`actual`·`pass`를 화면 대신 설명합니다. Windows 브라우저 실행이 실패했다면 `HTML_BROWSER_NOT_RUN`으로 표시하세요. Gazebo 창은 처음부터 필요하지 않습니다.

## 9. 발표 순서와 제출

3분 발표: ① 복도 사례(30초) → ② 16시점·P/N 수치(60초) → ③ U 반례(30초) → ④ RED→GREEN 로그와 안전 한계(60초).

제출: `STUDENT_WORKSHEET_KO.md`, 수정한 TODO, unittest, `d13_results.json`, P/N 시각화 캡처 또는 JSON 대체 자료, `git rev-parse HEAD`. **N ≠ 실제 주행 허가, SW Stop ≠ 인증 E-Stop**, 실제 G07 사람 검출/안전 TTL 검증은 이번 데모 범위 밖입니다.
