# DAY 3 — 실제 G07 완성 MVP 기반 AI Native 디버깅 워크북 (기획 후보)

본 디렉터리는 **완성 워크북이 아니라 제작 기획·프롬프트 초안**입니다.
DAY 2에서 이미 공개된 완성 MVP 코드 전체를 그대로 활용하고, 개발 → 통합 → 인수 오류를 해결하는 프롬프트 방법을 학습합니다.

- [실제 공개 MVP 소스 및 빌드](../day02_mvp_sources/README_KO.md)
- [DAY 3 상세 제작 계획](DAY3_MVP_WORKBOOK_PLAN_KO.md)
- [DAY 3 완성형 마스터 프롬프트 초안](MASTER_PROMPT_DAY3_MVP_KO.txt)
- [공개 원본 출처 검증기](../day02_mvp_sources/scripts/verify_dual_source.py)
- [DAY 3 L0 계획/원본 검증](test_workbook_contract.py)

```bash
# 공개 소스 release에서 원본 서명 확인 (새 Goal/Gazebo 없음)
python3 special_lecture/day02_mvp_sources/scripts/verify_dual_source.py
# 교재 기획 구성 L0 테스트
python3 -m unittest discover -s special_lecture/day03_mvp_workbook -p 'test_*.py' -v
```

**원본 기준 고정**: `release/day02-dual-mvp-full-source-build-20261126` @ `96be43164fab3f15025edd59279bcfd50b6232cd`.

**공개 범위**: 기존 공개된 실제 MVP 소스, 학습 계획, 공개 진단 테스트만. 강사 정답 및 hidden tests는 비공개. `main` 병합에는 사용자 별도 승인이 필요합니다.
**검증 경계**: 문서·소스 SHA L0 PASS는 실제 Gazebo L2/Owner WSL2 L3의 신규 PASS가 아닙니다. 현재 신규 L2/L3는 `NOT_RUN`입니다.


## 52장 실물 워크북 — GitHub 공개 렌더 QA 출고

**생성 완료:** `build_workbook.js` (PptxGenJS v4.0.0)로 52장 전량을 생성했고, 동일 소스의 GitHub Actions Run [#45837564279](https://github.com/silverbjin/axia-robot-safety-student/actions/runs/45837564279)에서 PPTX/PDF/PNG 렌더 QA 52/52 PASS 후 바이너리를 브랜치에 커밋했습니다.

- [전체 52장 편집용 PPTX](AXIA_DAY3_MVP_MASTER_FIRST_WORKBOOK_52_KO.pptx)
- [전체 52페이지 PDF](AXIA_DAY3_MVP_MASTER_FIRST_WORKBOOK_52_KO.pdf)
- [52장 Contact Sheet](AXIA_DAY3_MVP_52_ContactSheet.png)
- [렌더링 QA 보고서](PPTX_RENDER_QA_KO.md)
- [실제 GitHub CI 산출물 SHA·검증 범위](WORKBOOK_RENDER_MANIFEST.json)
- [52장 목차 및 학습 활동](WORKBOOK_SLIDE_INDEX_KO.md)

**교재 콘텐츠:** Master-first → G07 실제 입력/출력 데이터 구조 → U00~U13 각 A면(Result First)/B면(Complete Unit Prompt·Why·Expected·Review) → 개발·통합·인수 종합 → Incident Card.

**주의:** CI의 52장 PDF 렌더 PASS는 디자인·편집 구조 검증이지 새로운 Gazebo L2/Owner WSL2 L3 인수가 아닙니다. 과거 공개 Native L2 성공 Run 44965035965, 실패 Run 44914827138은 서로 다른 실행입니다. 원본 안전 TTL(Scan300/CM120/Guard150)은 변경하지 않았고 인증 E-Stop을 주장하지 않습니다. 학생용 저장소에 강사용 정답·비공개 증거는 포함하지 않습니다.

교육용 전체 소스는 같은 저장소 `special_lecture/day02_mvp_sources/accepted/runtime` 및 `failed/runtime` 경로로 재사용하며 중복 복사하지 않습니다.

## DAY 3 실제 G07 시나리오 활용 가이드 (S01~S06 / F01~F04)

- [완성 MVP의 시나리오 운영·학생 관측·강사 시연 상세 가이드](DAY3_G07_MVP_SCENARIO_USE_GUIDE_KO.md)
- [SHA 고정 읽기 전용 시나리오 원샷 스크립트](scripts/day03_g07_scenario_once.sh)
- [시나리오 L0 검증과 원본 실행 범위](DAY3_G07_SCENARIO_QA_KO.md)

```bash
bash special_lecture/day03_mvp_workbook/scripts/day03_g07_scenario_once.sh --doctor
bash special_lecture/day03_mvp_workbook/scripts/day03_g07_scenario_once.sh --compare
```

본 데모는 이미 공개된 DAY 2 **과거 실측 보고서의 정적 증거 리플레이**만 수행합니다. 새 ROS/Gazebo/Goal 실행은 없으며 신규 L2/L3 인수도 하지 않습니다. `main` 병합은 별도 승인 전 보류합니다.
