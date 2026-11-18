# D03 Linux Docker (학생용)

공식 Docker 설치: https://docs.docker.com/engine/install/ubuntu/
Docker Engine과 Compose Plugin을 설치한 뒤 테스트합니다.

~~~bash
docker version
docker compose version
git clone --branch D03 --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
~~~

강사가 silverbjin/axia-d03-lab:jazzy-harmonic-v1 이미지의 실제 Hub 게시와 Digest를 확인한 경우:

~~~bash
docker compose -f setup/d03/compose.student.yaml pull
docker compose -f setup/d03/compose.student.yaml run --rm lab bash
bash block_A/day03/scripts/run_lab.sh red
~~~

이미지는 linux/amd64입니다. ARM64 호스트에는 에뮬레이션이 필요할 수 있습니다. 이미지가 미게시된 경우 순수 Python venv 실습을 택합니다. docker 그룹 권한은 높은 시스템 권한에 해당하며 --privileged는 사용하지 않습니다.
