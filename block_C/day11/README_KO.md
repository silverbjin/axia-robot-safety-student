# AXIA Block C D11 — AutoEncoder 정상상태 재구성과 MSE 이상판정

2026-11-23(월) 19:00–22:00 · 이론 60분 + 실습 120분

**학습목표 1:** AutoEncoder 기반 정상상태 재구성 원리 이해.  
**학습목표 2:** 재구성 오차 기반 이상상태 판정 실습.

- [학생 데모 관찰 가이드](STUDENT_DEMO_GUIDE_KO.md) — 공개 저장소 클론, 데이터/모델/판정 아키텍처, 강사 화면 관찰.
- [학생 상세 120분 실습 가이드](STUDENT_LAB_GUIDE_KO.md) — 실행 명령·코드 해설·예상 출력·오류 복구·제출.
- [독립 MSE 수학 연습](mse_toy_practice.py) — Python 표준 라이브러리만 사용; 모델·체크포인트가 아님.
- [학생 TODO](student_ae_todo.py) — 의도적 NotImplementedError = EXPECTED_RED. 강사 정답 미포함.

처음부터 실행하는 최소 명령(깨끗한 Ubuntu 24.04/WSL2, Python3.12 가정):

~~~bash
mkdir -p "$HOME/axia_d11_course"
git clone https://github.com/silverbjin/axia-robot-safety-student.git \
  "$HOME/axia_d11_course/axia-robot-safety-student"
cd "$HOME/axia_d11_course/axia-robot-safety-student"
bash block_C/scripts/block_c_once.sh --doctor
python3 block_C/fixtures/generator.py --check --fixture-dir block_C/fixtures
python3 block_C/day11/mse_toy_practice.py
~~~

저장소가 이미 존재하면 재클론하지 말고 데모 가이드의 비파괴 갱신 절차를 사용하세요.

**SYNTHETIC_COURSE_FIXTURE**: 합성 Raw 4,599행/46 Trace, 10-sample Window, 6특징, Train240/Valid80/Test100 VALID + 4개 INSUFFICIENT_DATA. 실제 TurtleBot3 모터 계측 아님. 교육용 AI Warning은 비인증 신호이며 로봇 SW Stop·인증 E-Stop·Nav2·cmd_vel을 호출하지 않습니다. 공개 CI의 문서/TOY PASS는 학생 TODO 완성이나 WSL2 강사 checkpoint 실행 성공을 뜻하지 않습니다.


## D11 몰입형 라이브 Replay 참여 활동지

[12분 학생 예측·공개형 Replay 활동지](STUDENT_LIVE_REPLAY_ACTIVITY_GUIDE_KO.md): 강사의 오프라인 기록 재생 화면을 보면서 IF/AE 판정을 미리 예측하고, 공개 후 오탐·미탐·품질 부족을 구분합니다. 학습 목표별 기대 효과와 자기점검 문항 포함. 강사 비공개 점수 CSV/체크포인트는 제공하지 않습니다. 학생 필수 제출물은 기존 mse_practice.log + d11_report.md 두 개로 유지합니다.


## D11 추가 배포 — WSL2/venv 및 Google Colab 학생 TODO Notebook (2026-11-23)

- [초심자용 WSL2·Colab Notebook 실습 안내](notebooks/STUDENT_NOTEBOOK_GUIDE_KO.md)
- [WSL2 venv Notebook (학생 TODO)](notebooks/lesson11-autoencoder-student-wsl2-todo.ipynb)
- [Google Colab Notebook (학생 TODO)](notebooks/lesson11-autoencoder-student-colab-todo.ipynb)
- [Google Colab에서 공개 TODO 열기](https://colab.research.google.com/github/silverbjin/axia-robot-safety-student/blob/main/block_C/day11/notebooks/lesson11-autoencoder-student-colab-todo.ipynb)

두 파일은 37셀/코드7셀로 S1~S3 기초 데이터·MSE 연습은 실행 가능하고 **S4~S6은 의도적 EXPECTED_RED**입니다. 완성형 강사 AE 학습·추론 코드와 checkpoint는 강사 비공개 저장소에만 유지합니다. Google Colab 호스팅과 CUDA GPU의 실제 실행은 환경별로 재검증해야 합니다. 교육용 AI WARNING은 인증된 E-Stop·실제 SW Stop이 아닙니다.
