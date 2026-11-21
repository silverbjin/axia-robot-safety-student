# AXIA Block C D12 — 학생용 위험 이벤트 모니터링·운영자 피드백

**일정:** 2026-11-24 19:00–22:00 (이론60/실습120). **SYNTHETIC_COURSE_FIXTURE 합성 학습자료만 사용합니다.**

**학습목표 1:** ROS2 알림ㆍ로그ㆍ대시보드 기반 위험 이벤트 모니터링 구조 이해.  
**학습목표 2:** 이상 이벤트 시각화 및 운영자 피드백 실습.

D12는 기존 ROS 2 Jazzy 교육용 \`DiagnosticArray\` 전송을 재사용합니다. 공개 \`sample_events.jsonl\`의 **12개 가상 사건**을 읽고 터미널 상태 목록(최소 대시보드 역할)과 운영자 피드백 JSONL을 작성합니다. 계획 슬라이드의 클릭형 대시보드는 **미구현 시안**입니다. AI **WARNING**은 실제 SW Stop·**인증된 E-Stop**이 아닙니다. \`INSUFFICIENT_DATA\`는 점수 없음이고 정상(NORMAL)과 다릅니다.

## 처음 시작하는 순서

1. [학생용 12분 라이브 데모 가이드](STUDENT_DEMO_GUIDE_KO.md) — 공개 저장소 clone, 12행 확인, 화면 예상 출력, 피드백 1건 작성.
2. [학생용 120분 초심자 상세 실습](STUDENT_LAB_GUIDE_KO.md) — 20:00~22:00 단계별 CLI·코드 해설·실제 ROS/오프라인 fallback·보고서.
3. [학생 미구현 TODO](student_event_todo.py) — **EXPECTED_RED**. 기본 120분 실습 완수 조건에 포함하지 않습니다.
4. [공개 가상 이벤트 12건](ros_transport/sample_events.jsonl) 및 [교육용 ROS 전송 모듈](ros_transport/) — 강사 모델 정답·가중치 없음.

**최초 실행:**

~~~bash
git clone https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
bash block_C/scripts/block_c_once.sh --doctor
# ROS Jazzy가 설치된 경우에만:
bash block_C/scripts/block_c_once.sh --ros-l1
~~~

\`--ros-l1\`의 PASS는 **교육용 ROS DDS 실측**에 한정됩니다. 해당 PC에서 실제 실행하지 않았다면 기존 CI PASS를 자신의 현장 성공이라고 보고하지 마세요. Gazebo/Goal/cmd_vel/생산 Guard TTL을 실행하지 않으며 실제 인증된 E-Stop을 검증하지 않습니다.

**제출:** \`events_view.log\`, \`operator_feedback.jsonl\`, \`d12_report.md\` (ROS 실행 시 \`verdict.json\` 추가). 운영자 기록은 **사람의 조사 의견**이지 로봇 정지 명령이 아닙니다.

**공식 문서:** [ROS 2 Jazzy Topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html) · [ROS Logging](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Logging.html) · [diagnostic_msgs](https://docs.ros.org/en/jazzy/p/diagnostic_msgs/index.html).
