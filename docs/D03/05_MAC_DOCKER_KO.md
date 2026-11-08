# macOS (Intel / Apple Silicon) — AXIA D03 Docker 실습 가이드

## 지원 원칙

- macOS에는 Ubuntu용 ROS 2 Jazzy apt 패키지를 직접 설치하지 않습니다. Docker Desktop으로 Ubuntu 24.04 사용자 공간의 컨테이너를 실행합니다.
- Intel Mac: `linux/amd64`를 기본적으로 실행합니다.
- Apple Silicon (M1/M2/M3/M4/후속): 이 교육용 Compose는 **`platform: linux/amd64`**를 강제하므로 에뮬레이션을 사용합니다. Docker Desktop에서 x86_64 에뮬레이션이 정상 동작하는지 먼저 확인하십시오. Apple Silicon에서 Gazebo GUI·고부하 Gazebo 시뮬레이션까지 일관되게 된다고 보장하지 않습니다.
- GUI 없는 Python/ROS Diagnostics 학습이 기본 범위입니다. 실제 AXIA P1 안전인수는 Ubuntu amd64 기준으로 별도 수행합니다.

## STEP 1 — Docker Desktop 설치

공식 문서: https://docs.docker.com/desktop/setup/install/mac-install/

1. Mac의 Apple 메뉴 → '이 Mac에 관하여'에서 CPU와 macOS 버전을 확인합니다.
2. Docker Desktop에서 Apple Silicon 또는 Intel 설치 파일을 선택하고 설치합니다.
3. Docker Desktop을 실행하고 사용 약관·권한 절차를 완료합니다.
4. **macOS Terminal**을 열고 다음을 확인합니다.

```bash
docker version
docker compose version
docker info --format '{{.OSType}}/{{.Architecture}}'
# Linux daemon 정보가 출력되어야 합니다.
```

공식 Docker Desktop의 지원 macOS 버전 범위는 업데이트에 따라 변경됩니다. 설치 시 지원되는 macOS 버전을 확인하세요.

## STEP 2 — 교육 패키지 준비 및 Docker 빌드

다운로드한 ZIP의 압축을 해제한 후, macOS Terminal에서 해당 디렉터리로 이동합니다:

```bash
cd ~/Downloads/AXIA_D03_ENV_SETUP_20261107
bash docker/build_and_verify.sh
# 기대: [PASS] AXIA_D03_ENV_SMOKE
```

Apple Silicon에서 첫 실행 시 amd64 에뮬레이션 경고 및 느린 패키지 설치가 나타날 수 있습니다. 이는 시뮬레이션 안정성을 뜻하지 않으며 `axia-smoke`까지 통과한 범위만 기록합니다.

### 사전 빌드 이미지 사용

강사가 `dist/axia-d03-jazzy-harmonic-v1-linux-amd64.tar.gz` 및 `.sha256`을 배포한 경우:

```bash
bash docker/import_image.sh
# checksum 검증 → 로드 → CLI smoke
```

동일성은 이미지 ID, 플랫폼, SHA256을 바탕으로 확인합니다. 이미지 자체가 `linux/amd64`이므로 Apple Silicon에서 호스트 CPU 명령을 에뮬레이션합니다.

## STEP 3 — D03 실습 시작

```bash
docker compose -f docker/compose.yaml run --rm lab bash
# 컨테이너 내부
ros2 interface show diagnostic_msgs/msg/DiagnosticStatus
ros2 pkg prefix diagnostic_aggregator
axia-smoke
cd /workspaces/axia
git clone --branch feat/block-a-d01-d03-todo-20261106 --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git student
cd student
PYTHONPATH=block_A/day03 python3 -m pytest -q block_A/tests/test_safety_public.py
# 초기 RED: TODO_NOT_IMPLEMENTED
exit
```

`workspace/` 디렉터리에 학생 과제가 그대로 남습니다. 위 URL은 **사전 검토 중인 학생용 Draft 브랜치**이므로 정식 배포 전 강사 승인이 필요합니다.

## 문제가 발생한다면

- `Cannot connect to Docker daemon`: Docker Desktop을 시작한 다음 `docker version`을 재시도.
- `no matching manifest for linux/amd64`: 올바른 Docker base image/tag 및 Docker Desktop의 CPU/플랫폼 지원을 점검.
- `exec format error`: 다른 아키텍처의 이미지를 잘못 가져왔거나 에뮬레이션이 지원되지 않는 상태. 강사의 amd64 이미지 재확인.
- Gazebo가 느리거나 시작 실패: GUI·Gazebo 실행은 필수 D03 Python 실습과 구분. 억지로 GPU privileged 옵션을 켜지 말 것.

## Mac에서 하지 않는 일

`--privileged`, `/var/run/docker.sock` 마운트, USB/모터 제어, 실제 `/cmd_vel` Goal, 인증된 하드웨어 E-Stop 주장. Docker는 시험환경 표준화 수단이며 안전 인증 수단이 아닙니다.