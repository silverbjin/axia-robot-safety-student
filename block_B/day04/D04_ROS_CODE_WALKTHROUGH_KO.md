# AXIA D04 — 슬라이드 8~10 ROS 2 코드 공개 해설 (학습용 발췌)

> 원본 실행 경로: 강사 비공개 `ros2_ws/src/axia_d04_vision_demo`, ROS 2 Jazzy / Gazebo Harmonic  
> 이 문서는 **수업에서 설명하는 핵심 코드만 공개한 학습용 발췌**이다. 원본 강사 P1 launch, Safety Supervisor, Fault Injector, Scenario Verifier 정답이나 숨김 테스트는 포함하지 않는다.  
> 학생이 **동일한 Python 이미지 YOLO 추론 코드를 실제로 실행**하려면 [`yolo_single_image_demo.py`](yolo_single_image_demo.py)와 [학생 실습 가이드](D04_STUDENT_LAB_GUIDE_KO.md)의 0-B절을 사용한다.

## 8장. overlay.py — 공식 Waffle Pi RGB를 비파괴적으로 추가

강사의 실제 `overlay.py`는 공식 Waffle SDF, Pi 카메라 SDF, world xacro에서 요소를 찾아 **복사한 센서만** 임시 SDF에 추가한다.

~~~python
from copy import deepcopy
import xml.etree.ElementTree as ET

base = ET.parse(waffle)
pi_camera = ET.parse(pi)
link = base.find(".//model/link[@name='camera_link']")
sensor = pi_camera.find(".//sensor[@name='camera'][@type='camera']")
if link is None or sensor is None:
    raise ValueError("Missing official Waffle camera_link or Waffle Pi RGB camera")

sensor = deepcopy(sensor)                # 공식 카메라 정의를 복사
sensor.set("name", "axia_d04_rgb")
link.append(sensor)                      # 기존 조인트/구동 제어는 수정하지 않음
~~~

**관찰 포인트:** `camera_link`는 로봇 본체 구조를 유지하는 위치, `deepcopy`는 공식 센서 정의 재사용, 임시 SDF는 원본 TurtleBot3/ Nav2 파일 보존. 움직이는 사람 Actor는 visual-only로 만들어 물리 접촉·정지 증거가 아니다.

## 9장. config.py — 기존 yolo_ros의 플러그인을 연결

강사 `config.py`는 새 검출 알고리즘을 구현하지 않고 upstream C++ 플러그인에 **입력 토픽·모델·임계값**을 지정한다.

~~~yaml
/yolo/yolo_node:
  ros__parameters:
    use_sim_time: true
    plugins: ["detection", "debug"]
    cameras: ["cam0"]
    cam0:
      rgb_topic: /camera/image_raw
      image_reliability: 2
    detection:
      plugin: yolo_ros/DetectionPlugin
      cameras: ["cam0"]
      model_path: "/실행환경에서_검증한_절대경로/yolo26n.onnx"
      provider: cpu
      threshold: 0.15
      iou: 0.45
      n_threads: 2
      max_fps: 5
    debug:
      plugin: yolo_ros/DebugPlugin
      cameras: ["cam0"]
~~~

**핵심:** `threshold: 0.15`는 실제 ROS/ONNX DetectionPlugin 설정. 학생 필수 함수 `select_person(...,min_confidence=0.5)`는 **별도 합성 CSV 후처리**이므로 같은 파라미터로 취급하지 않는다. `max_fps: 5`는 설정 상한이지 실측 Hz 보장이 아니다. 모델 파일은 강사 런타임에서 SHA256 검증하고 제공한다(이 경로는 실제 존재하는 파일 경로가 아닌 설명용 placeholder).

## 10장. d04_p1_yolo.launch.py — ROS 브리지와 기존 추론기

공개 가능한 핵심 연결은 다음과 같다.

~~~python
from launch_ros.actions import Node

image_bridge = Node(
    package="ros_gz_image",
    executable="image_bridge",
    name="axia_d04_rgb_bridge",
    arguments=["/camera/image_raw"],
    output="screen",
)
# 강사 실행기: 기존 공식 Nav2 + AXIA P1 launch를 별도로 Include
# 강사 실행기: upstream yolo_bringup/launch/yolo.launch.py를 Include
preview = Node(
    package="image_view",
    executable="image_view",
    name="axia_d04_yolo_preview",
    remappings=[("image", "/yolo/cam0/debug_image")],
)
~~~

**실제 데이터 흐름:**

~~~text
Gazebo Waffle Pi RGB
  └── ros_gz_image/image_bridge
        └── /camera/image_raw
             └── /yolo/yolo_node (C++ yolo_ros, ONNX)
                   ├── /yolo/cam0/detections  [yolo_msgs/msg/DetectionArray]
                   └── /yolo/cam0/debug_image [sensor_msgs/msg/Image]
~~~

강사 실행기는 `ROS_DOMAIN_ID=40`과 yolo_ros가 설치된 overlay를 사용한다. 학생이 CLI로 `DetectionArray`를 해석하려면 **`yolo_msgs`를 빌드해 설치한 overlay**를 source해야 한다. 토픽 이름만 발견됐다고 발행 주기나 메시지 내용이 검증된 것은 아니다.

**전체 launch를 학생 개인 PC에서 그대로 실행할 수 없는 이유:** 강사 P1 launch와 안전 계층은 비공개이며 이 발췌는 패키지 전체가 아니다. 다만 YOLO 이미지 1장 추론은 **강사와 동일한 Python 소스**가 학생 공개 저장소에 있어 강사 P1 없이 재현할 수 있다. 원본 학습 목표에 맞춰 범위를 의도적으로 분리했다.

## 21장. YOLO 파이썬 실추론 소스

직접 실행 가능한 전체 원본 코드(강사와 파일 바이트 일치):

- [`yolo_single_image_demo.py`](yolo_single_image_demo.py) — 모델 로드, CPU predict, person 필터, bbox/score CSV, 모델·이미지 해시 manifest
- [`run_teacher_yolo_demo_once.sh`](run_teacher_yolo_demo_once.sh) — 개인 PC 가상환경, 공식 가중치·샘플 사진 캐시, 1회 실행
- [D04 학생 실습 가이드 0-B절](D04_STUDENT_LAB_GUIDE_KO.md) — 실행 순서·예상 결과·오류 처리

이 추론 코드는 `ros2 topic`, `/cmd_vel`, Nav2 Goal 또는 인증 E-Stop을 실행하지 않는다.

## 23·25·27장. 학생이 직접 구현할 코드

- `block_B/fixture_io.py`: SHA256 검사와 **SYNTHETIC_COURSE_FIXTURE** CSV 읽기
- `block_B/tests/test_block_b_public.py`: 입력/예상 예외를 단위 테스트로 정의
- `block_B/block_b_todo.py`: **`select_person()` 한 함수는 TODO**, 학생이 직접 GREEN으로 구현
- `measure_person_range()`는 D05 TODO로 남긴다.

**확인 질문:** “실제 한 장의 이미지에서 YOLO가 만든 사람 후보를 확인했나요? 그리고 같은 의미의 필드로 구성된 **별도의 합성 CSV**에서 올바른 사람 하나를 선택하는 코드를 작성했나요?” 두 결과가 다른 실습이라는 사실까지 설명할 수 있으면 수업 목표를 달성한 것이다.

**원본 공개 기술 자료:** [ROBOTIS TurtleBot3](https://github.com/ROBOTIS-GIT/turtlebot3_simulations), [Nav2](https://github.com/ros-navigation/navigation2), [yolo_ros pinned 94d2dd5](https://github.com/mgonzs13/yolo_ros/tree/94d2dd500cb26027ee9c019f4d3a02029ac615cc), [Ultralytics YOLO26](https://docs.ultralytics.com/ko/models/yolo26). 모델·예제 사진은 공식 라이선스 조건에 따라 학생 PC에만 내려받는다.
