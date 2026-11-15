# AXIA Block C / C-01 Synthetic 시계열 데이터

C-01은 전류(A)·토크(N·m)·가속도(m/s²) **가상 데이터**를 다룹니다.
실제 TurtleBot3 Waffle의 센서 측정이나 인증된 안전 이벤트가 아닙니다.

- train: 정상 24 traces / 2,400 rows
- validation: 정상 8 traces / 800 rows (임계값 결정)
- test: 14 traces / 1,399 rows (정상 4, 이상 6, 데이터 품질 부족 4)
- seed 2409, 10 Hz, Trace ID 중복 없음
- 학습용 피처: `current_a`, `torque_nm`, `accel_mps2`
- `truth_label`, Trace ID, timestamp는 **모델 입력값이 아닙니다**.
- `SHA256SUMS`는 파일 변조 감지이며 실제 센서 출처의 인증이 아닙니다.

## 실행 (WSL2 Ubuntu 24.04, Python 3.12, pytest 8.3.5)

```bash
bash block_C/scripts/c01_fixture_once.sh --doctor
bash block_C/scripts/c01_fixture_once.sh --check
```

데이터를 재생성하려면 **새로운 빈 목적지 경로**만 사용하세요.

```bash
python3 block_C/fixtures/generator.py --write --output-dir /tmp/axia-c01-generated
python3 block_C/fixtures/generator.py --check --fixture-dir /tmp/axia-c01-generated
```

기존 디렉터리는 덮어쓰지 않습니다. C-01에서는 ROS 2/Gazebo/Goal/cmd_vel 실행이 필요하지 않습니다.
D09~D12 교육 과제의 강사 정답 모델과 Hidden Tests는 별도 비공개 저장소에만 있습니다.
