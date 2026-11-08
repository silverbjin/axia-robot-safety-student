# D03 학생용 Docker Hub 이미지 빠른 시작 (배포 후 사용)

강사가 Docker Hub에 업로드하고 **digest를 검증한 다음** 이 안내를 배포합니다. 아래 이미지는 아직 강사의 업로드 확인이 필요한 예시입니다.

대상 이미지: `silverbjin/axia-d03-lab:jazzy-harmonic-v1` (linux/amd64)

1. 각 OS에 Docker Desktop 또는 Docker Engine+Compose를 설치하고 `docker info`를 확인합니다.
2. 강사가 제공한 Digest가 있으면 `silverbjin/axia-d03-lab@sha256:<강사 공지 digest>` 형태로 pull합니다. Digest를 받지 않았다면 아래 태그 버전을 사용합니다.

```bash
docker pull --platform linux/amd64 silverbjin/axia-d03-lab:jazzy-harmonic-v1
mkdir -p axia-d03-workspace
cd axia-d03-workspace
git clone --branch feat/d03-p1-diagnostics-adapter-tdd --single-branch \
  https://github.com/silverbjin/axia-robot-safety-student.git

docker run --rm -it --platform linux/amd64 \
  -v "$(pwd):/workspace" -w /workspace \
  silverbjin/axia-d03-lab:jazzy-harmonic-v1 bash
```

컨테이너 내부에서:

```bash
cd axia-robot-safety-student
PYTHONPATH=block_A/day03 python3 -m pytest -q \
  block_A/tests/test_safety_public.py block_A/tests/test_d03_adapter_public.py
```

처음은 의도된 RED, 구현 후 전체 30개 GREEN이 목표입니다. 이 이미지는 강사 정답이나 P1 실제 주행 코드를 포함하지 않으며, ROS 2/Gazebo 전체 인수 성공을 보증하지 않습니다. macOS Apple Silicon에서는 amd64 에뮬레이션으로 속도가 저하될 수 있습니다.