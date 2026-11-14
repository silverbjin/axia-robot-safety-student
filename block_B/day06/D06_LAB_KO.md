# D06 Safety Bubble — 교육생 실습 (11/16, 3h)

학습 목표: (1) CLEAR/SLOWDOWN/STOP/UNKNOWN 규칙과 거리 경계를 설명한다. (2) Nav2 Collision Monitor의 stop/slowdown polygon·source 설정을 구별한다. (3) 교육용 range fixture와 실제 속도 제한·안전 인증의 차이를 설명한다.

환경: Python 3.12/pytest. **GPU, 카메라, Gazebo 및 로봇 이동은 이 필수 실습에 필요 없다.**

시나리오: 로봇 앞 사람/장애물 거리가 1.20m -> 0.65m -> 0.30m로 바뀐다. 교육용 예시 Stop 0.40m, Slow 0.75m, Ratio 0.30. NULL/STALE/NaN은 UNKNOWN이다. 이는 특정 안전거리의 인증 값이 아니다.

## 수업 시작점 및 Live Demo

- 단계별 3시간 실습은 [D06_STUDENT_3H_CLASSROOM_GUIDE_20261116_KO.md](D06_STUDENT_3H_CLASSROOM_GUIDE_20261116_KO.md)를 따른다.
- 학생 독립 Gazebo + 강사 G07 주행 화면 관찰은 [D06_STUDENT_LIVE_DEMO_GUIDE_20261116_KO.md](D06_STUDENT_LIVE_DEMO_GUIDE_20261116_KO.md)를 따른다.
- **main 병합 전에는** `docs/d06-classroom-materials-20261113` 브랜치에서 새 문서를 사용한다. 학생 Python TODO는 **의도한 RED**, 학생의 별도 Gazebo는 **NO_GOAL/NO_CMD_VEL**이다.

## RED 실습
기존 공개 저장소의 루트에서:

    python3 -m pytest -q block_B/day06/tests/test_d06_public.py

처음에는 TODO_D06_... NotImplementedError로 일부 RED가 예상되며 정상이다. 실패 내용을 분석하고 코드를 채운다.

## GREEN 구현
- 파일: block_B/day06/safety_bubble_todo.py
- classify_range: valid가 true, 0<=age<=0.5, 유한한 양수 거리인 경우에만 거리 비교. d<=0.40 STOP 우선. 0.40<d<=0.75 SLOWDOWN, d>0.75 CLEAR.
- bubble_policy: status, expected_ratio, safety_certified=False, control_published=False를 담은 교육용 dict만 반환한다. UNKNOWN ratio는 None이며 안전하다는 뜻이 아님.
- 설정 stop>=slow, ratio>=1, 0/음수 radius, NaN 파라미터는 ValueError.
- 위 테스트를 다시 실행해 GREEN 증거를 제출한다.

## 공식 Nav2 비교
Nav2 Collision Monitor의 StopZone과 SlowZone은 거리값 하나를 임의로 받아 로봇 모터를 직접 제어하지 않는다. 실제 LaserScan 포인트를 개별 zone 안에 몇 개 포함하는지 계산하여 인가된 Twist command를 감속 또는 0으로 변환한다. 이 기능은 공식 nav2_collision_monitor가 담당한다. D05 정렬 RGB-D distance는 기록/시각화 정보이며 별도 승인된 scan source를 대체하지 않는다.

강사 시연에서 /axia/d06/test/scan -> official Collision Monitor -> /axia/d06/test/cmd_out으로 **격리한 시험 토픽**만 이용한다. 학생은 /cmd_vel을 publish하지 않는다.

제출: 코드 파일, pytest 출력, 거리별 상태표, UNKNOWN을 CLEAR로 간주하면 위험한 이유 3문장. 테스트가 RED라면 TODO 미완료 상태라고 표시한다.
