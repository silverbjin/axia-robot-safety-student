# D04 학생용 `main` 통합 안내 및 브랜치 역할 (2026-11-15)

> **역할:** 공개 **학생 TODO + 독립 실습·시연 도구** 저장소. 강사용 비공개 정답, hidden tests, P1 Safety Supervisor 등은 포함하지 않는다. 이 문서는 현재 `main`에 이미 포함된 D04 기능의 사용 순서와 과거 개발 브랜치 역할을 기록한다.

## 이미 main으로 병합된 브랜치

| 원본 브랜치 | PR / 결과 | 용도 |
|---|---|---|
| `feature/block-b-student-mvp-20261108` | [#4](https://github.com/silverbjin/axia-robot-safety-student/pull/4) **MERGED** | D04 사람 감지 `select_person`·D05 깊이 `measure_person_range` 학생 TODO, fixture SHA256, 기본 Python pytest |
| `feature/block-b-d04-guides-20261112` | [#10](https://github.com/silverbjin/axia-robot-safety-student/pull/10) **MERGED** | D04 실습 경로/venv/오류 진단 및 합성 실습과 YOLO 선택 시연 구별 |
| `feature/block-b-d04-shared-yolo-demo-20261112` | [#11](https://github.com/silverbjin/axia-robot-safety-student/pull/11) **CLOSED, NOT MERGED** | 강사용과 Git blob이 같은 공개 가능 CPU 단일 이미지 YOLO 시연·강의용 코드 지도. 모든 관련 소스가 #12 통합본에 포함되어 **현재 main 대비 ahead=0** |
| `feature/d04-student-gazebo-yolo-20261112` | [#12](https://github.com/silverbjin/axia-robot-safety-student/pull/12) **MERGED** | 독립 Waffle Pi Gazebo Harmonic + `yolo_ros` 실시간 감지 + Gazebo/YOLO GUI 시연 및 공개 CI 검증; #11 포함 |

이 브랜치들을 다시 main에 merge/cherry-pick 하지 않는다. 새 실습 개발의 출발점은 **현재 `main`**이다.

## D04 학습 실행 순서

저장소 루트에서 시작한다.

```bash
git clone --branch main https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'pytest==8.3.5'
python -m pytest -q block_B/tests/test_fixture_io.py
python -m pytest -q block_B/tests/test_block_b_public.py
```

1. **Python 합성 데이터 및 TODO:** [D04 학생 실습](D04_STUDENT_LAB_GUIDE_KO.md), `block_B/block_b_todo.py`. 학생 TODO의 초기 RED는 의도적이며 강사 정답을 복사하지 않는다.
2. **단일 이미지 YOLO (선택):** `block_B/day04/run_teacher_yolo_demo_once.sh`, `block_B/day04/yolo_single_image_demo.py`, [코드 해설](D04_ROS_CODE_WALKTHROUGH_KO.md). 이 경로는 CPU의 고정 이미지 bbox/class/confidence 예제이며 **Gazebo 창을 열지 않는다**.
3. **실제 Gazebo/YOLO GUI (선택·독립):** [D04 Gazebo 학생 GUI 가이드](D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md), `block_B/day04/run_student_gazebo_yolo_once.sh --self-check` 이후 명시적 `--run`. WSL2+WSLg GUI 표시가 가능한 장비에서 실행한다.
4. 실패하거나 미검증인 경우에도 `ROS_GAZEBO_PASS`, `WSL2_GUI_PASS`를 임의로 기록하지 않는다. 제출은 학생 TODO/pytest 실제 출력과 선택 시연의 원본 로그를 구분한다.

## 인수된 CI 근거와 미검증

- 공개 학생 실제 ROS 2 Jazzy/Gazebo Harmonic/YOLO: [Actions #43166114547](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43166114547) — Gazebo 실제 RGB·scan·DetectionArray 검증.
- 공개 CI Xvfb GUI 두 창: [Actions #43166756309](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43166756309) — Gazebo/YOLO 영상 창 관찰, 실제 사용자 WSLg 화면과 별개.
- 공개 학생 계약 [Actions #43167526178](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43167526178) — 29 PASS (PR #12 근거). D04 단일 이미지 CPU 근거는 PR #11 본문의 [Actions #43155417917](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43155417917).
- **학생의 TODO 완성 GREEN, 사용자 로컬 WSL2 WSLg GUI 재현은 자동 승격 금지.** 학생 실습은 **NO_GOAL / NO_CMD_VEL**, visual-only Actor 사용이며 인증 HW E-Stop 검증이 아니다.

## 세 저장소의 역할

- `silverbjin/axia-robot-safety-instructor` (private): 정답/숨김 테스트·강의 스크립트·강사 P1 시연
- `silverbjin/axia-robot-safety-student` (public): 지금 읽는 학생 TODO/공개 실습
- `silverbjin/axia-robot-safety-ci-public` (public): 독립 CI 검증기/WSL2 공개 배포 실행기. **비공개 GitHub Actions를 사용하지 않는다.**

이번 문서 병합은 테스트·실행기·fixture·안전 TTL 또는 Nav2 소스의 변경을 포함하지 않는다.
