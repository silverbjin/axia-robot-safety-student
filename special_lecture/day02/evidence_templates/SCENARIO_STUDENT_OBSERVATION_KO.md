# DAY 02 — G07 MVP 시나리오 학생 관측 기록지

- 학생 실습 브랜치 / 개인 Git SHA:
- 실제 실행한 원샷 커맨드 및 exit code:
- 대상 Student 릴리스 SHA:
- 성공 원본 Student/Public/CI Run:
- 실패 원본 Student/Public/CI Run:
- 직접 실행 검증 수준: L0 / L1 NOT_RUN / L2 NOT_RUN / L3 NOT_RUN
- 인용한 과거 증거: [링크/정확 SHA]
- AI에 입력한 프롬프트 및 추가로 요구한 증거:

| 장면 | 무엇을 관측했나요? | 관련 ROS 2 토픽/함수 | AI 주장 / 학생 검증 | 원본 직접 / 과거 인용 |
|---|---|---|---|---|
| S01 준비 | | `/scan`, `/safety/scan` | | |
| S02 CLEAR | | `/cmd_vel_pre_guard`, `/cmd_vel` | | |
| S03 SLOW | | Collision Monitor / Guard | | |
| S04 STOP | | `/cmd_vel`, `/odom` | | |
| S05 Goal Cancel | | ActionStatus, exact UUID, odom | | |
| S06 Shutdown | | Nav/Loc ACK, CM exit | | |
| F01/F02 실패 심화 | | Callback/RMW/Clock/Odom | | |

**자가점검:** (1) Source vs RMW received vs Callback 간격 구분 (2) 실제 수치 vs AI의 추정 구분 (3) 최초 TTL 위반 (4) Goal 취소 ACK와 terminal 구분 (5) 소프트웨어 STOP과 인증 E-Stop 구분 (6) L0 PASS를 L2 성공으로 쓰지 않았는지.

**30초 발표문:** "제가 본 MVP는 ______이며, 데이터는 ______→______로 전달됩니다. 가장 인상적인 원본 증거는 ______입니다. 제가 직접 실행해 검증한 부분은 ______이고, 새 Gazebo/WSL2 인수는 ______입니다."
