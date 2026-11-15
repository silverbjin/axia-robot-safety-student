# D11 — fit CPU AE with train-only scaler, validation MSE threshold, held-out test

이론 60분 / 실습 120분. 합성 데이터(SYNTHETIC_COURSE_FIXTURE)만 사용합니다. 실제 TurtleBot3 측정이나 인증된 E-Stop이 아닙니다.

1. 프로젝트 루트에서 `bash block_C/scripts/block_c_once.sh --doctor`로 환경을 확인합니다.
2. fixture의 SHA256과 train/valid/test 분리를 확인합니다.
3. `student_ae_todo.py`의 TODO를 구현합니다.
4. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q block_C/tests/test_student_task_expected_red.py`로 RED→GREEN 진행을 기록합니다.
5. 출력 파일과 시간·trace 품질 위반의 최초 지점을 보고합니다.

학생의 TODO는 완성 전 EXPECTED_RED이며 공개 CI의 PASS는 이 함수의 정답 구현을 의미하지 않습니다.
