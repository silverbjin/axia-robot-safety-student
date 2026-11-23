# AXIA D11 — 학생용 WSL2 / Google Colab Jupyter Notebook 실습 가이드

**수업:** 이상탐지 기반 위험상태 모니터링 · 180분(이론60분+실습120분), 초·중급자.  
**학습목표:** ① AutoEncoder 기반 정상상태 재구성 원리 이해 ② 재구성 오차 기반 이상상태 판정 실습.  
**데이터:** SYNTHETIC_COURSE_FIXTURE와 연계한 독립 합성 예제. 실제 로봇 센서 계측이나 ROS/Gazebo 시연이 아닙니다.

## 1. 학생용 Notebook 두 종류

| 실행환경 | 공개 실습 파일 | 주의 |
|---|---|---|
| WSL2 Ubuntu 24.04 | [lesson11-autoencoder-student-wsl2-todo.ipynb](lesson11-autoencoder-student-wsl2-todo.ipynb) | 첫 셀에서 venv 설치·커널 전환 |
| Google Colab | [lesson11-autoencoder-student-colab-todo.ipynb](lesson11-autoencoder-student-colab-todo.ipynb) | 현재 Colab 런타임 사용, GPU 옵션 |

**중요:** 37셀/코드 7셀로 구성되며 S1~S3은 실행 가능한 기초 실습이고 S4~S6은 학생 구현용 **EXPECTED_RED**입니다. 전체 AE 학습 완료·추론 PASS로 주장할 수 없습니다. 학습된 완성형 AE 정답과 원래 실행 결과는 **강사 정답 비공개** 정책에 따라 강사 비공개 저장소에만 보관됩니다.

## 2. WSL2: 리포지토리 클론부터 Notebook 열기

Ubuntu WSL2에서 다음 전체 블록을 실행합니다. 기존 작업 파일 삭제나 강제 Git reset은 하지 않습니다.

~~~bash
(
  set -Eeuo pipefail
  ROOT="$HOME/axia_d11_course/axia-robot-safety-student"
  mkdir -p "$(dirname "$ROOT")"
  if [[ ! -d "$ROOT/.git" ]]; then
    git clone https://github.com/silverbjin/axia-robot-safety-student.git "$ROOT"
  fi
  cd "$ROOT"
  if [[ "$(git branch --show-current)" = main &&
        -z "$(git status --porcelain)" ]]; then
    git pull --ff-only origin main
  fi
  echo "SOURCE_SHA=$(git rev-parse HEAD)"
  bash block_C/scripts/block_c_once.sh --doctor
  python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
) || echo "D11_ENV_HOLD: 첫 번째 실패 단계부터 점검하십시오."
~~~

소스의 위치는 `block_C/day11/notebooks/lesson11-autoencoder-student-wsl2-todo.ipynb`입니다. VS Code Jupyter나 JupyterLab에서 이 파일을 엽니다. 첫 번째 코드 셀의 환경 옵션은 `TORCH_VARIANT=cpu`(기본), `DEVICE_MODE=auto`(가능한 장치 자동 선택), `cpu` 또는 `cuda`(GPU 필수)입니다. venv/패키지를 설치했어도 실행 중 커널은 자동 전환되지 않습니다. 전용 venv 커널을 선택한 뒤 다시 실행하여 `[PASS SETUP]`을 확인합니다. 첫 설정 셀에서 `SETUP_HOLD`가 나오면 아직 실행환경 준비가 끝나지 않은 상태입니다.

## 3. Google Colab에서 바로 열기

1. [Colab](https://colab.research.google.com/) 접속 → **파일 → 노트 업로드** → `lesson11-autoencoder-student-colab-todo.ipynb` 선택.
2. GPU 사용을 원하면 **런타임 → 런타임 유형 변경 → GPU**에서 가능한 장치를 선택합니다. GPU 할당 여부는 개인 런타임에 따라 다릅니다.
3. 첫 셀의 `DEVICE_MODE`를 `auto`, `cpu`, `cuda` 중 선택합니다. GPU가 없는데 `cuda`를 강제하면 CPU로 성공 처리하지 않고 HOLD가 되어야 합니다.
4. **런타임 → 모두 실행** 후 S1~S3 출력과 shape를 관찰합니다. S4~S6의 `[EXPECTED_RED]` 메시지는 미구현 상태입니다.
5. Colab은 WSL2 venv를 생성하지 않고 현재 런타임을 사용합니다. 부족한 패키지만 설치하며, 설치 후 재시작이 필요하면 안내에 따릅니다.

**주의:** Colab 호스팅 서비스의 실제 GPU 실행은 아직 검증되지 않았습니다. GPU 런타임을 선택했다고 코드가 자동으로 CUDA를 사용했다고 가정하지 말고 첫 셀의 실제 device 결과를 확인합니다.

## 4. S1~S6 코드·shape·출력 해설

| 단계 | 무엇을 배우나요? | 주요 shape와 검증 | 배포 상태 |
|---|---|---|---|
| S1 | 전류·토크·가속도 합성 센서 Raw 생성 | 4,599 Raw / 46 Trace | 실행 가능한 기초 코드 |
| S2 | Trace 경계·품질 검사·10샘플 Window·6특징 | Train (240,6), Valid (80,6), Test VALID (100,6), 품질 문제4 | 실행 가능한 기초 코드 |
| S3 | 정상 Train-only scaler 및 MSE 손계산 | MSE 0.01/1.00(TOY) | 실행 가능한 기초 코드 |
| S4 | Encoder 6→8→3, Decoder 3→8→6 정상 재구성 학습 | 출력과 입력 모두 (batch,6), loss 변화 | **TODO EXPECTED_RED** |
| S5 | 정상 Valid-only 95% cutoff 및 Test 평가 | NORMAL/WARNING/INSUFFICIENT_DATA 구분 | **TODO EXPECTED_RED** |
| S6 | D10 Isolation Forest와 AE 비교 | VALID100 혼동행렬, 품질 불량4 미점수 | **TODO EXPECTED_RED** |

S1~S3은 모델을 새로 훈련하는 과정이 아닌 공통 데이터·수학 준비입니다. S4~S6에서 `raise NotImplementedError`가 있는 학생 함수를 완성하고 별도 테스트를 실행해야 전체 모델 학습·추론 결과를 주장할 수 있습니다. 기존 `block_C/day11/student_ae_todo.py`도 별도 미구현 상태를 그대로 유지합니다.

**데이터 누수 방지:** StandardScaler.fit은 정상 Train에서만, cutoff는 정상 Valid에서만, Test는 마지막 평가에서만 사용합니다. 모델 score와 timestamp가 부정확한 4개 품질 오류 사례는 점수가 아닌 `INSUFFICIENT_DATA`입니다. 값 0으로 NORMAL 처리하지 않습니다.

## 5. 오류 복구표

| 첫 증상 | 의미 | 권장 조치 |
|---|---|---|
| Git clone 실패 | 저장소 경로 또는 네트워크 오류 | Git URL·네트워크 확인, 기존 소스 삭제 금지 |
| Python 패키지 부족 | 설치 중인 환경과 실제 커널이 다를 수 있음 | 첫 코드 셀·Python 경로·venv 커널 점검 |
| `SETUP_HOLD` | 가상환경 전환 완료 전 | 새 커널 선택 후 재시작 |
| GPU unavailable | 현재 런타임에 CUDA 장치가 없음 | `cpu` 또는 `auto`를 선택하거나 GPU 런타임 점검 |
| `EXPECTED_RED S4/S5/S6` | 학생 TODO 미구현 | 정상 출발점, 목표 shape와 검증 조건을 보고 구현 |
| shape AssertionError | 데이터·모델 입출력 계약 위반 | 오류 발생 첫 셀, 입력 크기와 dtype 확인 |
| INSUFFICIENT_DATA | 센서/시간 품질 불량 | 점수를 임의로 0으로 대체하지 않음 |

## 6. 보고서와 학습 효과

기존 [초심자 상세 실습 가이드](../STUDENT_LAB_GUIDE_KO.md)와 [12분 Replay 학생 활동지](../STUDENT_LIVE_REPLAY_ACTIVITY_GUIDE_KO.md)를 함께 활용합니다. 기본 제출물은 **mse_practice.log + d11_report.md 두 개**입니다. 추가로 TODO를 구현했다면 실행환경, Git SHA, 실제 학습·검증 stdout를 보고서에 기록합니다.

자기 점검 질문: ① Trace와 Window의 차이는 무엇일까요? ② 왜 여섯 특징인가요? ③ 6→8→3→8→6은 어떤 데이터를 복원하나요? ④ MSE를 어떻게 계산하나요? ⑤ Valid와 Test를 왜 분리하나요? ⑥ IF와 AE 원점수 크기를 직접 비교해도 될까요?

**안전 범위:** 교육용 WARNING은 실제 SW Stop이나 **인증된 E-Stop**이 아닙니다. ROS2 Jazzy, Gazebo Harmonic, 실물 Safety Supervisor 또는 Nav2 제어권을 실행·검증하지 않습니다.
