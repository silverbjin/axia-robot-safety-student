# D09 — make six trace-safe mean/std features and mark invalid traces as INSUFFICIENT_DATA

이론 60분 / 실습 120분. 합성 데이터(SYNTHETIC_COURSE_FIXTURE)만 사용합니다. 실제 TurtleBot3 측정이나 인증된 E-Stop이 아닙니다.


## 0. GitHub 저장소 클론부터 시작 (최초 1회)

**Ubuntu 24.04 / WSL2의 새 터미널에서 시작합니다.** 학생 저장소는 공개이므로 GitHub 로그인 없이 읽기 전용으로 클론할 수 있습니다. 이미 클론한 경우에는 파일을 덮어쓰거나 재클론하지 않습니다.

```bash
git --version
mkdir -p "$HOME/axia_d09_course"
cd "$HOME/axia_d09_course"
if [ ! -d axia-robot-safety-student/.git ]; then
  git clone https://github.com/silverbjin/axia-robot-safety-student.git
fi
cd axia-robot-safety-student
# 기존 clone이 깨끗한 main인 경우에만 안전하게 최신 상태로 갱신합니다.
if [ "$(git branch --show-current)" = "main" ] && [ -z "$(git status --porcelain)" ]; then
  git pull --ff-only origin main
else
  echo "기존 브랜치/수정 사항 보존: 자동 pull 생략"
fi
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

예상 결과: `~/axia_d09_course/axia-robot-safety-student` 저장소가 준비되고 현재 브랜치가 `main`으로 표시됩니다(새 클론 기준). 기존 브랜치·수정 파일은 덮어쓰지 않습니다. **이후 명령은 같은 터미널에서 학생 저장소 루트에 머문 상태로 실행**합니다. `git clone` 실패 시 네트워크·Git 설치·접근 URL부터 확인하고, `git pull --ff-only` 실패 시 충돌을 강제 해결하지 말고 `git status`를 확인하세요.

**D09 라이브 도입(이론 첫 12분):** [학생용 데모 가이드 0-A절의 D08 실제 `/scan` Plot 관찰](STUDENT_DEMO_GUIDE_KO.md)을 먼저 확인합니다. 강사 화면의 실시간 LiDAR **거리(m)** 관찰이며 모터 전류·토크·가속도 실측이 아닙니다. Plot은 선택 데모로, 안 보이면 HOLD 후 기존 오프라인 실습으로 진행합니다. **이론 60분/실습 120분 유지**.

**D09 최신 학생 자료:** [데모 가이드](STUDENT_DEMO_GUIDE_KO.md) / [120분 실습 가이드](STUDENT_LAB_GUIDE_KO.md). 두 문서를 순서대로 읽고 본 README의 TODO 계약을 수행합니다.

1. 프로젝트 루트에서 `bash block_C/scripts/block_c_once.sh --doctor`로 환경을 확인합니다.
2. fixture의 SHA256과 train/valid/test 분리를 확인합니다.
3. `student_eda_todo.py`의 TODO를 구현합니다.
4. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q block_C/tests/test_student_task_expected_red.py`로 RED→GREEN 진행을 기록합니다.
5. 출력 파일과 시간·trace 품질 위반의 최초 지점을 보고합니다.

학생의 TODO는 완성 전 EXPECTED_RED이며 공개 CI의 PASS는 이 함수의 정답 구현을 의미하지 않습니다.
