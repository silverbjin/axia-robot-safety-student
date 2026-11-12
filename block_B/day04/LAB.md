# D04 · 11/12 19:00~22:00 — YOLO 사람 검출의 입력 계약

## 목표
1. Bounding Box와 confidence의 차이를 설명한다.
2. 높은 confidence의 사람 검출 1개를 결정하고 경계 오류를 거부한다.
3. **모델 추론 증거**와 **합성 기록 데이터 재생**을 구분한다.

## 준비 / 터미널
기존 [학생용 상세 실습 가이드](D04_STUDENT_LAB_GUIDE_KO.md)와 [공통 Block B 가이드](../README_KO.md)를 따른다. **터미널 1개**에서 시작하고 `.venv`를 직접 사용한다. 이미 clone한 학생 저장소와 기존 YOLO 성공 결과를 재사용한다. ROS/Jazzy가 source되어 있어도 외부 `launch_testing` pytest 플러그인은 차단해야 한다.

## 실시간 Gazebo + YOLO 창 확인 (학습 목표 1의 핵심 시연)

[학생 Gazebo YOLO GUI 실습 가이드](D04_GAZEBO_YOLO_GUI_STUDENT_GUIDE_KO.md)의 **한 번 실행** 절차를 따른다. 공개 학생 프로그램은 공식 Nav2 Waffle + Gazebo Harmonic + ROBOTIS RGB + C++ yolo_ros ONNX를 연결하여 **Gazebo와 Bounding Box 이미지 창**을 연다. Python 사진 한 장 실습 `run_teacher_yolo_demo_once.sh`는 Gazebo GUI를 열지 않으므로 혼동하지 않는다.

저장소 준비 후 학생 GUI 전용 디렉터리에서 실행:

~~~bash
cd "$HOME/axia_d04_student_gazebo_demo"
bash block_B/day04/run_student_gazebo_yolo_once.sh --run
~~~

학생 관찰 체크: Gazebo에서 Waffle과 움직이는 사람 모델, `image_view`에서 사람 Bounding Box, 선택형 RViz2에서 `/scan`, TF, RobotModel과 카메라를 확인한다. 실제 메시지 검증이 되면 `D04_STUDENT_GAZEBO_YOLO_LIVE_PASS`가 출력된다. **사용자 WSL2 GUI 인수는 별도 확인**이며 이 단계를 안전 정지 검증으로 취급하지 않는다.

## 실습 120분 (이론 60분 별도)
1. (20분) `detections.csv` 4행 확인: `f001` person+chair, `f002` 저신뢰, `f003` 정상 검출.
2. (20분) `bash block_B/day04/run_student_fixture_once.sh --fixture`로 `4 passed` 확인 후, `--red`로 `TODO_D04_SELECT_PERSON` 예상 RED 확인. 이때 래퍼의 exit 0은 예상 RED를 정확히 분류했다는 의미이며 학생 구현 GREEN이 아니다.
3. (50분) `block_B/block_b_todo.py::select_person` 구현: `[x1,y1,x2,y2)`, 이미지 크기, confidence 0~1과 min_confidence 포함 경계, 최고 score 선택.
4. (20분) `bash block_B/day04/run_student_fixture_once.sh --green`으로 D04 표적 회귀. 미구현이면 실패가 맞고, 직접 구현했을 때만 `D04_STUDENT_GREEN_PUBLIC_TESTS_PASS`를 확인한다.
5. (10분) 모델 출력 원본과 강사 합성 CSV의 출처·라이선스 차이 기록.

## 예상 출력 / 장애 대응
- TODO 상태 `NotImplementedError: TODO_D04_SELECT_PERSON`: **정상 RED**.
- `Fixture hash mismatch`: 데이터를 수정했거나 체크섬이 달라진 것. 원본을 다시 받으세요. 체크섬 재생성으로 오류를 숨기지 마세요.
- Bounding Box가 이미지 밖이면 함수는 `ValueError`를 내야 합니다. 결과를 조용히 clipping하지 않습니다.
- 모델/영상 설치 불가: CSV 재생으로 실습을 완성합니다(실제 YOLO 검증 아님).
- `No module named 'yaml'` / `launch_testing`: D04 코드 실패가 아니라 ROS의 pytest 플러그인 자동 검색 문제다. 학생 실행기는 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`을 해당 테스트에만 적용한다.
- `LOCAL_YOLO_CPU_ONLY: N persons`, `D04_STUDENT_REAL_IMAGE_LOCAL_CSV_ROWS=N`, `D04_STUDENT_ROS_GAZEBO_NAV2_SAFETY=NOT_RUN`: **이미지 YOLO 추론과 CSV 결과 검사는 성공**, ROS/Gazebo/안전 기능은 이번 실습에서 실행하지 않았다는 뜻이다. `NOT_RUN`은 오류가 아니다.

## 제출
TODO D04 코드, 한 개의 누락/오류 사례 분석, `pytest` 출력 캡처. 정답·Hidden Test는 제공하지 않습니다.
