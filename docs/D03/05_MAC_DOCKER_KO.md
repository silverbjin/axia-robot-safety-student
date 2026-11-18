# D03 macOS Docker Desktop (학생용)

공식 설치: https://docs.docker.com/desktop/setup/install/mac-install/
Mac Intel 및 Apple Silicon 모두 Docker를 사용할 수 있지만 본 수업 이미지는 linux/amd64이고 Apple Silicon은 에뮬레이션 성능 저하가 발생할 수 있습니다. Gazebo GUI는 지원/검증 범위가 아닙니다.

~~~bash
docker version
docker compose version
git clone --branch D03 --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
~~~

강사의 이미지 게시·Digest 검증 이후에만:

~~~bash
docker compose -f setup/d03/compose.student.yaml pull
docker compose -f setup/d03/compose.student.yaml run --rm lab bash
bash block_A/day03/scripts/run_lab.sh preflight
bash block_A/day03/scripts/run_lab.sh red
~~~

초기 예상 결과: 22 failed, 8 passed. 완성 후 공개 테스트 30 passed. 이미지가 아직 미배포라면 macOS Python 가상환경에서 순수 Python 필수 실습이 가능합니다.
