# AXIA D05 학생용 `main` 인수·브랜치 역할 인계 (2026-11-15)

**목적:** 별도의 공개 학생 저장소에 이미 병합된 D05 Python TODO·3시간 강의 가이드·독립 Waffle-mounted RGB-D/Gazebo/YOLO Live를 현재 `main` 기준으로 재사용한다. 강사용 비공개 정답·ROS Depth Observer·hidden tests·모델 weights를 포함하지 않는다.

## 1. 개발 브랜치별 역할·병합 판정

| 브랜치 | PR / 실제 처리 | 역할 |
|---|---|---|
| `feature/block-b-student-mvp-20261108` | [#4](https://github.com/silverbjin/axia-robot-safety-student/pull/4) MERGED | D04 `select_person`, D05 `measure_person_range`의 **학생 TODO**, 합성 detections/Depth fixture·해시·기본 pytest |
| `feature/block-b-d05-class-20261112` | [#13](https://github.com/silverbjin/axia-robot-safety-student/pull/13) MERGED | 3시간 D05 실습·학생 데모 가이드, 거리 median(m)·접근 두 시점 -0.50m/s, RED→GREEN 안내 |
| `test/d05-mounted-rgbd-red-20261113` | [#14](https://github.com/silverbjin/axia-robot-safety-student/pull/14) CLOSED NOT MERGED | Waffle 카메라 탑재/실제 접근 Actor를 **실패하도록 요구한 원래 RED 회귀**. 기능 미구현 시점의 교육 증거이므로 그대로 merge 금지 |
| `feature/d05-mounted-rgbd-actor-live-20261113` | [#15](https://github.com/silverbjin/axia-robot-safety-student/pull/15) CLOSED/ARCHIVED | Waffle `camera_link` 탑재 정렬 RGB-D와 사람이 2.8→2.0→2.8m로 움직이는 공개 Gazebo/YOLO scene/검증기. main에는 **통합 PR #16**으로 반영됨 |
| `release/d05-live-integration-20261113` | [#16](https://github.com/silverbjin/axia-robot-safety-student/pull/16) MERGED | #15의 공개 Live Gazebo/YOLO 소스·L2 Actions·교육 가이드 통합. D04 기본 시연, 학생 Python TODO는 유지 |
| `fix/d05-live-distance-observation-before-fault-20261113` | [#17](https://github.com/silverbjin/axia-robot-safety-student/pull/17) MERGED | 실제 강사 Observer가 `VALID distance_m`를 보여준 **후에만** Depth bridge를 차단하도록 공개 실행기/회귀계약 수정 |
| `docs/d05-student-gazebo-live-guide-20261113` | [#18](https://github.com/silverbjin/axia-robot-safety-student/pull/18) MERGED | WSL2 GUI 1터미널과 선택형 모니터링, `SENSOR_ONLY` vs 강사 `D05_PRIVATE_DISTANCE_OBSERVER` 구분 및 수업 중 오류 대응 |

**재병합하지 않는 이유:** PR #14는 의도된 RED이고, PR #15는 #16의 이전 버전이다. #17의 학생 실행기·검증기 **세 파일 Git blob SHA가 현재 main과 동일**, #18의 문서·계약 다섯 파일 Git blob SHA가 현재 main과 동일하다. 과거 병합 PR의 HEAD가 `main`보다 옛날이거나 `ahead_by>0`이어도 최신 소스가 누락됐다고 단정하지 않는다.

## 2. 현재 main에서 진행하는 3시간 D05 실습

1. [학생 실습·정답이 없는 TODO](D05_STUDENT_LAB_GUIDE_KO.md): `block_B/block_b_todo.py`의 `measure_person_range()`를 직접 구현하고 합성 f001 = **1.30m** median·invalid=UNKNOWN·두 시점 접근 속도 **−0.50m/s** 설명. 초기 RED는 정상이다.
2. [독립 공개 Gazebo/YOLO Live](D05_STUDENT_GAZEBO_LIVE_GUIDE_KO.md): 기존 D04 `block_B/day04/run_student_gazebo_yolo_once.sh`를 `AXIA_D05_LIVE=1 AXIA_D05_SENSOR_ONLY=1`로 사용하여 실제 ROS RGB/Depth/YOLO 이미지를 관찰한다. 아래 학생 실행은 비공개 `person_range_status` 실제 거리(m)를 발행하지 않는다.
3. [학생용 데모 가이드](D05_STUDENT_DEMO_GUIDE_KO.md)와 `block_B/day05/gazebo_live/{prepare_scene.py,verify_live.py}`로 실제 actor 접근을 관측한다. `--run` 이전에 환경 점검 `--self-check`를 적용한다.

실습 환경은 사용자 WSL2 Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, WSLg(선택 GUI)다. Python 합성 TODO 실습만 할 때는 GPU나 Gazebo가 필요하지 않다.

## 3. 인수·증거의 정확한 범위

- [공개 실제 Gazebo L2 #43353480617](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43353480617): Waffle-mounted RGB-D+YOLO/GUI sensor-only PASS. 학생이 private Observer 실제 거리(m)를 출력한 것은 아니다.
- [공개 관찰 순서 RED #43357838878](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43357838878): `1 failed, 37 passed`; [GREEN #43358060896](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43358060896): `38 passed`.
- [공개 Gazebo/YOLO GUI sensor-only #43358061055](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43358061055): 실제 RGB-D 정렬 8쌍, YOLO person/bbox 및 Xvfb 창 확인.
- [학생 D05 가이드 계약 #43365672072](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/43365672072): `38 passed`, 문서 변경만 검증(실제 WSLg 실행 아님).
- 강사용 WSL2에서 보고한 실제 8개 VALID **2.860311~3.025961m** 및 Depth 차단 UNKNOWN은 **강사 전용 과거 실행 증거**. 최신 90초 VALID 보존 순서와 로컬 WSLg를 CI의 sensor-only L2만으로 자동 합격시키지 않는다.
- **NO_GOAL / NO_CMD_VEL**, 표준 SW STOP과 인증 E-Stop은 다른 것이다. 실제 로봇 보호정지/Guard TTL, 주행 충돌 안전 인증에 포함하지 않는다.

## 4. 후속 학생 프로젝트의 출발점

```bash
git fetch origin main
git switch main
git pull --ff-only origin main
# 필요할 때만 새 작업 브랜치 생성
git switch -c feature/d05-next-task
```

이번 변경은 **브랜치 정리 문서만 추가**한다. 기존 Gazebo/ROS/YOLO 실행기, Depth/YOLO 모델, 공식 Nav2, student TODO, 제출 fixture, CI 실행 계약 변경 없음. 강사 정답을 학생 저장소로 복사하지 않는다.
