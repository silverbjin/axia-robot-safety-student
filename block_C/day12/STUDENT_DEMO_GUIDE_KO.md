# AXIA Block C D12 — 학생용 라이브 데모 가이드 (클론부터 운영자 판단까지)

**수업:** 2026-11-24(화) 19:00–22:00 / 이론 60분 + 실습 120분. **대상:** ROS 2·Python 초심자 포함.  
**학습목표 1:** ROS2 알림ㆍ로그ㆍ대시보드 기반 위험 이벤트 모니터링 구조 이해.  
**학습목표 2:** 이상 이벤트 시각화 및 운영자 피드백 실습.

> 이 저장소의 사건은 전부 **SYNTHETIC_COURSE_FIXTURE**(합성 학습자료)입니다. 이 데모의 12행은 **EDUCATION_TRANSPORT_DEMO 가상 점수**이며 D11의 실제 AE 모델 출력이 아닙니다. 실제 TurtleBot3 계측·Nav2·Gazebo 실행·Goal 전송·SW Stop·**인증된 E-Stop**과 무관합니다. AI **WARNING은 정보**이며 로봇을 멈추지 않습니다.

## 0. 시작 전 알아둘 것 — 무엇이 실제로 동작하나요?

~~~text
강사만 보유한 D11 IF/AE 기록 (비공개; 모델 정답/체크포인트 공개 금지)
                  │ [별개 경로, 오늘 학생 PC에서는 실행하지 않음]
                  ╳
학생 공개 sample_events.jsonl (가상 이벤트 12건)
       ├─ [오프라인] Python 표준 라이브러리 → 상태별 수·사건 시간선 → events_view.log
       ├─ [선택: ROS Jazzy] Bridge → /axia/education/diagnostics
       │                         → 실제 DDS Subscriber → verdict.json
       └─ [운영자 실습] 학생이 사건을 검토 → operator_feedback.jsonl

대시보드 설계 시안 ≠ 실제 동작하는 클릭형 Dashboard.
rqt_console = ROS logger가 생성한 로그를 관찰, DiagnosticArray 자체를 자동 로그화하지 않음.
생산 Safety Supervisor/Collision Monitor/Nav2 명령 경로와 연결하지 않음.
~~~

이 데모의 **운영 화면은 터미널 상태 목록/타임라인**입니다. 강사가 보여주는 29장 교안의 대시보드 S25·운영자 피드백 S27은 **미구현 UI 설계 시안**입니다. 운영자 피드백은 오늘 실제로 JSONL 파일에 작성합니다. 시안 화면을 클릭하면 저장되는 것처럼 설명하지 마세요.

## 1. 최초 클론 — WSL2 Ubuntu 24.04

**터미널 1**에서 다음을 순서대로 실행합니다(기존 수정 파일은 지우지 않습니다).

~~~bash
mkdir -p "$HOME/axia_d12_course"
cd "$HOME/axia_d12_course"
if [ ! -d axia-robot-safety-student/.git ]; then
  git clone https://github.com/silverbjin/axia-robot-safety-student.git
fi
cd axia-robot-safety-student
git status --short
git branch --show-current
git rev-parse --short HEAD
python3 --version
~~~

**의미:** clone은 독립된 학생 공개 저장소를 내려받습니다. status는 내 변경을 확인합니다. HEAD는 이 수업의 실제 소스 버전을 기록하는 증거입니다. Python 3.12.x가 기대 환경입니다. 저장소가 이미 있으면 강제로 reset하거나 checkout하지 않습니다. 이후 파일을 찾지 못한다면 **현재 폴더가 이 저장소 루트인지** 먼저 확인합니다.

기존 clone이 깨끗한 main일 때에만 다음을 선택적으로 실행합니다.

~~~bash
if [ "$(git branch --show-current)" = main ] && [ -z "$(git status --porcelain)" ]; then
  git pull --ff-only origin main
else
  echo "D12_LOCAL_CHANGES_PRESERVED"
fi
~~~

## 2. 실행 환경과 고정 입력 확인

~~~bash
mkdir -p "$HOME/axia_d12_course/student_evidence"
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
bash block_C/scripts/block_c_once.sh --doctor
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
p = Path("block_C/day12/ros_transport/sample_events.jsonl")
rows = [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s]
print("D12_SAMPLE_COUNT=", len(rows))
print("D12_LEVEL_COUNTS=", dict(sorted(Counter(x["level"] for x in rows).items())))
print("D12_SOURCE=", rows[0]["source"])
PY
~~~

**예상 출력(실제 실행 전 기준):**

~~~text
BLOCK_C_STUDENT_DOCTOR python=3.12.x role=student ros_required_for_unit=false gazebo_required=false
D12_SAMPLE_COUNT= 12
D12_LEVEL_COUNTS= {'CAUTION': 3, 'INSUFFICIENT_DATA': 3, 'NORMAL': 3, 'WARNING': 3}
D12_SOURCE= SYNTHETIC_COURSE_FIXTURE
~~~

Fixture 체크 성공 메시지는 generator 버전에 따라 다르므로 실제 화면을 증거로 남깁니다. 공개 12행의 input_sha256은 **'a' 64개인 형식 검사용 placeholder**입니다. 실물/원본 무결성 검증을 했다고 기록하면 안 됩니다.

## 3. 12분 몰입형 라이브 데모 큐시트

| 시각 | 강사 화면·조작 | 학생이 먼저 답할 질문 |
|---|---|---|
| 0–2분 | 사건 접수: "경고가 떴다. 로봇이 멈췄는가?" | WARNING과 실제 Stop이 같나요? |
| 2–4분 | 아래 터미널 시간선에서 12행·4상태 표시 | 어떤 event_id가 첫 WARNING인가요? |
| 4–6분 | DEMO:TST_N_00:002 선택 | risk_score=0.9, threshold=0.5의 의미는? |
| 6–8분 | DEMO:TST_N_00:003 표시 | 값이 없으면 NORMAL=0으로 기록해도 되나요? |
| 8–10분 | ROS Jazzy 실제 L1 결과 **또는** 오프라인 log 제시 | 데이터가 전송되었다는 증거는 무엇인가요? |
| 10–12분 | 운영자 피드백 초안 설명 | 사건 ID와 조사 근거를 어떻게 남길까요? |

**같은 파일로 모든 학생이 따라 할 수 있는 화면 명령:**

~~~bash
python3 - <<'PY' | tee "$HOME/axia_d12_course/student_evidence/events_view.log"
import json
from pathlib import Path
p = Path("block_C/day12/ros_transport/sample_events.jsonl")
for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    e = json.loads(line)
    score = "UNSCORED" if e["risk_score"] is None else str(e["risk_score"])
    print(f'{n:02d} | {e["source_timestamp_ns"] / 1e9:4.1f}s | {e["level"]:18s} | {score:8s} | {e["event_id"]}')
PY
~~~

**예상 출력 일부(12행 전체가 출력됨):**

~~~text
01 |  0.0s | NORMAL             | 0.1      | DEMO:TST_N_00:000
02 |  0.1s | CAUTION            | 0.45     | DEMO:TST_N_00:001
03 |  0.2s | WARNING            | 0.9      | DEMO:TST_N_00:002
04 |  0.3s | INSUFFICIENT_DATA  | UNSCORED | DEMO:TST_N_00:003
~~~

**코드 의미:** json.loads는 JSON 문장을 Python dict로 변환합니다. enumerate는 행 번호를 붙입니다. source_timestamp_ns는 **Trace 내부 합성 시각(ns)** 이며 실제 컴퓨터 wall time도 생산 안전 TTL도 아닙니다. None을 UNSCORED로 출력해 품질 실패를 정상값 0으로 위장하지 않습니다.

## 4. 실제 ROS 2 Jazzy 통신 데모(설치된 PC만)

~~~bash
test -f /opt/ros/jazzy/setup.bash && echo D12_JAZZY_INSTALLED || echo D12_ROS_OPTIONAL_FALLBACK
bash block_C/scripts/block_c_once.sh --ros-l1
~~~

Python3.12·Jazzy·rclpy·diagnostic_msgs가 갖춰져야 실제 ROS 시험이 됩니다. **예상 PASS 패턴**(새 WSL2 현장 실측 아님):

~~~text
C05_REAL_ROS_L1 {..."status": "PASS_REAL_ROS_L1_EDUCATION_ONLY", "sample_count": 8, ...}
BLOCK_C_STUDENT_JAZZY_ROS_L1_ONLY_PASS owner_wsl2_verified=false
~~~

8건 수신과 레벨 0/1/2/3, 발행→수신의 실제 DDS 구독, 종료 코드, period_min_ms/max_ms를 **새 실행 로그에서 확인**해야 해당 PC에서 ROS L1이라고 적을 수 있습니다. 공개 CI 과거 성공을 자신의 실습 성공으로 복사하지 않습니다. Jazzy가 없으면 이 단계를 **BLOCKED(환경 미설치)** 로 기록하고 3절 오프라인 로그 실습을 계속합니다.

**CLI 주의:** 수업용 publisher는 약 8건 발행 후 종료하므로 실행이 끝난 뒤 \`ros2 topic echo\`를 하면 토픽을 찾지 못할 수 있습니다. \`rqt_console\`에도 Bridge의 Python \`print\`가 자동으로 이벤트별 ROS 로그로 표시되지는 않습니다. ROS 토픽은 DDS 통신, \`/rosout\`은 ROS 로거의 별도 데이터입니다.

## 5. 운영자 판단 기록 실습(실제로 파일 생성)

~~~bash
python3 - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
src = Path("block_C/day12/ros_transport/sample_events.jsonl")
events = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
first = next(e for e in events if e["level"] == "WARNING")
feedback = {
    "event_id": first["event_id"],
    "operator_action": "INVESTIGATE",
    "reason": "점수 0.9가 교육용 threshold 0.5보다 큼; 실제 로봇 고장 여부는 미확인",
    "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
    "control_authority": False
}
out = Path.home() / "axia_d12_course/student_evidence/operator_feedback.jsonl"
out.write_text(json.dumps(feedback, ensure_ascii=False) + "\n", encoding="utf-8")
print("D12_FEEDBACK_WRITTEN", out, feedback["event_id"])
PY
~~~

**예상:** \`D12_FEEDBACK_WRITTEN ... DEMO:TST_N_00:002\`. 이 파일은 이벤트를 확인한 **사람의 판단 기록**일 뿐 Fault Injector 동작, SW Stop 실행, E-Stop 인증이 아닙니다. 기록 시각은 생성 PC마다 달라집니다.

## 6. 문제 발생 시 1차 확인

| 증상 | 최초 확인 | 다음 행동 |
|---|---|---|
| \`Repository not found\` | 저장소 URL/인터넷 | 학생 공개 저장소 URL 재확인, 강사 private 파일 우회 복사 금지 |
| \`BLOCK_C_ENV_DIFF_BLOCKED\` | \`python3 --version\` | Python 3.12 환경 사용 |
| \`No module named pytest\` | Python/venv | 실습 A는 표준 라이브러리로 먼저 진행 |
| \`D12_ROS_OPTIONAL_FALLBACK\` | \`/opt/ros/jazzy/setup.bash\` | 오프라인 JSONL 제출; ROS 성공 주장 금지 |
| 토픽이 없음 | publisher 이미 종료? | \`--ros-l1\`가 만든 실제 verdict 확인; 동일 오류 무한 재시도 금지 |
| \`NotImplementedError: D12 TODO not implemented\` | 공개 학생 TODO | **EXPECTED_RED**; 기본 120분 실습 실패 아님 |
| \`rqt_console\` 비어 있음 | ROS logger 미발행 | 진단 메시지를 자동 logger와 혼동하지 않기 |

**최종 제출:** \`events_view.log\`, \`operator_feedback.jsonl\`, \`d12_report.md\` (실제/예상 출력 차이, 운영 판단 근거, ROS 검증 수준); ROS를 실행했다면 \`verdict.json\` 경로를 보고서에 기록합니다. 전체 과정은 [120분 초심자 실습](STUDENT_LAB_GUIDE_KO.md)을 참고합니다.

공식 자료: [ROS 2 Jazzy Topics](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html), [ROS 2 Logging](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Logging.html), [diagnostic_msgs](https://docs.ros.org/en/jazzy/p/diagnostic_msgs/index.html).
