# AXIA D03 v3 — P1 공유형 ROS Diagnostics · Safe Mode 3시간 실습

**학생 공개 저장소 / 브랜치 D03_v3 / 180분 / ROS 2 Jazzy + Gazebo Harmonic + TurtleBot3 Waffle**

이번 버전에서는 **P1 학생용 소프트웨어 런타임을 함께 제공**한다. 학생이 Gazebo에서 P1 상태·LiDAR 장애·안전정지를 관측하고 두 가지 순수 Python 함수를 구현한다.

- **실습 ① P1 기준선:** 공식 Nav2와 Waffle, P1 Safety Supervisor / Fault Injector / Scenario Verifier를 재사용
- **실습 ② Diagnostics:** P1 JSON 상태 → diagnostic_msgs/DiagnosticStatus(level 0/1/2/3)
- **실습 ③ Safe Mode:** 상태 후보 판단, 보호정지·수동 복구 래치
- **실습 ④ Gazebo:** 사람형 교육용 proxy 8단계 이동, 기존 P1 scan_drop, 실제 P1 상태/odom 관측
- **실습 ⑤ 사건 분석:** 원인 선후관계 증거·HOLD/END 보고서

학생이 수정할 파일은 **block_A/day03/p1_adapter_todo.py** 와 **block_A/day03/todo_safety.py** 두 개뿐이다.
P1 FSM, Command Gate, 공식 Collision Monitor, Fault Injector 코드를 수정하거나 안전 임계값을 완화하지 않는다.

## P1 공유 패키지 설치 및 기본 실행 (먼저 읽기)

**[P1 설치·빌드·Gazebo Waffle 기본 실행 가이드](docs/P1/P1_STUDENT_INSTALL_BASIC_RUN_JAZZY_HARMONIC_KO.md)**

학생에게 공개한 P1/D3 런타임은 `ros2_ws/src/`의 **5개 패키지(49개 파일)**이다. 고정 커밋의 Instructor 원본 45개 파일은 매니페스트로 Git blob SHA를 검증한다. 강사 정답과 Hidden Tests는 포함하지 않는다.

~~~bash
# D03_v3 브랜치 Clone과 ROS Jazzy 공식 apt 저장소 준비 후
cd "$HOME/axia_d03_v3_student"
bash scripts/p1_d03_v3_student_setup.sh --install-deps  # 최초 1회·선택
bash scripts/p1_d03_v3_student_setup.sh --prepare
bash block_A/day03/v3/scripts/classroom.sh launch   # T2, YES-D3-SIM 승인
~~~

이 준비·실행은 **Goal/Fault를 자동 실행하지 않는다**. WSL2 GUI/주행 중 장애 시연은 별도 확인한다.

## 학생용 3시간 가이드

- [전체 180분 실습 가이드](block_A/day03/v3/README_D03_V3_LAB_KO.md)
- [P1 학생 공유 설계/인수 기준](block_A/day03/v3/DESIGN_D03_V3_KO.md)
- [학생 제출용 현장 대응 보고서](block_A/day03/v3/REPORT_D03_V3_KO.md)
- [P1 소스 출처·45개 blob SHA](block_A/day03/v3/P1_RUNTIME_SOURCE_MANIFEST.json)
- [단일 실행 진입점](block_A/day03/v3/scripts/classroom.sh)
- [공개 CI (ROS-free 배포 검증)](.github/workflows/d03-v3-public-ci.yml)

## 최초 준비 (환경 설치는 수업 전)

~~~bash
git clone --branch D03_v3 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git \
  "$HOME/axia_d03_v3_student"
cd "$HOME/axia_d03_v3_student"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pytest==8.3.5
deactivate
bash block_A/day03/v3/scripts/classroom.sh session
bash block_A/day03/v3/scripts/classroom.sh prepare
~~~

위 명령은 **Python/Jazzy/Harmonic/공식 Nav2/TB3와 colcon이 사전 설치**되었다는 전제다. 스크립트는 자식 Bash로 실행하므로 오류 시 상위 터미널은 종료하지 않는다. P1 실제 Goal/Fault는 자동 실행하지 않는다.

~~~bash
# 학생 TODO 시작 (Python 실습)
source .venv/bin/activate
bash block_A/day03/scripts/run_lab.sh inspect
bash block_A/day03/scripts/run_lab.sh red
# 함수 2개 완성 후:
bash block_A/day03/scripts/run_lab.sh green
bash block_A/day03/scripts/run_lab.sh run
deactivate
~~~

기존 TODO 초기 RED는 의도된 단계다. 최종 기준은 공개 필수 테스트 30개 GREEN, 합성 9개 사례 실패 0개다.
ROS Bridge와 Gazebo는 별도 **실제** 실행 확인이 필요하다.

~~~bash
# 도움말: 세션/World 경로/Preview/Live/증거 판정
bash block_A/day03/v3/scripts/classroom.sh --help
~~~

## 배포 및 안전 경계

- 공유 런타임 출처: Instructor 저장소 **0be687ee033233fcd53be1190e0b2f9e86730fc9** 중 공개 가능한 P1+D3 실행 소스 **45개**, Git blob SHA 검증.
- ROS 2 설치 파일은 Git에 복제하지 않고 공식 Jazzy/Nav2/TurtleBot3를 사용한다.
- 강사용 Reference 정답·비공개 채점·인수 증거·자격증명은 배포하지 않는다.
- 교육용 Diagnostics가 OK라고 주행 승인인 것은 아니다.
- **Software Stop과 Collision Monitor는 인증된 하드웨어 E-Stop이 아니다.**
- Gazebo 동적 시연 성공은 실제 GUI·TF/Nav2·P1 Goal·Fault→진단→odom 정지 증거가 갖춰졌을 때만 보고한다.
- 공개 CI는 **배포 검증(ROS-free)**과 **실제 Jazzy/Gazebo Headless 무주행 스모크** 두 가지가 있다. Headless 성공은 WSL2 GUI·Goal 이동·주행 중 장애 정지 PASS를 의미하지 않는다.
- main 브랜치 병합은 운영자 별도 승인 전까지 수행하지 않는다.
