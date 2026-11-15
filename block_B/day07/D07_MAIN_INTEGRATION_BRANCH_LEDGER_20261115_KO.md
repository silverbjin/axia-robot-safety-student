# D07 학생용 main 통합 인계 — 2026-11-15

**역할:** 독립 공개 학생 저장소. D07 학습 목표는 **① 사람을 동적 장애물로 처리하는 회피제어 구조 이해 ② 사람 회피 로직 및 주행제어 실습**이다. 단, 현재 필수 학생 구현은 합성 경로의 **read-only 회피 판단**이다. 실제 로봇 ControllerServer 주행은 검증되지 않아 별도 Gate에 남긴다.

## 브랜치·PR 역할

| 개발 브랜치 | PR / 처리 | 구현·교육 역할 |
|---|---|---|
| `feature/d07-human-aware-todo-20261110` | [#8](https://github.com/silverbjin/axia-robot-safety-student/pull/8) **MERGED** | `route_todo.py` 두 학생 TODO(`route_obstacle_status`, `assess_replan`), `routes.json` 합성 fixture, 학생 공개 RED 테스트. 최신 main 대비 ahead=0 |
| `docs/d07-3h-classroom-20261114` | [#20](https://github.com/silverbjin/axia-robot-safety-student/pull/20) Draft 교육 이력 | 이론 60분·실습 120분의 3시간 강의안, 학생 Demo/Practice 설명, RED→GREEN과 두 자료 계약 테스트. D06 등 이전 base 차이 때문에 브랜치 전체 병합하지 않음 |
| `release/d07-classroom-main-20261115` | D07 통합 릴리스 PR | #20의 D07 문서·테스트만 **최신 main에 선별 이식**, 학생 clone 브랜치를 main으로 변경, D07 교육 계약을 공개 CI에 추가 |

## 후속 수업용 경로

- [D07_LAB_KO.md](D07_LAB_KO.md): 학생 시작 페이지.
- [D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md](D07_STUDENT_3H_CLASSROOM_GUIDE_20261117_KO.md): 2026-11-17 19:00–22:00 이론 60m + 실습 120m. TODO→pytest RED/GREEN→UNKNOWN 경계→Nav2 실제 L1 결과 해석.
- [D07_STUDENT_DEMO_GUIDE_20261117_KO.md](D07_STUDENT_DEMO_GUIDE_20261117_KO.md): 강사가 공개 공식 Nav2 Planner L1 및 H01 no-goal 기록을 **읽기 전용**으로 설명. 안전제어·이동 성공을 가장하지 않음.
- [D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md](D07_STUDENT_PRACTICE_GUIDE_20261117_KO.md): 학생 측 소스 복제, 결과·로그 제출, 의도적 RED→GREEN.
- `block_B/day07/route_todo.py`, `fixtures/routes.json`, `tests/test_d07_public.py`: 기존 **학생 TODO·합성 데이터·검증** 파일 수정 없음.

## 검증 근거와 경계

- 기존 [공식 Nav2 Planner/Costmap ROS L1 #42661513782](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42661513782): synthetic `/axia/d07/test/scan` → ObstacleLayer→PlannerServer `ComputePathToPose`: lethal 0→101→0, Path 58→74→58. **NavigateToPose/Controller/odom 물리 주행 없음**.
- 최신 [D07 H01 실제 Gazebo no-Goal Gate1 #43673228520](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43673228520): 실제 장애물→Costmap→우회 경로 일부 스코프 PASS. **물리 Contact-free 이동/Guard 150ms TTL·Goal·Owner WSL2 L3는 미검증**.
- 학생 과제의 `robot_moved`, `collision_free_verified`, `safety_certified`는 항상 false. **학생 Python L0 ≠ Nav2 실운행**. 교육용 SW STOP ≠ 인증 E-Stop.
- 공개 학생 자료에는 비공개 강사 정답·hidden tests·비공개 GitHub Actions 없음.

## 다음 작업 시작

```bash
git fetch origin main
git switch main
git pull --ff-only origin main
git switch -c feature/d07-next
```

이번 인계 병합은 D07 교육 문서·경량 공개 테스트에만 적용한다. 안전/Goal/Nav2 런타임은 건드리지 않는다.
