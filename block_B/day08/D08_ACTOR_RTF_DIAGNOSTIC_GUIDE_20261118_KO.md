# AXIA D08 — Actor 저속 이동 RTF·자원 진단 가이드

작성일 2026-11-18 KST. 대상 ROS 2 Jazzy / Gazebo Harmonic / WSL2 WSLg.
**목적:** 이미 정상 실행 중인 Gazebo+YOLO+RViz2를 그대로 두고 Actor 저속 원인을 읽기 전용으로 진단한다.
실제 ROS/Gazebo 구동·재계획·CM/Guard 안전 인수는 이 스크립트로 수행하지 않는다.

## 원본 증거 및 검증 수준

사용자 제공 d04-gazebo-FoAq7eRu.zip의 실세계 Gazebo SDF에서 Actor x=2.8→2.0→2.8m, sim_time 0→5→10초를 확인했다. 원래 이동 속도는 **0.16m/s**, 왕복 10 sim-sec. SDF의 real_time_factor=1.0은 목표값이지 실측 RTF가 아니다.

이전 콘솔에서 gazebo_nav2, YOLO, Bridge, gazebo_gui, RViz2는 **이미 별도 프로세스**로 시작됐다. Actor는 Gazebo 내부 SDF 애니메이션이므로, 새로운 Actor 제어 ROS 노드를 만들기 전에 Gazebo RTF를 측정한다.

## 한 번에 실행하기 — 터미널 A/B만 사용

**터미널 A:** 이전에 Gazebo와 RViz2 화면이 실제 보였던 D08 renderfix Live 원샷을 실행한 채로 유지한다.

**터미널 B:** 아래 Bash 전체를 한 번에 실행한다. Gazebo는 재실행하지 않으며 ROS setup.bash도 외부 strict 셸에서 source 하지 않는다.

~~~bash
(
  set -Eeuo pipefail
  DIAG="$(mktemp --suffix=.py)"
  trap 'rm -f -- "$DIAG"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/axia-robot-safety-student/62ff3a5e74ea2b4fe83cf7a892432bb060c4144c/block_B/day08/tools/d08_actor_rtf_diagnose.py" \
    -o "$DIAG"
  python3 "$DIAG" --seconds 20
)
~~~

진단기는 실행 중인 Gazebo 프로세스 환경에서 GZ_PARTITION을 자동 탐지한다. 여러 세계가 켜져 있거나 탐지 실패 시, 터미널 A의 D04_STUDENT_GUI=1 로그에 나온 **현재** GZ_PARTITION을 그대로 지정한다. 아래는 기존 실행 로그의 예시이며 현재 숫자는 달라질 수 있다.

~~~bash
python3 "$DIAG" --seconds 20 --partition "axia_d04_student_1596_49"
~~~

이 명령은 **위 첫 번째 괄호 코드 블록의 마지막 python3 행을 교체**하는 예시다. 괄호가 끝난 독립 셸에서 임시 DIAG 변수를 재사용하지 않는다.

최근 증거 폴더가 현재 실행과 다르면 같은 마지막 행에 --scene 옵션을 추가하여 실제 scene/student_human_world.sdf.xacro 경로를 지정할 수 있다.

## 결과 해석

RTF 통계 메시지 3개 이상을 실제 수집한 경우 다음 출력 패턴과 종료코드 0을 기대한다.

~~~text
D08_ACTOR_DIAG_CATEGORY=<아래 카테고리>
D08_ACTOR_RTF_MEDIAN=<실측 수치> samples=<3 이상>
D08_ACTOR_DIAG_CAPTURE_STATUS=CAPTURED
D08_ACTOR_DIAG_EVIDENCE=/home/사용자/axia_d08_diagnostics/rtf_.../
D08_ACTOR_DIAG_ZIP=/home/사용자/axia_d08_diagnostics/rtf_.../d08_actor_rtf_diagnostics.zip
~~~

| 판정 | 의미 | 최소 후속 조치 |
|---|---|---|
| LOW_RTF_CANDIDATE | 실제 Gazebo RTF 중앙값 0.8 미만 | WSLg·GPU/CPU·센서/YOLO 부하 경계 확인 |
| SLOW_ACTOR_TRAJECTORY_CANDIDATE | RTF 정상이나 기본 Actor 속도 약 0.16m/s | D08 전용 waypoint 시간 0/5/10→0/2/4초 후보 |
| RTF_OK_GUI_FPS_UNVERIFIED | 시뮬레이션 시간 정상, GUI FPS 근거는 없음 | 화면 프레임·디스플레이 경계 확인 |
| SIM_PAUSED | Gazebo가 pause 상태 | Pause 상태 조사 |
| SIM_TIME_STALLED | sim_time이 증가하지 않음 | 첫 world clock 실패 조사 |
| RTF_NOT_MEASURED | WorldStatistics 부족 | partition/topic와 GUI 실행 중 여부 확인 |

예시 계산: 실제 RTF가 0.25라면 기본 한 방향 이동 5 sim-sec는 약 20 wall-sec이며, 추정 화면상 속도는 0.04m/s다. **이는 예시이며 Owner의 실제 RTF를 측정한 결과가 아니다.**

종료코드 3은 RTF 증거 부족이며 기존 Gazebo·YOLO 데모 자체의 실패 판정은 아니다. 외부 Actor 프로세스 추가, cmd_vel 발행, pose 명령은 수행하지 않는다.

## 자동 저장되는 증거

새 디렉터리 ~/axia_d08_diagnostics/rtf_UTC_PID/에 다음 파일을 생성한다.

- summary.json: 샘플 수, RTF 중앙/최솟값, sim_time 진행, Actor 속도, 판정과 미검증 상태
- world_stats_raw.txt: 실제 Gazebo topic 통계 원문
- gazebo_topics.txt: 해당 GZ_PARTITION의 조회된 토픽 (라이브 실행에 한함)
- processes.txt: Gazebo·YOLO·RViz 관련 PID/CPU/메모리 1회 스냅샷
- resources.txt: 메모리 및 CPU 개수
- REPORT.md: 요약 보고서
- d08_actor_rtf_diagnostics.zip: 전체 결과 압축

결과 ZIP과 사용자가 육안으로 체감한 이동시간 설명을 함께 분석한다. 로그에 로컬 경로가 포함될 수 있으므로 공개 배포 전 확인한다. 영상/이미지는 수집하지 않는다.

## CI 검증 및 배포 경계

공개 Student PR #45의 L0 테스트는 **합성 WorldStatistics/Actor SDF를 사용**한다. ROS_NOT_RUN / GAZEBO_NOT_RUN. 이 스크립트가 실제 RTF를 측정하는 것은 Owner WSL2 터미널 B에서 실행한 경우뿐이다.

이 과제는 NO_GOAL/NO_CMD_VEL. D06/G07 CM 120ms, Guard 150ms, sensor TTL, 실제 이동·무충돌·SW Stop 또는 인증 HW E-Stop을 검증하지 않는다. 이미 성공한 센서 Live는 보존한다. 사용자 승인 없이 main 병합하지 않는다.
