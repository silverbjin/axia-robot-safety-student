# AXIA D12 Incident Command Center — 학생용 실습·사용 가이드

**수업:** 2026-11-24 / ROS2 알림ㆍ로그ㆍ대시보드 기반 위험 이벤트 모니터링 구조 이해 / 이상 이벤트 시각화 및 운영자 피드백 실습.

**안전:** 사건은 모두 SYNTHETIC_COURSE_FIXTURE 교육용 합성값입니다. 야간 02:13은 연출된 시각이고, source_timestamp_ns는 Trace 내부 시간입니다. HTML은 실시간 ROS DDS, Gazebo, Nav2, Goal, cmd_vel, SW Stop 또는 **인증된 E-Stop**을 실행하지 않습니다.

## 1. 무엇을 체험하나요?

단일 HTML에 공개 EDUCATION_TRANSPORT_DEMO **12건**이 내장되어 있어 npm, 서버, 인터넷 없이 브라우저에서 실행됩니다.

~~~text
강사 비공개 D11 AE 기록 104건 ≠ 학생 공개 FAKE 이벤트 12건
[학생] 공개 고정 12건 → Replay/일시정지/예측/정답 공개/필터
                      → 운영자 조치·근거 기록
                      → operator_feedback.jsonl 내려받기/재검증
[별도 ROS] 12건 입력 → C05 Bridge → DiagnosticArray 8건
                    → 독립 Subscriber → ros_l1/verdict.json
~~~

**실시간 ROS DDS 웹 연결은 미구현**이며, HTML에서 구현한 것은 오프라인 합성 Replay와 수기 피드백 기록뿐입니다.

HTML의 '정답 공개'는 미리 정해진 **교육용 사건 레벨**을 보여 주는 것이지 실물 장비의 고장 정답이 아닙니다. 최신 공개 학생 TODO는 의도적으로 EXPECTED_RED 상태를 유지합니다.

## 2. 저장소 클론부터 실행 환경 확인

WSL2 Ubuntu 24.04 터미널에서 다음 블록을 **순서대로** 실행합니다.

~~~bash
mkdir -p "$HOME/axia_d12_course"
cd "$HOME/axia_d12_course"
if [ ! -d axia-robot-safety-student/.git ]; then
  git clone https://github.com/silverbjin/axia-robot-safety-student.git
fi
cd axia-robot-safety-student
pwd
git status --short
git rev-parse HEAD
python3 --version
bash block_C/scripts/block_c_once.sh --doctor
~~~

**해설:** pwd는 현재 작업 폴더, git rev-parse HEAD는 실제 소스 버전, --doctor는 Python 3.12 계약을 점검합니다. **예상 결과:** BLOCK_C_STUDENT_DOCTOR python=3.12.x 및 BLOCK_C_NO_GOAL_NO_CMD_VEL_NO_CERTIFIED_ESTOP. 이 점검은 ROS/Gazebo를 실행하지 않습니다. 기존 변경 파일은 지우지 말고, 깨끗한 main인 경우에만 git pull --ff-only origin main으로 갱신합니다.

## 3. 오프라인 HTML을 Windows 브라우저에서 열기

~~~bash
ls -l block_C/day12/incident_command_center/AXIA_D12_INCIDENT_COMMAND_CENTER.html
explorer.exe "$(wslpath -w "$PWD/block_C/day12/incident_command_center/AXIA_D12_INCIDENT_COMMAND_CENTER.html")"
~~~

Windows 탐색기에서 HTML 더블클릭도 가능합니다. 브라우저 주소는 로컬 **file://** 경로입니다. HTML이 다른 프로그램으로 열리면 Edge/Chrome 브라우저에서 해당 파일을 직접 여세요.

**예상 화면:** AXIA INCIDENT COMMAND CENTER, SYNTHETIC REPLAY, EDUCATION ONLY, NO CONTROL AUTHORITY, NOT LIVE ROS DDS. 전체 12건, 관찰 0건부터 시작합니다.

## 4. 12분 라이브 시연 — 학생이 관제 담당자

| 시간 | 버튼·조작 | 설명·예상 결과 |
|---|---|---|
| 0–2분 | 1건 진행 2회 | 합성 이벤트 2건 관찰, 레벨은 미공개 |
| 2–4분 | 1건 진행 → 세 번째 사건 선택, WARNING 예측 → 정답 공개 | DEMO:TST_N_00:002, 0.90 > 0.50 |
| 4–6분 | 1건 진행 → 네 번째 사건 INSUFFICIENT_DATA 예측 후 공개 | DEMO:TST_N_00:003, 점수 UNSCORED |
| 6–8분 | ▶ Replay / 일시정지 / 속도·상태 필터 | 관찰 순서와 표시 필터의 차이 |
| 8–10분 | 세 번째 사건 선택 → INVESTIGATE / 이유 / 피드백 기록 | 원본 ID와 사람의 판단 연결 |
| 10–12분 | 네 번째 사건 CHECK_QUALITY 기록 → JSONL 내보내기 | 서로 다른 사건 2건 저장 |

**왜 숨기나요?** 학생이 처음부터 사건의 레벨을 읽는 대신 먼저 예상한 후 데이터를 공개하게 하기 위해서입니다. 정답 공개 전에는 상태 필터에도 레벨이 노출되지 않습니다. **다시 시작**은 Replay만 초기화하며 기존 피드백은 유지합니다.

## 5. 가장 중요한 두 사건 비교

| 필드 | WARNING | INSUFFICIENT_DATA |
|---|---|---|
| ID | DEMO:TST_N_00:002 | DEMO:TST_N_00:003 |
| 합성 Trace 시각 | 0.2초 | 0.3초 |
| risk_score | 0.90 | null / UNSCORED |
| threshold | 0.50 | null |
| quality_reason | 없음 | DEMO_SAMPLE_MISSING |
| 운영자 조치 예 | INVESTIGATE | CHECK_QUALITY |

WARNING은 **교육용 이상 후보**이고, INSUFFICIENT_DATA는 **입력 데이터가 부족하여 점수를 낼 수 없음**을 의미합니다. 미점수 사건을 0점/NORMAL로 바꾸면 안 됩니다. 어느 경우도 실제 Stop의 증거가 아닙니다.

## 6. 운영자 피드백 작성·다운로드·다시 불러오기

1. 세 번째 경고 사건을 선택하고 먼저 상태를 예측한 뒤 정답 공개를 누릅니다.
2. 조치를 INVESTIGATE로 선택하고 **5~400자**의 판단 이유를 작성합니다. 예: '교육용 점수 0.90 > 기준 0.50, 실제 고장은 미확인이라 추가 조사 필요'.
3. **피드백 기록** 버튼을 누릅니다.
4. 네 번째 품질 사건에서 CHECK_QUALITY와 데이터 누락 확인 이유를 입력하고 두 번째 기록을 남깁니다.
5. **JSONL 내보내기**를 눌러 operator_feedback.jsonl을 다운로드합니다. 브라우저 다운로드 폴더에 **실제 파일이 생겼는지** 확인하세요.
6. **피드백 JSONL 다시 불러오기**에서 이 파일을 선택합니다. **예상 결과:** 피드백 JSONL 구조·사건 ID·제어권 없음 검증 통과: 2건.

**예상 파일의 한 줄(UTC 시각은 PC마다 다름):**

~~~json
{"event_id":"DEMO:TST_N_00:002","operator_action":"INVESTIGATE","reason":"교육용 점수 0.90 > 기준 0.50","reviewed_at_utc":"2026-11-21T03:00:00.000Z","control_authority":false}
~~~

원본 사건 파일은 수정되지 않습니다. reviewed_at_utc는 **운영자의 실제 기록 시각**이며 합성 Trace 시각과 빼서 안전 반응시간을 계산할 수 없습니다.

## 7. 선택: 공개 샘플 JSONL을 수동 불러오기

**교육용 sample_events.jsonl 불러오기**에서 다음 파일을 선택합니다.

~~~text
block_C/day12/ros_transport/sample_events.jsonl
~~~

앱은 고정 합성 **12건의 모든 필드가 일치**해야만 허용합니다. 새 입력을 불러오면 기존 피드백은 초기화되므로 먼저 내보내세요. **예상 결과:** 교육용 12건 검증·읽기 성공. 외부 서버 전송 없음. 강사 비공개 AE 104건이나 실제 제어 데이터는 불러오도록 설계하지 않았습니다.

## 8. 실제 ROS Jazzy 검증은 별도 실행

Jazzy 설치 PC에서만 아래 명령을 실행합니다.

~~~bash
cd "$HOME/axia_d12_course/axia-robot-safety-student"
export ROS_DOMAIN_ID=92
export AXIA_BLOCK_C_EVIDENCE_DIR="$HOME/axia_d12_course/student_evidence/ros_probe"
bash block_C/scripts/block_c_once.sh --ros-l1
cat "$AXIA_BLOCK_C_EVIDENCE_DIR/ros_l1/verdict.json"
~~~

교육용 C05 Probe는 **8건 수신·레벨 0/1/2/3·발행 종료·수신 주기**를 확인합니다. period_target_ms=100은 목표값이고, period_min_ms/max_ms가 실제 교육용 DDS 수신 간격입니다. 실물 Gazebo, 생산 Safety Supervisor TTL, SW Stop, 인증 E-Stop은 검증하지 않습니다. rqt_console의 /rosout 로그와 DiagnosticArray 전송도 별개입니다. ROS가 없는 PC는 ROS_BLOCKED로 기록하고 오프라인 실습을 계속합니다.

## 9. 문제 발생 시 첫 확인

| 증상 | 먼저 확인 | 대응 |
|---|---|---|
| HTML 없음 | pwd, ls block_C/day12/incident_command_center | 학생 저장소 루트·main 버전 확인 |
| 버튼 무동작 | 브라우저 개발자도구 Console 첫 오류 | 최신 Edge/Chrome으로 file:// 직접 열기 |
| Replay 종료 | 관찰 12/12 | 다시 시작 후 1건 진행 |
| 정답 공개 불가 | 사건 선택·상태 예측 여부 | 예측 선택 후 공개 |
| 피드백 실패 | 공개된 사건인지, 이유가 5자 이상인지 | 근거를 보강 |
| 내려받은 파일 없음 | 브라우저 다운로드 기록 | 파일 저장 여부 확인 |
| 원본 불러오기 거절 | 고정 12건 계약 불일치 | 변경하지 않은 공개 원본 선택 |
| ROS 모듈 없음 | Python3.12, /opt/ros/jazzy/setup.bash | 오프라인 진행, ROS 성공 주장 금지 |
| rqt_console 빈 화면 | DiagnosticArray vs /rosout | 기존 ROS Probe 결과로 확인 |

## 10. 제출과 검증 수준

**필수:** operator_feedback.jsonl **서로 다른 사건 2건**, 기존 D12의 events_view.log, d12_report.md. **가능한 경우에만:** 본인 PC ros_probe/ros_l1/verdict.json.

스스로 답해 보세요: (1) WARNING이 실제 정지를 뜻하나요? (아니요) (2) 왜 데이터 없음과 정상 데이터를 구별하나요? (거짓 NORMAL 방지) (3) 왜 사건 ID와 운영자 피드백을 분리하나요? (원본 증거 보존) (4) 오프라인 Replay가 실제 ROS 수신을 증명하나요? (아니요).

**주의:** 이 HTML과 피드백은 교육용입니다. 실제 로봇 제어 권한이 없고 실시간 DDS 연동도 없습니다. 화면·예상 출력은 학생 PC에서 실제로 확인한 뒤 기록하십시오.
