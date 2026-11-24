# AXIA D12 Jupyter Notebook — 실행·콘텐츠·렌더링 QA 보고서

**검수일:** 2026-11-23 (현재 대화 환경, Asia/Seoul 기준)  
**검수 대상:** `lesson12-risk-state-monitoring.ipynb` 및 `assets/`, 학생/강사 가이드, 저장된 출력, HTML.

## 1. 레퍼런스 분석 — 실제로 열어 본 파일만 사용

- 업로드된 `lesson04-modern-llm-blocks(1).ipynb` — **28셀(설명 22 · 코드 6) / 첨부 그림 8개**.
- 분석 결과: 학습목표 → 문제 제기 → 개념·그림 → 실행 전 코드 설명 → 실제 실행 코드 → 저장된 출력 해설 → 자기 점검의 반복 구조. 원본은 실제 SmolLM2 모델 모듈의 RMSNorm/SwiGLU/RoPE 관찰을 다루므로 모델 출력이나 수치는 **이번 D12로 복사하지 않음**.
- 요청 본문에 “두 Notebook”이라고 표현되어 있지만 실제 이 턴에 업로드된 참고 파일은 **1개**입니다. 제2 참고 Notebook은 자료 미제공으로 분석하지 않았습니다.
- 적용: 연한 파랑·회색, 의미에 따라 청록/황색/분홍/보라, 좌→우 다이어그램, 한국어 코드 전후 해설, Markdown 내부 이미지 attachment.

## 2. 제작 결과 (검증된 파일 기준)

| 항목 | 실제 값 |
|---|---|
| Notebook 전체 셀 | **54** |
| 설명 Markdown 셀 | **43** |
| 실제 실행 Code 셀 | **11** (순서대로 execution_count=1~11) |
| 주요 학습 단계 | **6개** (출처·판정·시간·진단·시각화·피드백) |
| 독립 생성 다이어그램 | **6개** (`assets/01_…`~`06_…`) |
| Notebook 내부 attachment 배치 | **7곳** (shape 그림 1회 재사용) |
| 코드가 실제 생성한 그래프 | **2개** (시간선/상태 분포) |
| 실제 HTML 이미지 총수 | **9개** (= 내부 배치 7 + 그래프 2) |
| 저장된 운영자 피드백 | **2개 JSONL 사건** |
| 최종 Notebook | `lesson12-risk-state-monitoring.ipynb` |
| 최종 HTML | `lesson12-rendered.html` (브라우저 QA용 독립 HTML) |

## 3. 실제 실행 환경

| 항목 | 실행 및 결과 |
|---|---|
| OS | Linux (이 대화의 컨테이너) |
| Python | **3.13.5** |
| NumPy | 2.3.5 |
| Matplotlib | 3.10.8 |
| nbformat / nbclient | 5.10.4 / 0.10.4 |
| nbconvert | 7.17.1 |
| GPU / ROS Jazzy / Gazebo | **불필요·실행하지 않음 (NOT_RUN)** |
| WSL2 Ubuntu24.04 Python3.12 | **실제 이 환경에서 실행하지 않음 (NOT_RUN)** |
| Colab 실행 | **별도 실행하지 않음 (NOT_RUN)** |
| 인터넷 | Notebook 코드 실행에 필요하지 않음; 배포 ZIP에 공개 source/fixture 포함 |

**실행 명령 (실제 수행):**

```bash
cd lesson12
python assets/make_diagrams.py
python assets/build_lesson12.py
python assets/run_and_verify.py
python assets/render_and_qa.py
```

코드를 작성한 뒤 **새 커널**에서 `nbclient.NotebookClient(..., allow_errors=False)`로 처음부터 끝까지 실행했습니다. `outputs/execution_details.json`에 코드 셀마다 실행번호와 실제 표준출력을 저장했습니다.

## 4. 실행·검증 판정

| 대상 | 실제 검사 | 결과 |
|---|---|---|
| 공개 JSONL/계약 원본 | Git blob SHA1로 GitHub 공개 원본 정확 일치·12행·13키 | **PASS L0** |
| 공개 이벤트 계약 | `validate_event` 12건·중복 ID 없음·제어권 거짓 | **PASS L0** |
| 임계값 분류 | 0.39/0.40/0.50/0.51, 품질 `None`, 샘플 12건 일치 | **PASS L0** |
| 품질 오류 거절 | score를 0.0으로 변조한 경우 ValueError | **PASS L0 (의도적 반례)** |
| 시간/중복 EventGate | 2건 수락, 중복/역행 거절, 250ms·250ms+1ns 경계 | **PASS L0, 가상 시각** |
| 교육용 ROS 변환 | topic·레벨 `[0,1,2,3]×3`·no-control | **PASS L0 Python dict** |
| dtype/shape | float64 `(12,)`, int64 `(12,)`, 결측 3 | **PASS L0** |
| 시간선 그래프 | WARNING `0.2,0.6,1.0`; 결측 `0.3,0.7,1.1` | **PASS L0** |
| 분포 그래프 | 각 3건·각 25%·전체 100% | **PASS L0** |
| 실제 피드백 파일 | `operator_feedback.jsonl` 쓰기·재읽기·ID·UTC·비제어 | **PASS L0** |
| 잘못된 피드백 거절 | 존재하지 않는 ID 및 제어권 True | **PASS L0 (의도적 반례)** |
| 실행 에러 저장 출력 | 11개 코드 셀의 error output 0개 | **PASS** |

**검수 스크립트가 집계한 실제 `[PASS]` 출력은 11줄이며**, 각각의 실행 셀에서 `assert`가 통과한 이후 출력합니다.

### 저장된 주요 실제 출력

```text
이벤트 수: 12 / 객체 필드 수: 13
NORMAL=3, CAUTION=3, WARNING=3, INSUFFICIENT_DATA=3
score=0.40, threshold=0.50 → CAUTION
score=0.50, threshold=0.50 → CAUTION
score=0.51, threshold=0.50 → WARNING
중복 사건 → duplicate event_id
Trace 시간 역행 → out_of_order source trace
시간 배열 shape/dtype: (12,) float64
WARNING 합성 시각: [0.2, 0.6, 1.0]
품질 부족 합성 시각: [0.3, 0.7, 1.1]
전체 비율 합계: 100.0 %
DEMO:TST_N_00:002 → INVESTIGATE | control_authority= False
DEMO:TST_N_00:003 → CHECK_QUALITY | control_authority= False
```

**중요:** 실제 출력은 **합성 교육 데이터**의 수치 검사이며, 모델 성능·실제 로봇 위험 발생률·센서→정지 latency를 나타내지 않습니다.

## 5. 그림·Markdown/HTML 렌더링 QA

| 확인 항목 | 실제 결과 |
|---|---|
| nbconvert HTML 출력 | **PASS**, `lesson12-rendered.html` |
| Chromium 브라우저 DOM 렌더링 | **PASS**, **1920×1080** |
| 페이지 가로 스크롤 | 1920px = viewport 1920px, **없음** |
| `<img>` 표시 | **9개**, broken 0, alt 누락 0 |
| JS 페이지 오류 | **0개** |
| 외부 HTTP 요청 | **0개** (오프라인 HTML) |
| 제목 계층 | h1/h2 **15개** 표시 |
| PNG 스크린샷 | **4장** (인트로, 시간/게이트, 그래프, 피드백) |
| 그림 픽셀 | 독립 6개 모두 **고해상도 2340px 가로**, 레이블과 화살표 시각 확인 |
| 한글 글꼴 | 제작 환경 `NanumGothic`; Colab에 CJK 없을 때 그래프 영문 라벨 fallback |

**실제 발생한 렌더 이슈 및 조치:**
1. 최초 다이어그램에서 matplotlib이 `Noto Sans CJK KR` 패밀리명을 찾지 못하여 한국어 글꼴 누락 경고 발생. **`NanumGothic`으로 교체**하고 다시 생성·검사하여 해소했습니다.
2. 기본 `nbconvert` 출력에서 코드가 만든 그래프 2개의 `alt` 텍스트가 누락됐습니다. HTML 후처리에서 2개 그래프의 실제 내용을 설명하는 텍스트를 넣고 재검사했습니다. **최종 HTML alt 누락 0개**입니다.
3. 실행 환경의 관리 정책상 Chromium의 **직접 `file://` 탐색은 차단**되었습니다. 대신 **동일 HTML 소스를 `page.set_content()`로 메모리 로드**해 Chromium의 실제 렌더·화면 크기·이미지·외부 요청을 검수했습니다. 그러므로 **사용자 WSL2의 `file://` 직접 열기 성공은 미검증**으로 남깁니다.
4. nbconvert에 포함된 필요 없는 원격 RequireJS/MathJax `<script src>`를 최종 HTML에서 제거했습니다. Mermaid 스크립트의 **비실행 문자열 URL**은 포함되어 있으나 외부 요청은 실제 0건이었습니다.

스크린샷: `outputs/render_qa/lesson12_intro_1920x1080.png`, `outputs/render_qa/lesson12_stage3_1920x1080.png`, `outputs/render_qa/lesson12_stage5_1920x1080.png`, `outputs/render_qa/lesson12_stage6_1920x1080.png`. 본 보고서는 **실제 브라우저 DOM 렌더링 확인**과 **실제 원격 파일 직접 열기 미검증**을 구분합니다.

## 6. 학습 목표 대응 검수

- **목표 1:** 공개 JSONL→계약→EventGate→Python 진단 payload의 순서와 `DiagnosticArray`·`/rosout` 차이를 코드/그림/출력 설명으로 확인합니다. **실제 ROS 2 Jazzy 통신 검증은 범위 밖**입니다.
- **목표 2:** 실제 합성 이벤트 12건 시각화(2개 그래프)와 운영자 JSONL 2건의 작성·재읽기를 검증했습니다.
- 개별 코드에 목적·입력·출력·설계 이유·예상값·PASS 조건·실제 결과 의미를 기재했습니다. 실습 단계별 초심자 질문/정답을 포함합니다.

## 7. 최종 출고 수준과 미검증 항목

**PASS — 교육용 오프라인 Python·Notebook:** 11/11 코드 셀 실행, 데이터·형상·경계·그림·피드백·HTML 인메모리 Chromium 렌더 검증. **기능별 부분인수만 인정합니다.**

**NOT_RUN / 비대상:** ROS 2 Jazzy DDS 발행/구독, 실제 `/rosout` logger, Gazebo Harmonic 및 TurtleBot3, Nav2 Goal, `/cmd_vel`, Safety Supervisor·Collision Monitor 센서 입력/종단 TTL, 실제 SW Stop·인증된 E-Stop, 사용자 Windows/WSL2·Colab 현장 재실행, 브라우저 직접 `file://` 열기. **이 항목은 PASS로 승격하지 않습니다.**

**참고:** 공식 ROS 2 Jazzy 링크는 Notebook 하단에 수록했으며, 학생·강사 문서는 이 검증 범위를 모두 반영합니다.
