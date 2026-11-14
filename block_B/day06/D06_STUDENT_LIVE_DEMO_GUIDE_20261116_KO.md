# AXIA D06 — 학생용 Gazebo Live Demo 및 강사 G07 관찰 가이드

**일시:** 2026-11-16(월) 21:25–21:40 선택 시연, 3시간 수업의 일부. **학습 목표:** ① 거리 구간별 속도 제한·감속·정지 규칙 이해 ② Safety Bubble 기반 안전제어 로직 설계 실습.

> **안전/공개 배포 경계:** 학생 PC는 기존 공개 D05 Gazebo Waffle+RGB-D+YOLO 시연을 그대로 재사용한다(**NO_GOAL / NO_CMD_VEL**). 이 학생 장면은 로봇이 정지해 있는 센서 Live이며 CM STOP 주행 증거가 아니다. 실제 CLEAR→SLOWDOWN→STOP 이동 시연은 **강사**가 비공개 G07 Owner + 공개 RViz2 sidecar로 수행하고 학생은 화면을 관찰한다. 비공개 Instructor 소스·강사 정답·Goal 승인 코드를 학생에게 제공하지 않는다.

> **수업 시연 상태 공지 (2026-11-14):** 강사 G07 이동 Goal + RViz2 동시 시연은 공개 CI 실제 Gazebo에서 CM 발행 150ms 위반이 재현되어 **현재 HOLD**다. 학생은 이를 직접 실행하거나 강사에게 무리한 재시도를 요청하지 않는다. 이번 L6은 검증된 **공식 CM 격리 ROS L1**을 관찰하고 고정 속도 0.20→0.06→0.00m/s의 의미를 해설한다. 기존 G07 성공 영상·CI 로그는 과거 증거로만 사용할 수 있다. 강사 G07 Live는 CI 전체 인수 후 별도 현장 최종 검수가 완료됐을 때만 선택한다. 학생 독립 공개 D05 Gazebo 관찰은 G07과 별도로 유지된다.

## 1. 어떤 화면을 확인하는가?

| 시연 | 실제 실행자 | 볼 수 있는 것 | 볼 수 없는 것 |
|---|---|---|---|
| 학생 독립 **공개** Gazebo | 학생 WSL2 | 실제 ROS + Gazebo Waffle, 움직이는 사람형 visual Actor, RGB-D/YOLO bbox, 선택 RViz2 | Nav2 이동 Goal, 실제 Collision Monitor STOP, live 사람 거리(m) |
| 강사 G07 Gazebo + RViz2 | 강사 Owner WSL2 | 움직이는 Waffle, LiDAR, CM 전후/Guard 최종 명령, odom, 교육용 Safety Bubble 링 | HW E-Stop 인증, 새 D06 GUI 인수 자동 통과 |
| 학생 Python TODO | 학생 Python pytest | CLEAR/SLOWDOWN/STOP/UNKNOWN, expected_ratio | /cmd_vel 발행과 실제 로봇 구동 |

PC 간 ROS_DOMAIN_ID는 자동 공유되지 않는다. 강사의 G07은 LOCALHOST 격리 세션이므로 학생은 **프로젝터/화면 공유로만 관찰**한다. 다른 PC의 ROS 통신 정책을 임의 완화하거나 강사 Goal을 복제하지 않는다.

## 2. 학생 터미널 A — 독립 Gazebo Live 원샷 (수업 전 준비 권장)

요구 환경: WSL2 Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, WSLg. 학생용 공개 D05 Gazebo Live의 기존 검증 소스 SHA `1c03c9bfb4b41e2726a7c1d2f47d65496bdaa474`를 고정하고 별도 폴더를 사용한다. 처음 실행 때 공개 YOLO/모델 의존성 다운로드·빌드가 발생할 수 있다.

~~~bash
(
  set -Eeuo pipefail
  SHA="1c03c9bfb4b41e2726a7c1d2f47d65496bdaa474"
  LAB="$HOME/axia_d06_student_gazebo_live"
  if [[ ! -e "$LAB" ]]; then
    git clone --quiet --no-checkout \
      https://github.com/silverbjin/axia-robot-safety-student.git "$LAB"
  fi
  test -d "$LAB/.git"
  git -C "$LAB" fetch --quiet --depth 1 origin "$SHA"
  git -C "$LAB" checkout --quiet --detach "$SHA"
  test "$(git -C "$LAB" rev-parse HEAD)" = "$SHA"
  test -z "$(git -C "$LAB" status --porcelain --untracked-files=no)"
  cd "$LAB"
  AXIA_D05_LIVE=1 bash block_B/day04/run_student_gazebo_yolo_once.sh --self-check
  AXIA_D05_LIVE=1 AXIA_D05_SENSOR_ONLY=1 \
    AXIA_D04_STUDENT_GUI=1 AXIA_D04_STUDENT_DOMAIN_ID=49 \
    AXIA_D04_STUDENT_GUI_HOLD_S=180 \
    bash block_B/day04/run_student_gazebo_yolo_once.sh --run
)
~~~

**예상 로그(현장 실측 주장 아님):**
~~~text
D04_STUDENT_GAZEBO_STATIC_PASS GAZEBO_NOT_RUN YOLO_NOT_RUN
D04_STUDENT_GAZEBO_LAUNCHED: GUI startup requested; NOT yet verified
D05_PUBLIC_SENSOR_ONLY_PASS REAL_RGBD_YOLO PRIVATE_D05_RANGE_NOT_RUN
D04_STUDENT_GUI_HOLD_STARTED seconds=180; press Ctrl+C when finished
D04_STUDENT_EVIDENCE=/home/.../axia_d04_student_evidence/d04-gazebo-...
~~~

학생 Live에 `/axia/d05/person_range_status`의 실제 미터 수치는 제공되지 않는다. YOLO bbox를 실제 거리라고 말하지 않는다. 이 runner는 **NO_GOAL / NO_CMD_VEL / NO_ESTOP**이다.

**선택 RViz2:** 이 학생 D05 장면의 실제 /scan·odom·TF·RobotModel을 확인하려면 GUI 실행 줄에 `AXIA_D04_STUDENT_RVIZ=1` 환경변수를 추가한다(사전 설치·그래픽 부하 확인). 학생 RViz2는 강사 G07/D06 보호 링 RViz2와는 **다른 장면**이므로 CM 정지 증거가 아니다.

## 3. 터미널 B — 학생 장면의 읽기 전용 ROS 토픽 확인

A가 실행 중인 동안만 B를 연다. `ROS_DOMAIN_ID=49`는 A의 학생 설정과 일치해야 한다.

~~~bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=49
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list | grep -E '/axia/d05/rgbd/(image|depth_image)|/yolo/cam0/detections'
ros2 topic info /axia/d05/rgbd/depth_image --verbose
ros2 topic echo /axia/d05/rgbd/depth_image \
  --once --field encoding --qos-reliability best_effort
~~~

예상 Depth encoding은 `32FC1`이다. 이는 실제 ROS 이미지 **형식**이며 사람까지의 거리 숫자가 아니다. 학생은 **ROS 토픽 발행 명령이나 Action Goal 전송 명령을 실행하지 않는다.** `Ctrl+C`로 B의 구독만 닫는다.

## 4. 강사 G07 Gazebo + RViz2 관찰표 — 15분

강사 원샷은 기존 G07 SHA 고정, 실제 TTY 수동 승인 `YES-P2-G07-GOAL`, Gazebo GUI 및 RViz2 읽기 전용 관찰기로 구성된다. 강사 PC의 `ROS_DOMAIN_ID`는 원샷이 자동으로 지정한다. 학생이 따라 입력하지 않는다.

| 단계 | 학생 예상 | 실제 관찰할 증거 | 관찰값/미검증 |
|---|---|---|---|
| CLEAR | 원래 명령 그대로 | /scan + /cmd_vel_supervised(입력) + /cmd_vel_pre_guard(CM 출력), /odom | __________ |
| SLOWDOWN | ratio 0.30 | 같은 시각의 실제 CM 전후 속도 비율; **입력 0.20m/s 고정 아님** | __________ |
| STOP | CM 출력 0, Guard 최종 0 | /cmd_vel_pre_guard → /cmd_vel 및 odom 정지 유지 | __________ |
| UNKNOWN | CLEAR 권한 불가 | 학생 `None`/NaN/stale 분류. 공식 CM state의 UNKNOWN enum이라 주장 금지 | __________ |

RViz2에는 RobotModel·TF·LaserScan·Odometry와 **교육용 0.40/0.75m 링**이 표시된다. 링 및 `D06_EDU_OBSERVATION_ZONE`은 단순 /scan 교육용 annotation이며 공식 CM verdict가 아니다.

**학생 질문:** CM 입력과 출력은 왜 다른가? `cmd_vel=0`과 실제 odom 정지는 어떻게 다른가? D05 영상 bbox와 Depth 카메라 Z를 공식 CM의 base_footprint 반경으로 왜 직접 대체할 수 없는가?

## 5. 실패·종료·증거 범위

1. 학생 GUI가 표시되지 않으면 소스 검사 `--self-check`만으로 Gazebo PASS를 주장하지 않는다. 실제 화면·RGB/Depth 최초 전달 문제를 `$HOME/axia_d04_student_evidence/d04-gazebo-*`의 `live_verdict.json`과 로그에서 확인한다.
2. 강사 G07이 BLOCKED면 같은 오류의 현장 재시도를 반복하지 않는다. 최초 안전 상태 전이/최초 Scan·CM·Guard 타이밍 위반을 확인한다. 강사 수업에서는 기존 [G07 실제 Gazebo L2](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43339521667)·[공식 D06 ROS L1](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/42656227824)을 **과거 증거**로 해설하며 이번 Live는 `NOT_RUN/BLOCKED`로 남긴다.
3. A의 Runner 정상 종료 또는 A에서 `Ctrl+C`, B에서 `Ctrl+C`. `killall`, `pkill -f`, `wsl --shutdown`으로 다른 실습을 종료하지 않는다.
4. 제출: 학생 Gazebo 실제 실행 여부, 화면·ROS 토픽, 소스 SHA, G07 3단계 관찰표, 자신의 Python RED/GREEN·UNKNOWN 반례(별도 [D06 실습 가이드](D06_STUDENT_3H_CLASSROOM_GUIDE_20261116_KO.md))와 **검증 수준**.

**검증 수준:** 학생 Gazebo 센서 Live ≠ 강사 G07 주행 L2/L3 ≠ 학생 Python L0. 신규 사용자 WSL2 GUI 관찰 전에는 `NOT_RUN`, SW Stop은 인증된 E-Stop이 아니다. 비공개 소스를 배포하지 않는다.