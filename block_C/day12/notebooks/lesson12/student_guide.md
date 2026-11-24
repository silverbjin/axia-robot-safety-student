# AXIA D12 — 학생용 Jupyter Notebook 실습 가이드

**강의 제목:** 이상탐지 기반 위험상태 모니터링  
**일정:** 3시간(이론 60분, 실습 120분) · **대상:** Python/ROS 2 초심자~중급자  
**학습 목표:** (1) ROS 2 알림·로그·대시보드 기반 위험 이벤트 모니터링 구조 이해 (2) 이상 이벤트 시각화 및 운영자 피드백 실습

## 1. 처음 배우는 학생을 위한 준비

- **필수:** Python 3.10 이상, Jupyter Notebook 또는 VS Code의 Jupyter 확장, `numpy` 및 `matplotlib`. 디스크 약 50MB 이상(설치 제외), CPU만으로 실행 가능합니다. 인터넷 없이도 파일을 받은 뒤 진행할 수 있습니다.
- **선택:** Windows 10/11 WSL2 Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic. **이번 Notebook 실행 자체는 ROS/Gazebo가 필요하지 않습니다.** 실제 ROS 수신은 별도 현장 실습으로 구분합니다.
- **중요:** 파일은 모두 **공개 합성 교육용 이벤트**입니다. 실제 로봇/센서/AI 추론 결과가 아닙니다. 경고를 보고 실제 Stop·인증된 E-Stop이라고 결론 내리지 마십시오.
- **전 단계:** D09(Trace·Window), D10(Isolation Forest), D11(AutoEncoder)를 학습한 경우 연결이 쉽습니다. 이번 시간에는 D11 모델을 다시 학습하지 않습니다.

## 2. 처음부터 실행하기 — WSL2 또는 Ubuntu

배포된 `AXIA_D12_lecture12_notebook_bundle.zip`을 작업용 폴더에 보관했다고 가정합니다. **받은 파일의 실제 경로**에 맞게 경로를 바꿔주세요.

```bash
mkdir -p ~/axia_d12_notebook
cd ~/axia_d12_notebook
unzip /path/to/AXIA_D12_lecture12_notebook_bundle.zip
cd lesson12
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
jupyter notebook lesson12-risk-state-monitoring.ipynb
```

**각 명령의 뜻:** `mkdir`은 수업 폴더를 만들고, `unzip`은 Notebook·`assets/`를 함께 풉니다. `venv`는 다른 프로젝트 패키지와 분리된 Python 환경입니다. `pip install`은 이 실습에 필요한 작은 패키지만 설치합니다. 마지막 Jupyter 명령이 브라우저에 Notebook을 엽니다.

**확인:** 현재 작업 폴더 `pwd`는 `.../lesson12`로 끝나고 그 폴더 안에 `assets/event_contract.py`와 `assets/sample_events.jsonl`이 반드시 있어야 합니다. 이 두 파일은 공개 AXIA 학생 저장소의 실제 파일과 **Git blob SHA가 일치하는 복제본**입니다. 파일을 변경하지 마세요.

**Windows PowerShell 직접 실행:** Python이 설치되어 있다면 압축을 풀고 `cd lesson12`, `py -m pip install -r requirements.txt`, `py -m jupyter notebook lesson12-risk-state-monitoring.ipynb`로도 실행할 수 있습니다. **MS Office는 Notebook 실행에 필요하지 않습니다.**

## 3. Google Colab에서 실행하려면

1. `lesson12/` 전체 폴더가 포함된 ZIP을 Google Drive 또는 Colab 세션에 올립니다.
2. `!unzip -q /content/AXIA_D12_lecture12_notebook_bundle.zip -d /content/axia_lesson`으로 풉니다.
3. 런타임 폴더를 `/content/axia_lesson/lesson12`로 맞춥니다(Colab 셀에서 `%cd /content/axia_lesson/lesson12`).
4. `lesson12-risk-state-monitoring.ipynb` 파일을 Colab에서 엽니다. 런타임의 현재 작업 폴더가 `assets/`를 포함하는 `lesson12`인지 `pwd`로 확인합니다.
5. 실행 중 경로 오류가 나면 Notebook 첫 실행 셀의 `ROOT = Path.cwd()`와 `ASSETS = ROOT / "assets"`를 확인합니다. `assets` 폴더 없이 `.ipynb`만 업로드하면 **BLOCKED**로 보는 것이 맞습니다.

**주의:** Colab 버전이나 런타임 구성이 다를 수 있습니다. 기본 matplotlib에 한글 글꼴이 없으면 코드가 그래프 제목/축 라벨을 **영어로 대체**하도록 작성했습니다. Notebook 안의 Markdown 그림은 내부 attachment이므로 별도의 PNG 연결 없이 표시됩니다.

## 4. 첫 실행 순서

Jupyter 메뉴에서 **Kernel → Restart & Run All**(VS Code에서는 Restart Kernel 후 Run All)을 선택합니다. 셀을 건너뛰면 `events`나 `contract` 변수가 없다는 오류가 발생할 수 있습니다. 실습 이전 D09~D11 Notebook 커널 변수는 사용하지 않습니다.

| 단계 | 직접 하게 될 일 | 실제 성공 출력에서 찾을 부분 |
|---|---|---|
| **STEP 1 · 출처 확인** | 공개 JSONL 12줄 읽고 SHA·상태 분포 확인 | `[PASS] 공개 원본 SHA · 12행 ...` |
| **STEP 2 · 판단 규칙** | 0.39/0.40/0.50/0.51 네 숫자의 임계값 구분, 결측 zero-fill 거절 | `[PASS] 경계 수치 4건...`, `insufficient data cannot be scored` |
| **STEP 3 · 시간 기준** | 가상 수신 시각으로 중복·역행·250ms 경계 검사 | `[PASS] EventGate...` |
| **STEP 4 · ROS 진단 구조** | Python dict로 진단 payload 매핑(실제 DDS 전송 아님) | `level: 2`, topic, `[PASS] Python payload 변환` |
| **STEP 5 · 시각화** | `(12,)` 배열과 시간선·상태 분포 그래프 두 장 | WARNING `0.2/0.6/1.0`, 품질 `0.3/0.7/1.1`, 총 100% |
| **STEP 6 · 운영자 피드백** | `outputs/operator_feedback.jsonl`에 기록 2건을 쓰고 다시 읽음 | `[PASS] 운영자 피드백 2건...` |

Notebook의 각 코드 셀 **바로 앞에는 입력·핵심 변수·예상 결과**, **바로 뒤에는 왜 그런 출력인지** 설명이 있습니다. 실행할 때마다 두 설명 사이를 읽으며 따라가세요.

## 5. 각 단계에서 꼭 짚을 질문

### STEP 1 — 사건의 출처부터 확인합니다

**질문:** JSONL 파일의 한 줄은 무엇인가요?  
**설명:** 독립된 사건 하나를 나타내는 JSON 객체입니다. `event_id=DEMO:TST_N_00:002`는 합성 0.2초의 첫 WARNING 사건입니다. 파일 내부 `input_sha256`이 `'a'*64`인 것은 실제 원본 해시가 아니라 교육용 placeholder입니다. 소스 파일의 실제 일치 여부는 Git blob SHA로 따로 확인합니다.

### STEP 2 — 위험과 '데이터 없음'을 나눕니다

**질문:** 0.5 점수와 0.5 임계값이면 WARNING인가요?  
**설명:** 수업 규칙은 `score > threshold`일 때만 WARNING이므로 **CAUTION**입니다. `INSUFFICIENT_DATA`는 `risk_score=None`, `threshold=None`으로 **점수 자체가 없습니다**. 0.0으로 바꾸면 '데이터가 없음'을 '정상'으로 오인하게 됩니다.

### STEP 3 — 시계를 섞으면 안 됩니다

**질문:** 합성 `source_timestamp_ns=200000000`과 지금 PC의 UTC 타임스탬프를 빼면 지연을 알 수 있나요?  
**설명:** 알 수 없습니다. source는 Trace 내부의 상대 시각, PC 시각은 다른 기준입니다. 오늘 EventGate 250ms는 **손으로 구성한 monotonic 값의 단위 테스트**이며 실제 센서/안전 TTL이 아닙니다.

### STEP 4 — ROS payload와 실제 ROS 통신을 구분합니다

**질문:** `payload['level']==2`면 실제 로봇 정지 명령인가요?  
**설명:** 아닙니다. 이것은 `DiagnosticStatus.ERROR`에 대응시키는 **표시 값**입니다. 더구나 이 Notebook은 딕셔너리만 생성하며 ROS를 실행하지 않습니다. `/rosout` 로그는 별도 ROS logger 경로입니다.

### STEP 5 — shape와 시각화 해석

**질문:** `(12,)`는 왜 `(12,13)`이 아니죠?  
**설명:** `seconds`, `scores`를 한 필드씩 추출했으므로 각 배열은 12원소 1차원입니다. JSON dict의 13개 키는 NumPy Tensor 차원이 아닙니다. 상태별 3건, 25%는 데이터 구성이며 실물 고장 확률이 아닙니다.

### STEP 6 — 두 개의 판단 근거를 남깁니다

**질문:** 왜 `operator_feedback.jsonl`을 원본과 별개로 저장하죠?  
**설명:** 사실(원본 이벤트)과 의견(운영자의 조사 이유)을 구별하기 위해서입니다. 두 기록의 `event_id`를 연결하면 다음 근무자가 인계 내용을 추적할 수 있습니다. 피드백 자체에는 **제어 권한이 없습니다**.

## 6. 예상과 실제 출력을 구분하여 제출하기

아래는 **Notebook을 작성한 환경에서 실제 실행해 얻은 대표 결과**입니다. 학생의 환경에서는 Python 버전과 UTC 기록 시각이 다를 수 있습니다.

```text
이벤트 수: 12 / 객체 필드 수: 13
상태: NORMAL=3 CAUTION=3 WARNING=3 INSUFFICIENT_DATA=3
첫 WARNING: DEMO:TST_N_00:002
첫 품질 부족: DEMO:TST_N_00:003
WARNING 합성 시각: [0.2, 0.6, 1.0]
품질 부족 합성 시각: [0.3, 0.7, 1.1]
전체 비율 합계: 100.0 %
운영자 피드백 파일: outputs/operator_feedback.jsonl / 2건
```

**제출물:** 실행 후 출력이 저장된 `.ipynb`, `outputs/d12_event_timeline.png`, `outputs/d12_level_distribution.png`, `outputs/operator_feedback.jsonl`, 그리고 사건 ID·판단 근거·검증되지 않은 범위를 설명한 간단한 보고서.

## 7. 오류 메시지별 첫 확인 지점

| 오류 | 먼저 확인할 것 | 해결 방안 |
|---|---|---|
| `ModuleNotFoundError: matplotlib` 또는 `numpy` | 사용 중인 `python`, venv 활성 여부 | 같은 환경에서 `python -m pip install -r requirements.txt` |
| `BLOCKED: lesson12 ... assets` | `pwd`, `ls assets` | ZIP 안의 `lesson12/`에 들어가 Notebook 실행, assets 함께 유지 |
| `공개 이벤트 파일이 기준 원본과 다릅니다` | 원본 JSONL 변경·문자 인코딩 | 실제 공개 fixture 원본으로 복원. **SHA 비교를 삭제하지 않습니다.** |
| `event schema missing` / `insufficient data cannot be scored` | `event_id`, `risk_score`, `quality_reason` | 실습에서 변경한 가상 데이터를 원본과 구분, 정답 zero-fill 금지 |
| `NameError: events is not defined` | 앞 코드 셀 건너뛰기 | Restart & Run All |
| 그래프 한글 네모 표시 | CJK 글꼴 설치 여부 | 코드의 영어 라벨 fallback 사용, Notebook 그림 설명 확인 |
| `outputs/`에 파일이 없음 | 전체 실행 여부, 디렉터리 쓰기 권한 | STEP 5/6 코드 실제 실행 후 다시 확인 |
| `rclpy` 관련 오류 | Jazzy 미설치/venv 혼용 | **Notebook과 분리된 현장 ROS 실습**으로 분류, Notebook PASS에 포함 금지 |

## 8. ROS 2 Jazzy는 선택적 후속 과제입니다

실제 ROS 2가 설치된 환경에서는 학생 공개 AXIA 저장소에서 기존 `--ros-l1`을 실행할 수 있습니다. 이 Notebook은 해당 명령을 자동 호출하지 않으며, **이 Notebook에 저장된 출력으로 실제 DDS/Gazebo를 검증했다고 주장해서는 안 됩니다.** 안전제어 노드·Goal·cmd_vel도 생성하지 않습니다.

## 9. 자기 점검 정답의 핵심

1. WARNING ≠ 실제 안전 정지.
2. score 0.50, threshold 0.50 → CAUTION (엄격 초과가 아님).
3. 점수 없는 품질 결손을 NORMAL로 바꾸지 않음.
4. 서로 다른 시계 기준의 숫자를 바로 빼지 않음.
5. Payload dict 작성 ≠ ROS DDS 메시지 실제 송수신.
6. 피드백 파일은 사건 ID로 원본에 연결하되 원본을 덮어쓰지 않음.

**참고:** Notebook 마지막의 ROS 2 Jazzy 공식 문서 링크 및 공개 AXIA 이벤트 계약 파일을 참조하세요.
