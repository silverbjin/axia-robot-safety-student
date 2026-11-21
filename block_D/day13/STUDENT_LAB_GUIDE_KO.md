# AXIA BLOCK_D D13 — 움직이는 사람을 피할 수 있을까?

**수업:** 2026-11-25(수) 19:00~23:00 / 4시간 실습  
**환경:** Ubuntu 24.04 / Python 3.12 표준 라이브러리. ROS 2 없이도 완료할 수 있습니다.  
**실습의 출처:** Instructor P3 G09 `p3_oracles.classify_time_indexed` (staging commit `fe92baf2c06834300a51c82de60b0ab2897b57d5`, blob `85dd0fa35b2e7982b0c86020fdd4f4952e6a039f`), 교육용 TODO는 강사 정답과 독립입니다.

## 1. 오늘의 이야기

복도에서 로봇과 사람이 **같은 지점을 지난다**고 해서 반드시 충돌할까요? 2초 차이로 지나갔다면 실제로 만나지 않습니다. D13에서는 '공간에서 겹치는가' 대신 **같은 시간에 두 개의 점유영역이 겹치는가**를 판단합니다.

- **P (Predicted overlap):** 같은 시각의 로봇·사람 원형 점유영역이 한 번이라도 겹친 경우.
- **N (No predicted overlap):** 전체 유효 시점에 겹침이 없는 경우. **다른 안전 센서를 무시해도 된다는 뜻은 아닙니다.**
- **U (Unknown):** 사람 관측이 stale/future/low confidence이거나 경로가 손상된 경우. 안전하다는 판단을 금지합니다.
- **frame mismatch:** 좌표 프레임이 다르면, 교육용 CLI가 G09 함수에 입력하기 전에 U로 분류합니다. 원본 G09 자체가 TF 변환을 수행하지는 않습니다.

> 실제 로봇의 강제정지, Nav2 Goal, ROS 토픽, `/cmd_vel`을 다루지 않습니다. 이것은 합성 데이터의 오프라인 예측 **L0 실습**이며 인증 안전 판단이 아닙니다.

## 2. 수업 순서 (240분)

| 시간 | 활동 | 학습 증거 |
|---|---|---|
| 19:00–19:30 (30분) | 복도의 두 이동체 사례, P/N/U의 의미 | 예상 판정표 |
| 19:30–20:10 (40분) | CSV, 예측 시각, 반경, 현재 관측시각, 좌표 프레임 | robot `16`개 샘플 분석 |
| 20:10–20:20 (10분) | 휴식 | |
| 20:20–21:20 (60분) | TDD: 최초 RED→4개 TODO 단계 구현 | 공개 unittest |
| 21:20–21:30 (10분) | 휴식 | |
| 21:30–22:30 (60분) | P/N/U 반례·HTML 슬라이더 시각화 | 결과 JSON·HTML |
| 22:30–23:00 (30분) | 실패 경계·보호층의 역할·발표 | 워크시트·검증 캡처 |

## 3. 실습 환경 준비

새 터미널 **1개**를 열어 다음을 실행합니다.

```bash
cd ~
git clone --branch main \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-d13-student
cd ~/axia-d13-student
python3 --version
git rev-parse HEAD
```

이전 클론이 있다면 `git fetch origin`으로 최신 상태를 확인하되, 기존 학생 실습 코드가 덮어써지지 않도록 새 디렉터리에 클론하세요. **D13은 `main`에 배포된 학생용 TODO 패키지**입니다. `git rev-parse HEAD` 출력은 강사가 배포 공지한 정확한 main SHA와 비교합니다. 미완성 TODO의 P/N 테스트 실패는 교육 의도이며 저장소 배포 실패가 아닙니다.

## 4. 먼저 데이터 읽기

`block_D/day13/fixtures/robot_trajectory.csv`를 열어 보세요. 열 4개는 `t_sec, x, y, radius`입니다.

- 시작 시각 **10.1초**, 종료 **13.1초**; 예측 구간 **3.0초**, 간격 **0.2초** → 양끝을 포함한 **16개 점**입니다.
- 사람 관측값 `(x,y,vx,vy,radius,confidence,observed_sec)`를 읽고 같은 `t_sec`에 맞춰 위치를 **등속도 투영**합니다.
- `person_future_x = x + vx × (t_sec - observed_sec)`, y도 동일합니다.
- 동시간 거리 `sqrt((robot_x - person_x)^2 + (robot_y - person_y)^2)`가 반경 합 이하일 때 겹칩니다.
- 관측 데이터 나이는 `now_sec - observed_sec`. **0~0.5초** 이내여야 합니다. confidence 최소 **0.5**.
- 양의 시간 간격·유한 숫자·비음수 반경·정확한 시각 배열을 모두 검증한 후 P 또는 N을 냅니다. 도중에 U를 발견하면 이전의 겹침 여부와 무관하게 U입니다.

**주의:** 0.2초는 미래 예측 *샘플 간격*이지 LiDAR 발행 주기가 아닙니다. ROS 2/Gazebo에서 실제 센서·DDS 수신 주기를 보장한다는 뜻이 아닙니다.

## 5. RED 확인 (정상적인 실습 시작)

```bash
python3 -m unittest discover -s block_D/day13/tests -p 'test_*.py' -v
echo "student_tests_rc=$?"
```

**최초 예상 출력 예시 (실제 공개 RED #44873013772에서 P/N 두 건의 FAIL 확인):**

```text
test_N_same_path_different_time ... FAIL
test_P_same_time_overlap ... FAIL
test_U_stale_future_low_confidence ... ok
FAILED (failures=2)
student_tests_rc=1
```

이 상태가 당초 의도한 *학생용 TODO*입니다. **RED를 GREEN으로 위장하거나 학생 저장소에 강사 정답을 복사하지 않습니다.**

## 6. 코드 작성: 네 단계로 나누기

여러 파일을 수정할 필요가 없습니다. **`block_D/day13/reachability_student.py`만 변경**합니다.

1. **검증 단계:** `now_sec`, `dt_sec`, `horizon_sec`, `stale_sec`, `confidence_min`이 유한한 숫자인지 확인. 사람 관측시각·신뢰도·반경이 올바른지도 확인합니다. 오류 시 U.
2. **경로 단계:** 예상 점 수는 `round(horizon_sec / dt_sec)+1`. 전체 샘플의 시간·좌표·반경을 검사합니다. 빠지거나 시간축이 틀리면 U.
3. **동시간 투영:** 각 `robot_point.t_sec`에서 사람의 `(x,y)`를 속도 `(vx,vy)`로 투영합니다. 실제 거리와 반경 합을 비교합니다.
4. **최종 분류:** 어떤 샘플에서든 겹침이 있으면 P. 모든 샘플이 유효하고 겹침이 없다면 N. 그 외는 U.

검사를 앞부분에서만 끝내지 말고 **마지막 시점까지 전부 검증**하세요. 겹침을 찾았다고 즉시 P로 반환하면, 뒷부분의 잘못된 데이터를 놓칠 수 있습니다.

## 7. 합성 8개 사례 판정

| ID | 기대 | 이유 |
|---|---|---|
| `P_same_time_overlap` | P | 같은 시점에 두 점유 원이 중첩 |
| `N_same_route_different_time` | N | 같은 경로지만 시간을 맞추면 중첩 없음 |
| `U_stale_track` | U | 관측 시간이 0.5초 초과로 오래됨 |
| `U_future_stamp` | U | 관측 시각이 현재보다 미래 |
| `U_low_confidence` | U | 신뢰도 0.05 |
| `U_frame_mismatch` | U | map과 odom 좌표 직접 비교 금지 |
| `U_missing_last_sample` | U | 16개가 아닌 15개 샘플 |
| `U_time_jump` | U | 0.2초 간격 불일치 |

처음 5개 테스트 중 U는 통과하더라도, 구현이 정확하다는 뜻은 아닙니다. P와 N의 결과가 서로 다른 이유를 직접 설명할 수 있어야 합니다.

## 8. 오프라인 결과와 시각화 확인

```bash
python3 block_D/day13/run_lab.py --list --out /tmp/axia-d13
python3 block_D/day13/run_lab.py --out /tmp/axia-d13
echo "runner_rc=$?"
ls -lh /tmp/axia-d13/
```

미완성 TODO일 때 `D13_STUDENT_RESULT=RED_EXPECTED_TODO`, `runner_rc=2`가 **예상**됩니다. 구현 완료 후에는 `D13_STUDENT_RESULT=GREEN`, `runner_rc=0`을 확인하세요.

`/tmp/axia-d13/P_same_time_overlap.html`을 **파일 탐색기/브라우저에서 로컬로 열고**, 슬라이더를 움직여 시간마다 파란 로봇 원과 빨간 사람 원이 겹치는지 관찰합니다. `N_same_route_different_time.html`과 비교한 다음 `d13_results.json`의 예상값과 실제값을 검토합니다.

WSL2에서 Windows 브라우저를 쓰려면 (선택):

```bash
explorer.exe "$(wslpath -w /tmp/axia-d13/P_same_time_overlap.html)"
```

GUI가 없으면 HTML을 열지 않아도 JSON 판정·unittest를 완료할 수 있습니다.

## 9. 문제 해결

- `ModuleNotFoundError`: 저장소 루트에서 명령을 실행했는지 확인합니다.
- `P`·`N`에서 `U`: TODO가 아직 작성되지 않았거나 유효성 검사에서 정상 입력을 U로 판정하는 상태입니다.
- `U`인데 `N`: stale·future·low confidence·경로 누락을 검사하지 않았을 수 있습니다.
- `N`인데 `P`: 시간을 무시하고 동일한 공간 좌표만 비교했을 수 있습니다.
- HTML이 비어 보임: `run_lab.py` 성공적 파일 출력, 브라우저 JS 활성화, 로컬 파일 경로를 확인합니다. SVG는 시각 보조이며 판정을 변경하지 않습니다.
- 테스트 불합격: 마지막 실패의 문구보다 **최초 유효하지 않은 시점 또는 관측시각**을 먼저 확인합니다.

## 10. 제출 및 종료

`STUDENT_WORKSHEET_KO.md`의 표를 완성하고, 수정한 `reachability_student.py`, `d13_results.json`, 대표 P/N/U HTML 화면 또는 관찰 기록, unittest 출력과 커밋 SHA를 제출합니다.

**교육 성공 = 오프라인 P/N/U 구현·설명·반례 검증.** ROS 실제 동작, Gazebo 주행 성공, 인증 E-Stop 또는 정식 안전 인수는 포함되지 않습니다.

터미널 종료: `exit`. 실행 프로세스/백그라운드 노드는 이 실습에서 생성하지 않습니다.
