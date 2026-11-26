# AXIA DAY02 v4 — 40장 워크북 Unit / 프롬프트 / 소스 맵

**A면(홀수 페이지):** 잘못된 AI 답변과 근거 있는 수치·데이터 파이프라인, 학생 질문·기록 칸.

**B면(짝수 페이지):** 완성형 복사 프롬프트, 작성 이유, 실행 명령, 예측 결과, 검토 체크리스트 3개, 노트. **전문 원문은 실제 제작한 PPTX/PDF 및 별도 20 Unit 프롬프트 핸드아웃(대화 첨부)을 참조**하십시오.

| 페이지 | Unit | 핵심 주제 | A면 오류 | B면 검증 결과/질문 |
|---|---|---|---|---|
| 1–2 | U00 | 버전·SHA·CI 계보 | 원본=릴리스=main 오판 | 핀된 실제 SHA 확인 |
| 3–4 | U01 | 실제 4개 ROS 2 패키지 | Nav2 재구현 오판 | 공식/자체 책임 분리 |
| 5–6 | U02 | Node/Topic/Message | /scan=Node 오판 | 실제 타입·출판자 |
| 7–8 | U03 | Gazebo→LiDAR→/safety/scan | 10Hz=100ms 수신 오판 | Bridge/Callback 분리 |
| 9–10 | U04 | Nav2→Supervisor→CM→Guard | Nav2 직접 바퀴구동 오판 | 4개 명령 토픽 확인 |
| 11–12 | U05 | /cmd_vel STOP vs odom ZERO | cmd_vel=0만으로 물리정지 오판 | 1.026s dwell |
| 13–14 | U06 | L0~L3 검증 수준 | L0=새 Gazebo PASS 오판 | 직접/인용/미실행 |
| 15–16 | U07 | Sim/Host/RMW/Callback 시간 | Header=wall 수신 오판 | 시계·출처 분리 |
| 17–18 | U08 | CM120/Guard150/Scan300ms | TTL 완화 유혹 | 안전 경계 불변 |
| 19–20 | U09 | exact Goal UUID 취소·종료 | Cancel ACK=terminal 오판 | CANCELED(5), Nav/Loc ACK |
| 21–22 | U10 | 0/2 실패에서 2/2 성공까지 | 과거 실패=최신 상태 오판 | 동일 SHA쌍 구분 |
| 23–24 | U11 | AI 설명의 파일·함수 검수 | 환각 코드 신뢰 | 실제 Git 경로 확인 |
| 25–26 | U12 | 직접 stdout vs 기대 출력 | 교재 예시=실행 로그 오판 | 명령/rc/SHA 기재 |
| 27–28 | U13 | Git 리뷰·커밋·보고 | 커밋=로봇 인수 오판 | 개인 SHA/미검증 |
| 29–30 | A01 | 실패 소스 pin | 무관한 Run 혼합 | 실제 a04f9a/8e03ac/0/2 |
| 31–32 | A02 | Source/RMW/Observer 계층 | witness 정상=원 수신 정상 오판 | 53.837/54.117/375.941ms |
| 33–34 | A03 | Cycle1/2 최초 위반 | 최후 예외가 원인 오판 | 439.012/362.100ms |
| 35–36 | A04 | 근본원인 가설·반증 | DDS 단일 원인 단정 | UNDETERMINED |
| 37–38 | A05 | RED→GREEN·CI 범위 | L0 GREEN=L2 수리 오판 | 새 L2 2/2 없으면 HOLD |
| 39–40 | A06 | 최종 증거 보고서·인계 | 메모만으로 인수 오판 | SHA·실행결과·미검증 |

## 프롬프트가 필요한 이유

1. **검증 범위 제한:** 기존 완성본을 새로 수정하지 않고 소스/토픽/Goal·증거만 조사합니다.
2. **출처 명시:** Student runtime SHA, Public CI SHA, Run, WSL2 RAW 숫자를 모두 작성합니다.
3. **AI 환각·검증 과장 방지:** 존재하지 않는 경로·L0를 L2로 확대·E-Stop 인증 등을 방지합니다.
4. **실패 심화의 정답 유출 방지:** 0/2 첫 타이밍 경계를 관측하되 FastDDS 근본 원인은 미결정으로 둡니다.
5. **출력 계약:** 변경 파일·명령·실제 stdout·rc·SHA·미검증을 기록합니다.
