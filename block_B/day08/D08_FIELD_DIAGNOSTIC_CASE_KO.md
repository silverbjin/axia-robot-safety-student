# D08 보충 실습 — 실제 D08 사람 검출 실패에서 데이터 파이프라인 진단하기

**대상:** D08 온라인 4시간 과정의 첫 1시간 안에서 15~20분 사용. **실습 방법:** 아래 공개 CI 증거를 읽고 표를 채운다. 학생 PC에서 ROS/Gazebo를 설치하거나 Goal을 발행하지 않는다.

## 1. 한 장으로 보는 구조

```text
Gazebo human/Contact 모델 ──> Waffle RGB ──> yolo_ros DetectionArray
                                 │                │ class=person?
                                 └─ Depth 32FC1 ─┴─> D05 registered ROI 거리
                                                     │ (관찰/교육용)
LiDAR /scan ──> 공식 Nav2 Collision Monitor ──> Guard ──> 베이스 명령
                         ↑ 별도의 안전 경로
D07 PlannerServer: Nav2 경로 계획 (D08 합성 person_xy와 실제 TF 동기화 증거 없음)
```

**중요:** D08의 Python `integration_todo.py`는 실제 ROS 토픽을 연결하지 않는다. 앞의 그림은 실제 D08 시연 데이터를 **해석하기 위한 구조**다. D08 교육용 STOP/UNKNOWN 출력이 모터 제어·보호 정지의 원인이라고 주장하지 않는다.

## 2. 실제 WSL2 현장 장애 기록 (분석 자료)

| 신호 | 현장 관측 |
|---|---|
| Waffle / 사람 모델 기준 위치 | `x=-2.00m` / `x=-0.58m`, 반지름 약 `0.07m` |
| 초기 전방 거리 | 약 `1.35m` 추정 (현재 시점의 실제 LiDAR 실측은 아님) |
| RGB / Depth 수신 | 80 / 155건 |
| `yolo_ros` 분류 | `umbrella=64`, **`person=0`** |
| D05 유효 거리 | **0건**, `distance_m=null` |
| 최근 RGB/Depth 시간차 | 관측 윈도우 최소 `198ms`; 허용 기준 `50ms` |
| 이전 수신 버퍼의 등록 쌍 | `currently_registered_pair_valid=true` |
| Nav2 Goal | **미발행**. 비전 검사 실패 시 안전하게 차단 |

이 사건에서 가장 먼저 실패한 입구는 **사람 분류 `person=0`**이다. D05 유효 거리 0건은 그 결과일 수 있다. 최근 RGB/Depth 동기화 문제도 별도로 조사해야 하며, 과거 버퍼에 유효한 쌍이 존재한다고 해서 최근 데이터가 신선하다는 증거는 아니다.

## 3. 같은 모델을 가까이 배치한 공개 CI 실측

실제 Gazebo에서 하나의 사람+Contact 모델을 옮긴 뒤, 로봇을 움직이지 않은 상태로 센서를 관찰했다.

| 위치 | 실제 전방 LiDAR | 비전 근거 |
|---|---:|---|
| 근접 배치 `x=-1.63m` | 약 `0.36m` | 새 RGB 영상의 ONNX `person` 원시 후보 8건, 최고 약 `0.55` |
| 원래 위치로 복귀 `x=-0.58m` | 약 `1.41m` | native `set_pose` ACK와 실제 `/scan`으로 복귀 확인 |
| 근접 RGB 영상 ROS 재생 | 해당 영상 | 고정된 upstream `yolo_ros` DetectionArray `person` 검출 3건, 최고 약 `0.55` |

**공개 근거:**
- <https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43117842587> — 실제 Gazebo, Waffle RGB-D/LiDAR, 근접·복귀, NO GOAL
- <https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43118537433> — 같은 근접 영상 픽셀의 ROS Image **재생**에 대한 실제 `yolo_ros` DetectionArray
- <https://github.com/silverbjin/axia-robot-safety-ci-public/pull/58> — 공개 CI 검증 계약 및 Draft PR

**증명의 한계:** 가까운 영상의 분류 성공은 **거리 가설을 지지하지만 원거리 실패 원인의 유일한 증명은 아니다.** 재생 L1은 WSL2에서 카메라/Depth/YOLO가 동시에 실시간 동작한다는 뜻이 아니다. 공개 NO-GOAL L2 역시 비공개 D05, Nav2 이동 Goal, Guard 종단 안전 TTL을 검증하지 않았다.

## 4. 팀 토의 및 제출 (5문장, 코드 작성 없음)

1. `RGB=80`인데 `person=0`이면 어떤 단계부터 조사해야 하는가? (이미지 수신 / 분류 / Depth / Nav2 중 선택하고 근거 작성)
2. `umbrella=64`는 "아무 물체도 안 보인다"는 설명과 왜 다른가?
3. 최근 시간차 198ms와 버퍼 `registered_pair_valid=true`가 동시에 기록될 때, **최근 유효 쌍**을 입증하려면 무엇을 측정해야 하는가?
4. 근접 `person` 양성은 왜 실제 안전 정지까지 성공했다는 뜻이 아닌가? LiDAR→Collision Monitor→Guard와 ROS Goal의 독립 증거를 적는다.
5. D08 합성 사례의 `UNKNOWN_REVIEW`를 로봇 자동 재출발 명령으로 바꾸면 안 되는 이유를 쓴다.

실습 종료 시 다음 표를 학생 노트에 작성한다.

| 진단 단계 | 현재 증거 | 판정 (PASS/BLOCKED/NOT_VERIFIED) | 추가로 필요한 증거 |
|---|---|---|---|
| 실제 RGB 수신 | | | |
| 실시간 person DetectionArray | | | |
| 최근 RGB-D 정합 및 D05 거리 | | | |
| LiDAR/Collision Monitor/Guard 종단 | | | |
| Goal 및 odom 정지 | | | |

**강사 확인 포인트:** 최초 실패 위치와 최초 시간차 위반을 구별하는가? `UNKNOWN`을 `CLEAR`나 SW 인증 E-Stop으로 오인하지 않는가? 공개 CI의 검증 레벨(L0, Gazebo NO-GOAL L2, 재생 L1, WSL2 미검증)을 구분하는가?

이 문서는 **합성 D08 실습의 보조 진단 자료**다. 교육생에게 비공개 정답 저장소를 제공하거나 Gazebo에서 강제로 이동 Goal을 실행시키지 않는다.
