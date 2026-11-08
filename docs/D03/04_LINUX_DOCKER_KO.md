# Linux — AXIA D03 Docker 설치·실습 가이드

## 적용 범위

- 권장: Ubuntu 24.04 amd64 호스트 + Docker Engine + Docker Compose plugin.
- Ubuntu 22.04 및 다른 Linux 배포판에서도 Docker Engine이 정상 동작하면 **컨테이너의 Linux 사용자 공간**은 Ubuntu 24.04 기반으로 제공됩니다. 호스트 커널/그래픽/장치는 동일하지 않습니다.
- ROS 2 Jazzy와 Gazebo Harmonic을 호스트에 직접 설치하려면 공통 `scripts/install_ubuntu2404_jazzy_harmonic.sh`를 사용하되, **Ubuntu 24.04 amd64**에서만 실행합니다.

## STEP 1 — Docker Engine 설치

Docker의 공식 Ubuntu 가이드에 따라 설치합니다: https://docs.docker.com/engine/install/ubuntu/ . 기존 Docker가 이미 설치되어 있으면 다시 설치하거나 충돌 패키지를 제거할 필요가 없습니다.

새 Ubuntu PC 기준 Docker 공식 명령은 다음과 같습니다. 패키지 제거 명령은 기존 환경에 영향을 주므로 자동 수행하지 않습니다.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF2
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF2
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Docker daemon 확인:

```bash
sudo systemctl status docker --no-pager
sudo docker version
sudo docker compose version
sudo docker run --rm hello-world
# 예상: Hello from Docker! (Docker Engine 자체 동작 확인)
```

Linux docker 그룹 추가는 호스트에 높은 권한을 부여하는 보안 관련 변경입니다. 이 교육 패키지는 자동으로 `sudo usermod -aG docker`를 실행하지 않습니다. 수업 환경이 승인된 경우에만 담당자 지침을 따르고, 그렇지 않다면 `sudo docker ...`로 실행합니다. `build_and_verify.sh`는 일반 사용자에게 docker 접근 권한이 부여된 환경을 전제로 합니다.

## STEP 2 — 이미지 빌드 및 검사 (패키지 압축 해제 루트)

```bash
cd ~/Downloads/AXIA_D03_ENV_SETUP_20261107
bash docker/build_and_verify.sh
# 기대: [PASS] AXIA_D03_ENV_SMOKE, 이미지 ID 출력
```

강사에게 받은 **동일 이미지 아카이브**를 사용하는 경우, 패키지의 `dist/` 폴더에 .tar.gz와 .sha256을 복사한 뒤:

```bash
bash docker/import_image.sh
# checksum OK → docker load → smoke 확인
```

## STEP 3 — 컨테이너에서 학생 실습

```bash
docker compose -f docker/compose.yaml run --rm lab bash
# 내부는 /workspaces/axia
git clone --branch feat/block-a-d01-d03-todo-20261106 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git student
cd student
PYTHONPATH=block_A/day03 python3 -m pytest -q block_A/tests/test_safety_public.py
# 초기 의도된 RED: 10 failed, 1 passed
exit
```

`workspace` 볼륨은 호스트에 남습니다. `ros2` 통신은 컨테이너의 독립 프로세스에서 CLI 학습용으로 제한됩니다. GUI/GPU/USB/실물 로봇은 설정에 포함하지 않았습니다. 네트워크가 필요하다면 Docker 기본 bridge 네트워크를 사용하지만 DDS 외부 참가자 접근은 이 수업 목표에 포함하지 않습니다.

## STEP 4 — 이미지 동일성 기록

```bash
docker image inspect axia-d03:jazzy-harmonic-v1 --format '{{.Id}} {{.Architecture}}'
docker images axia-d03
# 강사는 성공 빌드 이후 bash docker/export_image.sh로 tar.gz + SHA256을 생성
```

**각 학생이 동일한 Dockerfile을 따로 빌드하는 것과 강사 이미지 하나를 공유하는 것은 다릅니다.** 실제 수업 환경의 동일성을 엄격히 요구하면 후자를 선택해야 합니다.

## Linux ARM64 사용자의 제한

`compose.yaml`의 `platform: linux/amd64`로 에뮬레이션을 요청합니다. 성능·Gazebo 실행 가능성을 보장하지 않습니다. 교실에서 단위시험만 진행하는 경우에도 건전성 검사 `axia-smoke`가 PASS인지 확인해야 합니다.