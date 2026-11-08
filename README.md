# AXIA D03 — P1 MVP 기반 ROS Diagnostics · Safe Mode 통합 실습

**Student 공개 패키지 / 배포 브랜치 `D03` / 2시간 실습 / Python 3.12 기준**

목표: (1) P1의 상태 JSON을 ROS Diagnostics 상태 데이터로 변환하는 과정을 이해한다. (2) 이상 상태에서 단계적인 Safe Mode와 수동 복구 원칙을 구현한다.

> 이 패키지는 **합성 데이터로만 실습**한다. ROS 2·Gazebo 및 실물 로봇이 없어도 필수 실습이 실행된다. `NORMAL_CANDIDATE`와 `DiagnosticStatus.OK`는 주행 승인 아님. 소프트웨어 정지는 인증된 HW E-Stop이 아니다.

## 빠른 시작

~~~bash
git clone --branch D03 --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest==8.3.5
bash block_A/day03/scripts/run_lab.sh preflight
bash block_A/day03/scripts/run_lab.sh inspect
bash block_A/day03/scripts/run_lab.sh red    # TODO 초기 22 failed / 8 passed가 정상
~~~

수정할 파일: `block_A/day03/p1_adapter_todo.py`(핵심 함수 1개), `block_A/day03/todo_safety.py`(핵심 함수 1개). 이외 러너·ROS 브리지·fixture·테스트는 수정하지 않는다.

~~~bash
bash block_A/day03/scripts/run_lab.sh green
bash block_A/day03/scripts/run_lab.sh run
~~~

* 실습 안내: [`block_A/day03/README_D03_KO.md`](block_A/day03/README_D03_KO.md)
* 응용 문제 2개: [`block_A/day03/CHALLENGES_KO.md`](block_A/day03/CHALLENGES_KO.md)
* 결과 보고서: [`block_A/day03/REPORT_TEMPLATE_KO.md`](block_A/day03/REPORT_TEMPLATE_KO.md)
* ROS 선택 실습: `block_A/day03/ros_diagnostics_bridge.py`, `block_A/day03/scripts/d03_synthetic_ros_publisher.py` (격리 도메인, 강사 사전 확인)
* 공개 GREEN CI: `.github/workflows/d03-green-grading.yml` (개인 Fork 또는 D03 대상 PR)

**실행 구분**: ROS runtime, Gazebo, P1 실제 Goal·Fault 인수는 별도이며 학생 테스트 PASS로 대체할 수 없다. 학생에게 강사 정답/Hidden Tests를 배포하지 않는다.