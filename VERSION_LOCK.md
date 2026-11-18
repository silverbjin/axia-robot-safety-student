# AXIA Student — 재현 가능한 버전/출처 Lock

**범위: 학생용 D03 합성 Python TODO 및 Block B D04~D07 학습 소스. 전체 ROS/Gazebo 설치 환경 불변성은 미확정.**

| 요소 | 현재 사용·확인값 | 검증 수준 |
|---|---|---|
| Student Block B 원본 | `d2f16eaf5b5fb60ad9b8009fe1532fa75363e971` | 기존 실제 `main` 파일 고정 |
| Student D03 원본 | `4f74916a09f726ffd6978926adfc83ee9f528298` | 기존 D03의 student TODO 33개 파일 복사 |
| ROS 2 | Jazzy | 선택형 시각 실습 |
| Gazebo | Harmonic | 선택형 시각 실습 |
| OS | Ubuntu 24.04 / Windows WSL2 Ubuntu 24.04 | 선택형 시각 실습 권장 |
| Python | 3.12 | D03 및 Block B Python 합성 실습 |
| pytest | `8.3.5` | 학생 TODO 공개 시험 |
| `yolo_ros` | Git `94d2dd500cb26027ee9c019f4d3a02029ac615cc` | D04 선택형 ROS ONNX |
| YOLO26 ONNX | SHA256 `4f44c33cea12d4b5785e5e7c0a20c13d0c62a77de607ce96a40d6036c7d7bbcf` | 런타임 다운로드 / 모델 AGPL-3.0 |
| Gazebo actor mesh | SHA256 `49af0df3a319d1cb8ca2cebf02dbd00f625e5d5bec820bc5e109925b18b65c6e` | 런타임 다운로드 / 라이선스 미검증 |
| D03 학생 Docker 이미지 | `silverbjin/axia-d03-lab:jazzy-harmonic-v1` | **digest 미확인·이미지 검증 HOLD** |
| ROS Jazzy apt 패키지 | 설치 스크립트의 패키지명 | **정확한 .deb 버전·apt snapshot 미잠금** |

이 파일은 버전/해시 출처를 정리한 문서이며 전체 런타임이 digest로 고정됐다는 뜻이 아닙니다. 필수 Python TODO는 ROS/Gazebo 설치 없이 실행 가능합니다.

**미검증:** 학생용 Docker digest, 일부 ROS apt 정확한 버전, third-party actor 메시 재배포 허락, AGPL-3.0 모델 사용·배포 의무 확인. 해결 전에는 `G12_FULL_RELEASE=HOLD`입니다.
