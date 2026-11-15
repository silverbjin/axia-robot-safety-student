# D08 학생용 `main` 통합·브랜치 이력 (2026-11-15)

**정식 교육 범위:** 2026-11-18 19:00–23:00 온라인 4시간. 학생은 D04 사람 검출 → D05 Depth ROI median(m) → D06 Bubble → D07 기록 경로 평가 함수를 호출하는 **단일 `integrate_case()` TODO**만 구현한다. **ROS/Gazebo 설치, Goal, `/cmd_vel`, 안전제어 구현은 요구하지 않는다.**

## 브랜치/PR 역할 및 인수 판단

| 브랜치 | PR | 역할 | 처리 |
|---|---|---|---|
| `feature/d08-online-integration-todo-20261110` | [#9](https://github.com/silverbjin/axia-robot-safety-student/pull/9) | 학생 합성 6사례·단일 TODO·실행/ZIP 생성기·SHA256/심볼릭링크 방어·현장 YOLO 실패 분석, 최초 다운로드/제출 가이드 | 8개의 D08 파일을 **기존 Git blob 그대로** 최신 `main`에 선택 반영, 가이드의 clone 브랜치만 `main`으로 변경 |
| `release/d08-online-edu-main-20261115` | 신규 D08 main PR | #9의 8개 학생 파일 + 공개 학생 Actions Workflow + 기존 D04~D07을 유지한 README 색인 + 이 브랜치 이력 | 공개 L0와 미구현 TODO 의도된 RED 검증 후 `main` 병합 |
| `feature/d08-online-integration-ci-20261110` (별도 공개 CI 저장소) | [공개 #39](https://github.com/silverbjin/axia-robot-safety-ci-public/pull/39) MERGED | 학생 fixture/ZIP 소스·SHA 검증만 하는 기존 공개 CI | 중복 재병합 금지. Student 저장소 자체의 공개 Actions로 이번 PR도 확인 |

## 학생 과제 파일과 실행

- [D08_LAB_KO.md](D08_LAB_KO.md): `git clone --branch main`, Python 3.12 venv, RED→GREEN, 6사례 결과 CSV/JSON, SHA256 ZIP 제출.
- [D08_FIELD_DIAGNOSTIC_CASE_KO.md](D08_FIELD_DIAGNOSTIC_CASE_KO.md): 원거리 `person=0, umbrella=64`, 최근 RGB/Depth `198ms > 50ms` 문제와 공개 무주행 Gazebo·C++ YOLO 영상 재생의 한계 분석(15–20분).
- `integration_todo.py`: `integrate_case()` 하나만 학생 TODO. 강사 참조 코드·hidden test 없음.
- `fixtures/d08_synthetic_cases.json`: `clear_replan`, `slow`, `stop`, `lost`, `stale_depth`, `stale_track` 6개 합성 상황.
- `run_lab.py`, `submission_zip.py`: 이미 존재하는 새 출력 폴더/결과 위조·불완전 ZIP·symlink를 차단. 제출 ZIP 정확히 5파일(`trace.csv`, `summary.json`, `pytest.txt`, `integration_todo.py`, `SHA256SUMS`).
- `.github/workflows/d08-online-integration-student.yml`: **공개 GitHub Actions**, fixture/ZIP 약 10 PASS + 학생 TODO 의도적 RED 확인. 학생 개별 구현의 FULL GREEN을 허위 보고하지 않음.

## 증거 수준과 안전 경계

- 기존 [학생용 L0 공개 Actions #43136810905](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43136810905): **10/10 PASS** + `D08_STUDENT_EXPECTED_RED_CONFIRMED`, 최초 브랜치 산출물.
- 기존 [실제 Gazebo NO-GOAL #43117842587](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43117842587): human near 약 **0.359m**, far 약 **1.412m**, native `set_pose` ACK와 실제 `/scan`/RGB-D. 실제 모터 Goal 없음.
- [실제 C++ yolo_ros 영상 재생 L1 #43118537433](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43118537433): 근접 RGB 영상 재생에서 `person=3`, 최고 약 0.549731. **실시간 WSL2 YOLO/D05 Depth 종단이 아니다**.
- 학생 합성 과제의 `robot_moved`, `collision_free_verified`, `control_published`, `safety_certified`, `ros_verified`, `gazebo_verified`는 모두 **false**.
- **SW Stop ≠ 인증 HW E-Stop**. H01 이동·G07 안전 TTL/Guard 인수 HOLD는 D08 학생 실습 PASS와 별개.

## 후속 작업 진입

```bash
git fetch origin main
git switch main
git pull --ff-only origin main
git switch -c feature/d08-next
```

이번 릴리스에서 D04–D07 기존 코드/fixture를 덮어쓰지 않았고, 학생 정답이나 비공개 GitHub Actions를 추가하지 않았다. D08 수업은 `main`의 [실습 안내](D08_LAB_KO.md)에서 재개한다.
