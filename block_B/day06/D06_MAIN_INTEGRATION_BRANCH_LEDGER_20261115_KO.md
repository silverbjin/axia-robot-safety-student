# D06 학생용 main 통합 및 브랜치 역할 (2026-11-15)

**기준:** 학생 독립 공개 저장소 `silverbjin/axia-robot-safety-student`. 현재 수업은 D06 **Safety Bubble**이고 학습 목표는 (1) **거리 구간별 속도 제한 및 감속·정지 규칙 이해**, (2) **Safety Bubble 기반 안전제어 로직 설계 실습**이다.

## 개발 이력·브랜치 역할

| 브랜치 | PR | 역할 | main 반영 |
|---|---|---|---|
| `feature/d06-safety-bubble-todo-20261110` | [#7](https://github.com/silverbjin/axia-robot-safety-student/pull/7) MERGED | 합성 distances fixture, 학생 `classify_range`/`bubble_policy` TODO, 공개 RED 계약 | 이미 main에 포함, 재병합 금지 |
| `docs/d06-classroom-materials-20261113` | [#19](https://github.com/silverbjin/axia-robot-safety-student/pull/19) Draft/Open (기록용) | 3시간 실습·읽기 전용 Live 관찰 가이드, 공공 계약 RED→GREEN | 후속 `release/d06-classroom-main-20261115`에서 D06 전용 자료만 반영; 구형 전체 브랜치 병합 금지 |
| `release/d06-classroom-main-20261115` | 신규 릴리스 PR | #19 강의안 2개, 실습 진입 링크, 7개 공개 가이드 계약을 **최신 main**에 적용. 브랜치/clone 지시를 `main`으로 변경 | 공개 Actions 통과 후 main에 병합 |

## 실행할 자료

- [D06_LAB_KO.md](D06_LAB_KO.md) — 기존 과제 진입점.
- [D06_STUDENT_3H_CLASSROOM_GUIDE_20261116_KO.md](D06_STUDENT_3H_CLASSROOM_GUIDE_20261116_KO.md) — 2026-11-16 19:00~22:00(이론 60분 + 실습 120분), 한 터미널에서 RED → GREEN → 경계(0.40/0.75m) → UNKNOWN 및 증거 보존.
- [D06_STUDENT_LIVE_DEMO_GUIDE_20261116_KO.md](D06_STUDENT_LIVE_DEMO_GUIDE_20261116_KO.md) — 선택형 **학생 독립 D05 Gazebo sensor-only** 관찰(Goal/실제 CM 정지 없음); 강사 G07 주행은 Owner 안전 인수 **HOLD**이므로 공식 CM 격리 L1으로 대체.
- `block_B/day06/safety_bubble_todo.py` — 학생이 구현할 두 함수. 초기 NotImplementedError/RED는 의도적이고 정답·hidden tests는 이 공개 저장소에 넣지 않는다.

## 기존 검증과 이번 인수 범위

- [공식 Nav2 Collision Monitor 격리 ROS L1 #42656227824](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42656227824): 실물/주행이 아닌 **격리 토픽**에서 synthetic LaserScan 거리 1.20/0.65/0.30m → 명령 0.20/0.06/0.00m/s. ROS 메시지·공식 CM 정상 실행을 검증했지만 실제 `/cmd_vel` 구동, odom, Goal, 정지 유지, 인증 E-Stop은 미검증.
- [학생용 가이드 기존 GREEN #43554329167](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43554329167): 46 tests PASS. 교육 자료와 학생 TODO가 남은 상태.
- [2026-11-15 학생 공개 CI #43672694775](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43672694775): 이번 release branch 공개 `scaffold-contract` PASS; `student-green` job은 설계대로 SKIPPED(학생 정답 구현 미포함).
- 강사용 G07+RViz 실제 Goal은 공개 CI/Owner L3에서 **CM source 간헐 150ms TTL 위반**과 첫 Guard latch 이후 인수 HOLD. 이를 기존 ROS L1 PASS로 대체해 안전시연 완료했다고 주장하면 안 된다.
- 학생 교육용 `STOP` 정책 출력은 안전 인증된 정지 명령과 다르며, **SW STOP ≠ 인증된 hardware E-Stop**이다.

## 후속 개발 시작

```bash
git fetch origin main
git switch main
git pull --ff-only origin main
git switch -c feature/d06-next
```

이번 통합은 D06 가이드·수업 계약만 변경한다. 학생 TODO·fixture·공식 Nav2·Safety Supervisor·Collision Monitor 안전 설정/TTL·Goal/모터 코드는 변경하지 않는다.
