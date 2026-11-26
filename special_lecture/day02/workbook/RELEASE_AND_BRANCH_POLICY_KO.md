# DAY 02 — 성공 SHA 릴리스·브랜치·학생 배포 운영 계약

1. **실제 성공의 단일 기준:** Student runtime `f7edb2d126502eeeed58ae014adadc7a2096d41b`; Public strict L2 2/2 `64ba0161e66126b4743b4b12a859f4a5349ae58a` Run #44965035965; Owner WSL2 L3 RAW 보고서 `c2c4f66c532be2a41855239860b9a9f5d60c4586` PASS_SCOPED.
2. **실행 소스 보존:** 릴리스 브랜치는 성공 Student SHA에서 새로 생성. 문서와 검증기 추가 후에는 HEAD가 달라집니다. 운영 파일 8개의 git blob SHA는 `COURSE_RELEASE_MANIFEST.json`과 `verify_release.py`에서 불변 검사합니다. 신규 L2/L3 실행은 하지 않으며 기존 증거를 정확히 명시하여 인용합니다.
3. **불필요한 브랜치 병합 금지:** 과거 0/2 HOLD #105(Student), #229(Public)와 다른 실험 후보는 SUPERSEDED 이력으로 보존하고 후속 #108(Student), #231(Public)을 명시합니다. 이력을 재작성/삭제하지 않습니다.
4. **안전 정책 보존:** Goal 자동 발행·TTY 승인 우회·Nav2/Collision Monitor/Guard/안전 TTL 변경 금지. 운영 런타임 변경 시 이전 성공을 새 SHA에 소급 적용하지 않습니다.
5. **학생 자료의 공개 범위:** 공개된 기존 G07 런타임과 읽기 전용 검사·교육 프롬프트·검토용 문서만 허용. 비공개 Instructor 정답, hidden test, 개인 원본 로컬 로그, rosbag, raw TAR/ZIP, 개인 경로, 토큰·기밀자료 업로드 금지.
6. **배포 게이트:** Git blob 8/8, 정책·출처 Manifest, 미변조 반례, 학생 공개 L0, 공개 CI PASS를 확인한 후 수업 배포. CI L0 PASS≠새 Gazebo L2 또는 새 WSL2 L3 인수입니다.
7. **main 통합:** 현재 Student/Public main과 성공 소스가 분기되어 있으므로 단순 전체 PR 병합 금지. 선택적 통합 PR + 런타임 영향 검토 + 공개 회귀 + **사용자 별도 명시 승인** 필요.
8. **남은 검증 한계:** 원본 자동 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING` 보존, 외부 GUI 영상 독립 검수 없음, DDS 최초 지연 근본원인 미입증, `CERTIFIED_ESTOP=false`.
