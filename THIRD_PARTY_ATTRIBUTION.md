# AXIA Student — 외부 소스·모델·메시 출처 원장

검수 시점: 2026-11-14. 학생 저장소에 **소스·모델 파일을 포함하지 않고**, 실습 런타임에서 별도 다운로드하는 자산도 구분합니다.

| 자산 | 사용 위치 | 고정 값/출처 | 라이선스 확인 | 배포 범위 |
|---|---|---|---|---|
| `yolo_ros` C++/ROS 브리지 | `block_B/day04/run_student_gazebo_yolo_once.sh` | Git `mgonzs13/yolo_ros@94d2dd500cb26027ee9c019f4d3a02029ac615cc` | 해당 SHA 루트 LICENSE 및 `yolo_ros/package.xml` **MIT** | 학생 저장소에는 **포함하지 않음**, 런타임 clone |
| `yolo26n.onnx` | 같은 스크립트 | `https://huggingface.co/unileon-robotics/YOLO26-ONNX/resolve/main/yolo26n.onnx`, SHA-256 `4f44c33cea12d4b5785e5e7c0a20c13d0c62a77de607ce96a40d6036c7d7bbcf` | 모델 카드 **AGPL-3.0** | **재배포/사용 조건 미승인**, 런타임별 확인 |
| Gazebo `walk.dae` actor | 같은 스크립트 | `https://fuel.gazebosim.org/1.0/Mingfei/models/actor/tip/files/meshes/walk.dae`, SHA-256 `49af0df3a319d1cb8ca2cebf02dbd00f625e5d5bec820bc5e109925b18b65c6e` | **확인되지 않음** | 번들 금지, 모델·메시 권리 검토 필요 |
| 공식 Nav2 / Collision Monitor / tb3_sandbox | ROS/Gazebo 시각 실습 | `ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup`, `nav2_minimal_tb3_sim` 설치된 버전 | 공식 Navigation2 루트 LICENSE는 패키지별 혼합, 각각의 `package.xml` 우선 | 공식 설치 패키지 재사용; 교재 코드에 공급원 복제 없음 |
| ROBOTIS TurtleBot3 Waffle Pi | D04 Gazebo 시각 실습 | `ros-jazzy-turtlebot3-gazebo`, 공식 모델 경로 | `ROBOTIS-GIT/turtlebot3` Jazzy 루트 Apache-2.0 | 공식 설치된 모델 참조, 자산 번들 없음 |
| Ultralytics Python 단일 이미지 | D04 선택 강의 | 학생 `block_B/day04/yolo_single_image_demo.py`에서 별도 설치·다운로드 가능 | YOLO 모델 및 가중치는 코드와 별개의 라이선스 | 기본 Python TODO·필수 시험에는 사용 안 함 |

검증한 1차 라이선스 링크:
- `https://github.com/mgonzs13/yolo_ros/blob/94d2dd500cb26027ee9c019f4d3a02029ac615cc/LICENSE`
- `https://github.com/mgonzs13/yolo_ros/blob/94d2dd500cb26027ee9c019f4d3a02029ac615cc/yolo_ros/package.xml`
- `https://huggingface.co/unileon-robotics/YOLO26-ONNX`
- `https://github.com/ros-navigation/navigation2/blob/jazzy/LICENSE`
- `https://github.com/ROBOTIS-GIT/turtlebot3/blob/jazzy/LICENSE`

**HOLD:** 원본 이미지·메시·가중치의 법적 이용 조건은 교재 문서로 자동 승인되지 않는다. AGPL-3.0 의무가 적용되는 배포·네트워크 이용 형태는 실제 제품/강의 배포 방식에 따라 별도 확인한다. 다운로드 시 고정 해시를 유지하고, 외부 링크·라이선스가 달라지면 해당 자산만 재검증한다.
