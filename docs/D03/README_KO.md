# D03 — 수업 자료·환경설정 인덱스 (학생용)

## 시작 순서

1. `block_A/day03/README_D03_KO.md`를 읽고 `bash block_A/day03/scripts/run_lab.sh preflight`로 점검합니다.
2. `bash block_A/day03/scripts/run_lab.sh red`로 예상 RED를 확인합니다(22 failed, 8 passed).
3. `p1_adapter_todo.py`와 `todo_safety.py`를 구현하고 `bash block_A/day03/scripts/run_lab.sh green`으로 30/30 PASS를 확인합니다.
4. `block_A/day03/REPORT_TEMPLATE_KO.md`에 Git SHA·원본 출력·검증 범위를 제출합니다.

## 환경설정 선택

- Python 3.12 + pytest 8.3.5만으로 **필수 실습 가능**합니다.
- Windows 10/11은 `docs/D03/02_WINDOWS_WSL_NATIVE_KO.md` 및 `setup/d03/scripts/*`를 선택적으로 사용합니다. 설치 스크립트는 관리자 권한과 재부팅이 필요할 수 있으니 반드시 내용을 읽고 실행하세요.
- Docker는 OS별 `docs/D03/03_...`·`04_...`·`05_...` 가이드를 보세요.
- Docker Hub `silverbjin/axia-d03-lab:jazzy-harmonic-v1`은 빌드/Push 확인 전에는 사용 가능하다고 가정하지 않습니다. 강사가 검증한 digest를 제공한 경우에만 Pull하세요.
- `setup/d03/compose.student.yaml`은 **Pull-only**입니다. Instructor 비공개 원본이나 정답을 포함하지 않습니다.

## 교육 범위

ROS 2 Jazzy + Gazebo Harmonic, TurtleBot3 Waffle의 P1 사례를 **진단용으로 재현**합니다. 학생 과제는 주행·Fault·Start를 호출하지 않으며, SW Stop은 산업용 인증 E-Stop이 아닙니다.

## 배포 기준

Repository: https://github.com/silverbjin/axia-robot-safety-student/tree/D03
최초 공개 D03 실습 baseline: `afbdfdc3df205d373dbae695683b42dacf0632e9`.
추가 문서 반영 HEAD는 `git rev-parse HEAD`로 확인하세요. `main`은 사용자 승인 없이 병합하지 않습니다.
