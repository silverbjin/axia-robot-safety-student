# AXIA Block C — D09~D12 학생용 TODO 실습

SYNTHETIC_COURSE_FIXTURE는 가상 전류/토크/가속도입니다. 실제 Waffle 센서 데이터·안전인증 E-Stop이 아니며, 모든 학생 코드에 `control_authority=false`를 유지합니다.

- D09: C-01 원본 해시와 trace 분할 확인, 10샘플 window/EDA.
- D10: 정상 학습 IF와 정상 검증 threshold, holdout test.
- D11: CPU AE, train-only scaler, 복원 MSE와 IF 비교.
- D12: JSONL fallback과 선택적 Jazzy `DiagnosticArray` 교육 토픽.

시작 명령:

```bash
bash block_C/scripts/block_c_once.sh --doctor
bash block_C/scripts/block_c_once.sh --unit
# 아래 TODO 기능시험은 학생이 구현하기 전 EXPECTED_RED
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q block_C/tests/test_student_task_expected_red.py
```

강사 정답·Hidden Test·모델 가중치는 학생 저장소에 없습니다. 공개 CI는 배포 계약만 검증합니다. `--ros-l1`은 Jazzy 설치 시 선택하며 Gazebo·cmd_vel·Goal은 실행하지 않습니다.
