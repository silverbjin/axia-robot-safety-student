# Windows 10/11 — AXIA D03 Docker 환경 가이드

## 전제

- Docker Desktop for Windows (공식): https://docs.docker.com/desktop/setup/install/windows-install/
- 최신 Docker Desktop의 Windows 10/11 에디션·빌드 지원 조건을 **설치 당일 다시 확인**합니다. WSL2의 최소 Windows 10 요구와 동일하지 않습니다. Windows 10 Home에서도 WSL2는 사용 가능하지만, Docker Desktop 지원 여부와 Linux 컨테이너 backend 조건을 별도 확인해야 합니다.
- Docker Desktop → Settings → General → WSL 2 기반 엔진 사용. Docker Desktop이 시작되어 있어야 합니다.
- Docker CLI는 Windows **PowerShell에서 실행**할 수 있습니다. 동시에 Ubuntu WSL에 별도 Docker Engine을 설치하지 마세요(엔진 충돌 위험).

## PowerShell 터미널 1 (Docker 앱 먼저 실행)

```powershell
docker version
docker compose version
docker info --format '{{.OSType}}/{{.Architecture}}'
# 기대: linux / x86_64 등 (Linux containers 모드)
```

## 강사가 만든 이미지가 아직 없을 때 — 빌드

```powershell
cd "$HOME\Downloads\AXIA_D03_ENV_SETUP_20261107"
docker compose -f docker/compose.yaml build --pull
docker compose -f docker/compose.yaml run --rm lab axia-smoke
# 기대: [PASS] AXIA_D03_ENV_SMOKE
```

`Compose`의 `platform: linux/amd64`는 OS가 달라도 동일 CPU 아키텍처의 학습 이미지를 사용하기 위한 설정입니다. 최초 빌드 시 인터넷·디스크가 필요하고, CPU가 ARM인 PC는 느릴 수 있습니다.

## 강사 배포 이미지 파일이 있을 때 — 가져오기

강사에게 받은 `axia-d03-jazzy-harmonic-v1-linux-amd64.tar.gz`와 `.sha256`을 패키지의 `dist/` 폴더에 놓습니다. 체크섬 확인과 `docker load`는 Ubuntu WSL Bash 또는 Git Bash에서 `bash docker/import_image.sh`를 실행하면 됩니다. PowerShell만 사용하려면:

```powershell
# 배포한 파일의 SHA256을 강사 제공 .sha256 내용과 비교
Get-FileHash .\dist\axia-d03-jazzy-harmonic-v1-linux-amd64.tar.gz -Algorithm SHA256
docker load -i .\dist\axia-d03-jazzy-harmonic-v1-linux-amd64.tar.gz
docker compose -f docker/compose.yaml run --rm lab axia-smoke
```

## 수업 진행

```powershell
docker compose -f docker/compose.yaml run --rm lab bash
```

컨테이너 안에서는 `ros2 interface show diagnostic_msgs/msg/DiagnosticArray`, `ros2 pkg prefix diagnostic_aggregator`, `axia-smoke`로 사전 확인할 수 있습니다. 컨테이너의 `/workspaces/axia`는 압축해제 디렉터리 아래 `workspace/`와 연결됩니다. 학생 파일만 놓고, 강사 정답·비밀 토큰·실물 로봇 제어코드는 넣지 않습니다.

```bash
cd /workspaces/axia
git clone --branch feat/block-a-d01-d03-todo-20261106 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git student
cd student
PYTHONPATH=block_A/day03 python3 -m pytest -q block_A/tests/test_safety_public.py
# 예상: TODO 미구현인 상태에서 의도된 RED
```

수업 종료 시 `exit`. Compose의 `run --rm`은 컨테이너를 삭제하지만 `workspace/`에 저장된 파일은 보존됩니다. `docker system prune` 또는 `wsl --unregister`는 자료 삭제 위험이 있으므로 수업용 해결책으로 사용하지 않습니다.

## GUI 제한

Windows Docker에서 Gazebo GUI는 기본 설정으로 제공되지 않습니다. 별도 X11/WSLg, GPU 및 DDS 네트워킹 설정 검증이 필요합니다. D03의 필수 목표는 Diagnostics/단위시험이므로 **컨테이너 안에서 실제 주행 실습을 하지 않습니다**.