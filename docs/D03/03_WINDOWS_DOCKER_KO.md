# D03 Windows 10/11 Docker Desktop (학생용)

공식 Docker Desktop Windows 지원조건: https://docs.docker.com/desktop/setup/install/windows-install/
Settings → General에서 WSL2 based engine을 확인하고 WSL Integration에서 Ubuntu-24.04를 활성화합니다. WSL 내부에 Docker Engine을 중복 설치하지 않습니다.

WSL2 Ubuntu 터미널:

~~~bash
docker version
docker compose version
git clone --branch D03 --single-branch https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student
~~~

강사가 Docker Hub 이미지의 실제 빌드·Push 및 Digest를 확인한 경우에만:

~~~bash
docker compose -f setup/d03/compose.student.yaml pull
docker compose -f setup/d03/compose.student.yaml run --rm lab bash
bash block_A/day03/scripts/run_lab.sh preflight
bash block_A/day03/scripts/run_lab.sh red
~~~

예상 RED: 22 failed, 8 passed. 학생 완료 시 공개 30 passed. 이미지가 미배포라면 WSL2 Python venv로 필수 실습을 수행합니다. Docker GUI·GPU·물리 로봇 제어는 이 과제에서 검증하지 않습니다.
