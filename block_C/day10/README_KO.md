# D10 — Isolation Forest 정상 기준 이상탐지·조기 경고 검증

**2026-11-20(금) 19:00–22:00**, 이론 60분/실습 120분. 합성 데이터 (`SYNTHETIC_COURSE_FIXTURE`)만 사용합니다. 실제 TurtleBot3 계측이나 인증 E-Stop이 아닙니다.

**학습 목표 1:** Isolation Forest 기반 이상신호 탐지 구조 이해.  
**학습 목표 2:** 정상 패턴 기준 이상탐지 및 조기 경고 검증 실습.


## 터미널이 `~`에서 시작할 때 — D10 사전검사 원샷

다른 장의 상대경로 명령만 단독 복사하면 `~/`에서 실패할 수 있습니다. 아래 블록은 위치를 직접 이동한 뒤 D10의 **학생 입력 준비**만 확인합니다. 미완성 `student_if_todo.py`를 정답인 것처럼 실행하지 않습니다. 오류가 생겨도 바깥 터미널 전체를 종료하지 않습니다.

```bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d10_course/axia-robot-safety-student"
  mkdir -p "$(dirname "$ROOT")"
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  cd "$ROOT"
  if [[ "$(git branch --show-current)" == main && -z "$(git status --porcelain)" ]]; then
    git pull --ff-only origin main
  else
    echo 'D10_STUDENT_SOURCE_UNTOUCHED existing branch or local changes'
  fi
  bash block_C/scripts/block_c_once.sh --doctor
  python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
  printf 'D10_STUDENT_PREFLIGHT_PASS source_sha=%s todo_expected_red=true\\n' "$(git rev-parse HEAD)"
) || printf '%s\\n' 'D10_STUDENT_PREFLIGHT_HOLD: 앞의 최초 오류를 확인하세요. 터미널은 유지됩니다.'
```

`--doctor`는 Python 3.12를 요구하며, 불일치 시 `BLOCK_C_ENV_DIFF_BLOCKED expected=3.12 actual=...` 메시지로 종료합니다. 공개 학생 TODO 미구현으로 발생하는 `NotImplementedError`는 **EXPECTED_RED**이고, 강사 정답의 C03 성공과 혼동하지 않습니다. D09 특징 CSV가 만들어지지 않았다면 이 사전검사 이후에도 D10 학습은 시작할 수 없습니다.


### Python 3.12 / scikit-learn 환경 오류를 예방합니다

- `bash block_C/scripts/block_c_once.sh --doctor`는 **Python 버전과 스캐폴드 환경을 확인**하는 단계이며 `sklearn`이 이미 설치됐음을 증명하지는 않습니다.
- `ModuleNotFoundError: No module named 'sklearn'`가 발생하면 시스템 Python에 `pip install`하지 말고 **[초심자용 D10 상세 실습 가이드](STUDENT_LAB_GUIDE_KO.md)**의 `1. 가상환경 준비`를 진행합니다.
- 학생 가상환경 `~/axia_d10_course/.venv`와 강사 D10 원샷의 `~/axia_d10_course/.venv-d10`은 **역할과 설치 범위가 서로 다릅니다**. 강사 비공개 정답이나 설치 스크립트를 학생 저장소에 복사하지 않습니다.
- D09 학생 특징 CSV가 없으면 `NotImplementedError`(EXPECTED_RED) 또는 입력 준비 누락이지 `sklearn` 설치만으로 해결되지 않습니다.

학습 순서:
1. **[학생용 데모 관찰 가이드](STUDENT_DEMO_GUIDE_KO.md)** — 시스템 아키텍처·원본→특징·Train/Valid/Test와 강사 라이브 화면의 기대 결과.
2. **[학생용 120분 실습 가이드](STUDENT_LAB_GUIDE_KO.md)** — Python 3.12 환경·원본 무결성·D09 6특징 입력 확보·TODO 구현·출력 검증·첫 경고 분석.
3. `student_if_todo.py`의 `fit_evaluate_if`는 초기 `NotImplementedError` 상태이며 **정답 미포함**입니다.

기준 데이터: Raw **4,599행/46 Trace**, 6개 특징, Train **240 VALID 정상** / Valid **80 VALID 정상** / Test **100 VALID + 품질 오류 4**. Normal Train에 대해서만 model/scaler를 fit하고 정상 Valid만으로 95% 분위 threshold를 정하며 Test는 마지막 평가에만 사용합니다.

학생용 기초 확인:
~~~bash
bash block_C/scripts/block_c_once.sh --doctor
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  block_C/tests/test_student_task_expected_red.py -k d10
~~~

`NotImplementedError`로 시작하는 D10 실패는 학습자의 **EXPECTED_RED**입니다. 이 공개 테스트만 GREEN으로 바꾸어도 점수 누수·품질·평가 타이밍 검증이 끝난 것은 아니므로 실습 가이드의 실제 입력·산출물 점검을 따릅니다. 공개 스캐폴드 CI는 정답이 포함되지 않았는지 확인하며 학생 개별 풀이 PASS를 뜻하지 않습니다.

**안전 경계:** AI score는 비인증 교육용 WARNING이며 기존 Safety Supervisor/FSM/Stop/Nav2/Goal/`cmd_vel`을 변경하거나 발행하지 않습니다.
