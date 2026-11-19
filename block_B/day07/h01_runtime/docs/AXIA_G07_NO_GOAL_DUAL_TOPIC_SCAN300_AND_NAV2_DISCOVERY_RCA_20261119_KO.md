# AXIA G07 — NO_GOAL Scan 300ms 최초 경계·Nav2 종료 탐색 회귀 보고서

**작성**: 2026-11-19 · **단계**: RED → GREEN → REFACTOR → REVIEW → COMMIT

## 현상과 원본

현장 WSL2 NVIDIA ZOAgryLW는 Raw Scan 최대 452.540ms, Safety Scan 최대 458.803ms, Clock 평균 RTF 0.782939, Gazebo 서버 `exit -11`을 보고했습니다. 서로 다른 원인을 하나의 최종 오류로 취급하지 않습니다. 실제 첫 native Scan 지연과 ROS 콜백 지연을 분리하기 위해 공개 CI에 D08의 기존 native Gazebo/ROS 관측기를 추가했습니다.

**공개 실제 L2 최초 실패**: [#44455727595](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44455727595)와 아티팩트 `axia-d06-g07-nogoal-cm-ordered-l2-44455727595`. 최초 학생용 Raw Scan 증거:
- source stamp `44.400s→44.502s`, 학생용 Raw ROS host `206.976532→207.410886s`: **434.354ms, 안전 TTL300ms FAIL**
- 동일 Gazebo native timestamp pair: **103.745ms**; 독립 ROS raw observer 역시 정상적인 약 103ms
- 학생용 원본 `raw_first_gap_diagnostics.phase=BEFORE_FIRST_SAFETY_SCAN`. 즉 **두 토픽이 모두 활성화되기 전 구독 준비 구간**의 초기 수신 지연. 이것은 진행 중인 안전상태의 안정성을 증명하지 못하고, 원래 프로그램이 수신된 첫 Raw만으로 20초 창을 시작했기 때문에 20초 검증 전체를 실패하게 만든 경계 오류였습니다.
- 별도 Nav2 READY 인접 native Scan 약 301ms, 국소 Clock RTF 약 0.367이 관측되었으나 실제 Student 첫 Raw gap과는 **다른 메시지 쌍**입니다. Gazebo 내부 센서 publisher의 원인은 미측정.
- 같은 실패 세션에서 종료 helper는 `/lifecycle_manager_navigation/get_parameters`를 **3초 안에 발견하지 못해 ACK가 실패**, CM `exit -11`, Gazebo 서버는 `exit 0`. 이것은 앞선 현장 Gazebo 서버 `-11`과 별도 실패입니다.

## 최소 수정 — 안전 기준은 유지

수정 1: `tools/g07_wslg_no_goal_sensor_probe.py`
- 기존 `assess_window()`의 Raw/Safety 각 **300ms 호스트 수신 TTL**, 센서 유효 거리(front >0.75m, side >1.20m), Odom 정지, Clock 단조 검사를 그대로 유지합니다.
- `select_dual_topic_window()`로 Raw와 /safety/scan **모두 수신된 시각 이후부터** 관찰 구간을 정의합니다. 준비 이전에는 절대 Goal 승인하지 않고, Raw만 수신하던 기간의 최초 위반을 `startup_pre_both_scan_diagnostics`로 별도 보존합니다.
- 두 토픽이 모두 활성화된 후 **새로운 20초 실제 wall-time 관찰**을 반드시 완료합니다. 부족하면 `DUAL_TOPIC_FULL_DWELL_NOT_PROVEN`, 한쪽 누락이면 `DUAL_TOPIC_READINESS_MISSING`으로 HOLD합니다. 준비 후 300ms를 한 번이라도 넘으면 기존대로 무조건 HOLD입니다.
- 최초 위반 source stamp/host monotonic 쌍(`scan_receipts_compact`)을 기존대로 유지합니다. 대용량 전체 LaserScan Range 원본은 중복 기록하지 않습니다.

수정 2: `tools/p2_g07_ordered_shutdown.py`
- 기존 종료 helper의 `GetParameters` service 발견 3초 단발 실패를 재현하고 `wait_for_service_bounded`를 추가했습니다.
- **최대 12초, 1초 단위의 서비스 발견 대기**이며 기존 60초 전체 종료 기한 안에서만 동작합니다. 탐색에 실패하면 서비스 없음으로 HOLD, Lifecycle ACK 없는 상황을 절대 정상 종료로 승격하지 않습니다.
- CM120ms/Guard150ms/Scan300ms, 공식 Nav2, Waffle, Gazebo World, Goal, Twist 제어를 변경하지 않았습니다.

## 검증 결과

- 원본 L2 #44455727595: Raw 434.354ms / native 103.745ms / Nav2 서비스 탐색 실패 / CM -11, Gazebo 0.
- 공개 TDD RED [#44458939278](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44458939278): 서비스 발견 helper 부재를 회귀로 재현. 새로운 Raw/Safety 창 테스트에서는 기존 소스 문자열 계약을 실제 의미에 맞게 정정했습니다.
- 공개 L0 GREEN [#44459147066](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44459147066): 두 토픽 시작·준비 후 위반·준비 누락·12초 한도 테스트 PASS.
- **실제 Gazebo+RViz L2** [#44459151881](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44459151881): NO_GOAL rc=0, 신규 두 토픽 관찰 20.002s, Raw 196개 최대 124.332ms, Safety 196개 최대 122.827ms, CLEAR196/196, Navigation/Localization ACK=true, Collision Monitor child exit 0, Gazebo server child exit 0, 강제 종료 없음. 실제 종료 증거와 원본 JSON/launch.log는 CI 아티팩트로 보존합니다.
- 해당 L2는 소프트웨어 렌더링 CI 단일 세션입니다. **WSL2 NVIDIA/D3D12 최종 인수(L3)는 별도 현장 검증이 필요**하며, 실제 주행·CM120/Guard150의 이동 중 경계까지 포함하는 통합 시연 인수와 혼동하면 안 됩니다.
- Public CI 엄격 인수 게이트(센서 TTL PASS+20초+CM0+gz0) 보강 실행은 별도 결과로 추적합니다.

**검증 소스 기준**: 학생용 런타임 소스 `f1f5d932de831d3dabedf9a44a5fa27cf5705f42`. 학생 브랜치 `fix/g07-nogoal-ordered-cm-shutdown-20261119`, 공개 CI 브랜치 `fix/d06-wslg-lidar-vs-rtf-ci-20261118`. 두 저장소 모두 main 미병합. SW STOP은 인증된 E-Stop이 아닙니다.


---

## 5. 추가 실제 오류 — 계측 프로세스와 Nav2 종료 요청의 경합

[엄격 실제 CI #44459901466](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44459901466)은 Raw/Safety 본시험에 문제가 없는데도 `Navigation ManageLifecycleNodes SHUTDOWN SERVICE_TIMEOUT`, Collision Monitor `exit -11`으로 FAIL하였다. 최초 오류를 먼저 보면 **두 개의 독립 read-only Scan 진단 노드가 Nav2 종료 서비스와 동시에 계속 실행되는 경계**가 확인된다. 이것이 SIGSEGV의 직접 원인임을 stack trace로 입증하지는 못했으며, 우선 **프로세스 수명 경합 가설**로 한정한다.

승인된 MVP 원칙에 따라 공식 Nav2/CM/Waffle/Gazebo source는 수정하지 않는다. `scripts/p2_no_goal_smoke_ci.sh`에 NO_GOAL + 공식 Nav2 ordered-shutdown 전용 **`AXIA_G07_NO_GOAL_WITNESS_HANDOFF=1`** 조건부 증거 핸드오프를 추가했다. 학생 probe가 양쪽 토픽 20초 Scan300 검사를 완료하면 `g07_witness_probe_complete.signal`을 기록하고, CI 또는 Owner wrapper가 소유한 두 별도 구독 프로세스에 종료 요청을 전달해 실제 exit0를 기다린다. 두 PID가 모두 정상 종료된 사실을 확인한 후 `g07_witness_stopped.ack`에 `G07_READONLY_WITNESSES_STOPPED`를 기록한다. 그 ACK가 없으면 fail-closed, Goal 없음. 이후 기존 공식 navigation→localization shutdown 및 Gazebo WorldControl pause, launch SIGINT 경로를 재사용한다.

### 실제 GREEN 증거

- [#44461092763](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44461092763): Raw 최대142.175ms/192개, Safety 최대141.016ms/191개·CLEAR191/191, 이중 토픽 20.005초, Navigation+Localization ACK, CM exit0, Gazebo server exit0, RViz/Gazebo GUI 창 모두 확인.
- [#44461627846](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44461627846): 독립 cold-run Raw 최대127.526ms/196개, Safety 최대125.545ms/196개·CLEAR196/196, 이중 토픽 20.003초, 두 observer stop 증거, Nav2 ACK, CM exit0, Gazebo server exit0. 두 실행 모두 Goal/Twist 신규 발행 없음.
- 공개 CI L0 [#44462067138](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44462067138): 71개 모의/순수 파이썬 계약 PASS. GitHub 원본 아티팩트 2개에서 JSON 및 실제 child exit log 검증.

**기준 소스 커밋:** `8e19742fd7bd80db73a37dc7b1d798768dc33e2a`, 학생 smoke blob `9cb5baf6c766a79cf6fd5134707981e32bb23e85`. Classroom 기본 실행에는 opt-in 조건이 없으므로 종료 핸드오프 기능이 개입하지 않는다. 학생 정답으로 인증된 EStop을 주장하지 않는다.

**인수 미완료:** 강사 Windows11/WSL2/WSLg NVIDIA 실제 `--nvidia-causal` 실행은 아직 안 했으므로 이 공개 L2를 L3라고 보고하지 않는다. Moving Goal/CM120/Guard150과 전체 데모 데이터 전달 안전 TTL은 별도, CI+현장 검증 범위 명시 전까지 `AXIA_MVP_DEMO_ACCEPTED=HOLD`. main 미병합.
