# AXIA Student — 라이선스 및 배포 가능 범위 확인서

**상태: REDISTRIBUTION_REVIEW_PENDING. 이 문서는 새 소프트웨어 라이선스 부여문이 아닙니다.**

이 독립 학생 저장소에는 교육용 Python TODO·테스트·강의 안내를 게시합니다. 저장소 전체에 일괄 적용되는 저작권자의 라이선스 허락 범위는 현재 확인되지 않았으므로, **본 파일이 추가되었다는 이유로 G12 정식 릴리스 또는 제삼자 자산 재배포를 허가하지 않습니다.** 학생 코드에 부여할 명시적 라이선스는 권리자의 승인을 받은 뒤 별도로 확정합니다.

| 항목 | 현재 확인 범위 | 정식 릴리스 판정 |
|---|---|---|
| 학생용 자체 작성 코드·문서 | TODO 파일과 강의 가이드 파일은 현재 저장소에 존재. 작성자 및 허락 문구 미확정 | **HOLD: 저작권자 및 라이선스 명시 필요** |
| 외부 `yolo_ros` | 참조하는 **고정 SHA `94d2dd500cb26027ee9c019f4d3a02029ac615cc`**의 루트 LICENSE와 package.xml에서 MIT 확인 | 공개 저장소에 소스를 포함하지 않음; 빌드 시 별도 Git checkout |
| YOLO26 `yolo26n.onnx` | Hugging Face 원본 모델 카드가 **AGPL-3.0** 표시 | **HOLD: 실제 사용·배포 조건과 AGPL 의무/상용 라이선스 검토** |
| 공식 Nav2 | Jazzy 원본 루트 LICENSE가 Apache-2.0 / BSD-3-Clause / LGPL-2.1-or-later 등 패키지별 혼합 명시 | 패키지별 license 파일·공지 유지 필요. 이 저장소에서 소스 재배포 안 함 |
| TurtleBot3 | ROBOTIS `turtlebot3` Jazzy 원본 LICENSE에서 Apache-2.0 확인 | Waffle 모델/메시별 독립 이용 조건은 별도 검토 |
| Gazebo Fuel actor 메시 `walk.dae` | 학생 실행기가 외부 URL에서 고정 해시 다운로드, 권리자·재배포 허락 파일 미확인 | **HOLD: 라이선스 미확인·자산 번들 금지** |
| Python pytest | 시험 환경 `pytest==8.3.5`; 패키지 라이선스와 배포 형태는 별도 확인 필요 | 재배포 파일 미포함 |

**원칙:** 외부 모델·메시를 이 저장소나 Release ZIP에 복사·번들하지 않습니다. 다운로드는 각 출처·SHA·사용 조건에 따릅니다. 이 목록은 법률 의견이나 저작권자의 재배포 허가가 아닙니다. 확인 기록은 [THIRD_PARTY_ATTRIBUTION.md](THIRD_PARTY_ATTRIBUTION.md)에 유지합니다.

**최종 상태: G12_LICENSE_CONTENT_COMPLIANCE_PENDING.**
