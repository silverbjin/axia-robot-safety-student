# AXIA D15 — Evidence Theater 몰입형 라이브 데모 제작·검증 기록 (교육용)

**목적:** 기존 G07 공개 파생 7단계 숫자 Replay를 **학생 예측 → 숫자 증거 공개 → 합성 수치 반례 판정** 화면으로 고도화한다. 신규 Gazebo/ROS2/Goal/인증 E-Stop 기능을 추가하지 않는다. 이 문서는 개발 단계별 **문제 발생 → 최초 실패 → 최소 수정 → 실제 회귀 출력**을 수업에 활용하기 위한 것이다.

## 1. 범위·변경하지 않은 기준선

- 재사용: `block_D/day15/evidence_review.py`·7단계 `STAGES`·`fixtures/jrcigogl_public_derived.json` 및 기존 G07 제어 토픽·Goal·odom·5개 TTL 파생 수치.
- 보존 fixture Git blob: `ae7d594b5452d96cc8802bc53bc8ad578fe99fb7`. 원본 기계 상태 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING`, 형식 안전인수 false, 실제 GUI 내용 미검증, 인증 E-Stop=false.
- D13/D14의 P/N/U 및 G10은 **합성**. S04는 별도 실제 Gazebo L2. 이전 G07 `jrCIgoGl` 실주행 공개 파생 숫자와 한 세션으로 합치지 않는다.
- 구현은 HTML·CSS·JS 인터랙션이며, **실제 첫 위반 타임스탬프는 미제공**. 순서형(ordinal) 7장면은 원본 시간축이나 물리 애니메이션이 아니다.

## 2. RED → GREEN → REFACTOR → REVIEW → COMMIT 기록

| 단계 | 실제 작업 | 교육 포인트 |
|---|---|---|
| RED | `test_d15_evidence_theater.py` 6개를 **기존 코드 변경 전** 추가. PR #111과 공개 CI #44966719245에서 실패 확인 | 인터랙티브 UI가 없어서 실패하는 정확한 사전 회귀 |
| GREEN | `evidence_theater.py`의 단일 HTML UI 및 `run_lab.py` 연결; 기존 CLI 3파일 경로 유지 | 작은 단위로 코드를 추가하고 기존 공개 증거와 출력을 재사용 |
| REFACTOR | 7장면 수치 재계산·시간 보간 제거, 기존 `offline_replay_html()` 인터페이스 유지, JS 공개 전에는 수치 숨김 | 기존 사용자/테스트 계약을 유지하는 최소 변경 |
| REVIEW 1 | D15 전용 CI #44966819797 성공; BLOCK_D #44966819832 실패 | 첫 통합 실패는 기존 통합 검증기 안의 D15 테스트 개수 18 고정 |
| GREEN 2 | `block_D/tools/verify_student_release.py`에서 D15 테스트 예상 18→24 | 새 6개 테스트 추가에 따라 기대 수만 조정, 안전값 수정 없음 |
| REVIEW 2 | D15 CI #44967035472에서 `Ran 24 tests`, `D15_BROWSER_SCREENSHOT=1920x1080` 및 브라우저 조작 성공. BLOCK_D #44967035452 실패 | 통합 계약의 **또 다른** 하드코딩(`test_block_d_release.py`) 발견 |
| GREEN 3 | `block_D/tests/test_block_d_release.py`의 기대 테스트 개수 18→24 | 동일 오류를 반복 재시도하지 않고 실제 원인 고정 |
| COMMIT | 각 변경은 PR #111 전용 브랜치에 분리 커밋. 공개 CI 게이트 통과 후 병합 준비 | 임계값 완화나 근거 없는 PASS 승격 없음 |

### 재현된 최초 실패와 실제 회귀 증거

첫 통합 실패 출력:
~~~text
RuntimeError: BLOCK_D_RELEASE_CONTRACT_FAIL: D15 tests count wrong
~~~

두 번째 통합 실패 출력:
~~~text
AssertionError: 24 != 18
~~~

실제 공개 D15 테스트 및 Chrome 브라우저 검증 출력(#44967035472):
~~~text
Ran 24 tests in 0.088s
D15_SYNTHETIC_NEGATIVE_DETECTION=5/5
D15_BROWSER_SCREENSHOT=1920x1080
D15_BROWSER_SMOKE_PASS_PREDICT_REVEAL_NEXT_FAULT_SCOPE_NO_ROS_GAZEBO
~~~

이 출력은 **GitHub Actions Ubuntu 24.04에서 Headless Chrome으로 실제 HTML 스크립트를 실행한 결과**이다. 다른 PC의 Windows Edge/Chrome, WSLg/Gazebo GUI 성공까지 의미하지 않는다.

## 3. 파일별 역할과 실행 절차

| 파일 경로 | 목적 |
|---|---|
| `block_D/day15/evidence_theater.py` | 오프라인 단일 HTML·CSS·JS. 예측, 증거 공개, 5개 합성 반례, 반응형 |
| `block_D/day15/run_lab.py` | 기존 공개 파생값/숫자 검증 호출 후 결과 JSON 2개·HTML 1개 생성 |
| `block_D/day15/tests/test_d15_evidence_theater.py` | 7장면·5변조·원본 HOLD·출처·무외부 의존성·기존 파일 경로 회귀 |
| `block_D/day15/tests/browser_smoke_d15.py` | 브라우저가 있으면 예측→공개→다음→반례 판정 수행, 1920×1080 스크린샷 치수 검사 |
| `block_D/day15/STUDENT_EVIDENCE_THEATER_LIVE_GUIDE_KO.md` | 학생 클론부터 12분 시연, JSON 대체, 워크시트 제출 |
| `block_D/tools/verify_student_release.py` 및 `block_D/tests/test_block_d_release.py` | 기존 BLOCK_D 통합 L0의 정확한 테스트 수(24개) 반영 |

~~~bash
cd ~
git clone --branch main --depth 1 https://github.com/silverbjin/axia-robot-safety-student.git axia-d15-theater
cd ~/axia-d15-theater
python3 -m unittest discover -s block_D/day15/tests -p 'test_*.py' -v
python3 block_D/day15/run_lab.py --out /tmp/axia-d15
explorer.exe "$(wslpath -w /tmp/axia-d15/d15_offline_replay.html)"
~~~

Linux CI Chrome 스모크(브라우저가 없는 경우 별도 `NOT_RUN` 출력):
~~~bash
python3 block_D/day15/tests/browser_smoke_d15.py
~~~

## 4. 화면의 인과관계·오해 방지 설계

- **단계 선택:** 7개 장면만 존재하고 자동 시간축·원본 센서 프레임은 생성하지 않는다.
- **예측 후 공개:** 수치는 학생이 선택하기 전 숨겨져 있고, 공개 후 기존 파생 JSON에 들어 있는 필드만 표시한다.
- **거리 막대:** CLEAR/SLOW/STOP의 파생 거리를 최대 CLEAR 대비 비율로 표현한다. 로봇 속도·이동궤적의 시간보간이 아니다.
- **Goal/odom:** CANCELED(5)와 STOP 명령·odom ZERO dwell(≈1.029446s)은 서로 다른 독립 검증 근거다.
- **TTL:** Scan·CM source·CM Observer·Guard age·Guard status는 각자 기준이 있다. 첫 실제 위반 시각 `first_violation_timestamp=null`은 유지한다.
- **Fault Challenge:** 복사된 5개 수치 변조의 `expected_failed_gate`를 맞히는 퀴즈. 로봇에 Fault Injector를 보내는 인터페이스는 없다.
- **상시 표시:** 실제 영상 아님, D13/D14 synthetic/S04 별도, 원본 HOLD, NEW ROS/Gazebo/Goal NOT_RUN, 인증 E-Stop 아님.

## 5. 검증 수준 및 향후 강사 WSL2 확인 항목

**완료된 검증:** 공개 CI Python L0·CLI/JSON 회귀, Headless Chrome 실제 예측/공개/이동/반례 조작·1920×1080 PNG 크기.  
**미검증:** 강사 Windows PowerPoint 강의실 프로젝터·WSL2 Windows 브라우저 현장 화면·새 ROS 2/Gazebo/실물 주행/인증 제동. Chrome CI 브라우저 1회 스모크는 실제 WSL2 GUI 인수와 다르다.

강사 WSL2에서는 한 번의 `git clone`·`python3`·`explorer.exe` 실행으로 수업 도입을 준비하고, 화면 실패 시 JSON 2개로 즉시 전환한다. 학생에게는 원본 공개 파생 증거의 범위를 유지하며 실무 사고를 요구한다.

**관련 배포:** Student PR #111, Instructor 비공개 강사용 상세 가이드는 Instructor 저장소 별도 브랜치와 PR에서 관리. 각 저장소의 `main` 병합은 해당 저장소 CI 및 문서 검토 후에만 시행한다.
