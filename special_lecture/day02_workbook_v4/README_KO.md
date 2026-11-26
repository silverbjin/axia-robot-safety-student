# AXIA DAY 02 — Master-first Dual MVP Workbook v4.0 (2026-11-26)

## 목적
본편은 **2026-11-22 실제 인수된 G07 완성 MVP**(U00~U13), 선택 심화는 **2026-11-21 실제 Native Moving 0/2 실패 MVP**(A01~A06)를 학습합니다. 각 Unit은 A면 오답·데이터 파이프라인 분석 → B면 **완성형 복사 프롬프트·작성 이유·명령·예상 출력·AI 응답 점검**으로 구성됩니다. 총 **40장** (14×2 + 6×2)입니다.

## 정확한 소스·인수
| | 성공본 | 실패본 |
|---|---|---|
| Student 런타임 | `f7edb2d126502eeeed58ae014adadc7a2096d41b` | `a04f9a7da8d54bbd9f944d05388792cb706adf28` |
| Public CI SHA | `64ba0161e66126b4743b4b12a859f4a5349ae58a` | `8e03ac0a912ca9b81bdddda70212e52e6d804389` |
| 과거 Native L2 | [#44965035965](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44965035965) **2/2 PASS** | [#44914827138](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44914827138) **0/2 FAIL** |
| Owner WSL2 L3 | [11/22 원본 사후 RAW](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/c2c4f66c532be2a41855239860b9a9f5d60c4586/docs/operations/AXIA_G07_OWNER_WSL2_L3_POSTRUN_RAW_EVIDENCE_REVIEW_20261122_KO.md): 수치·Lifecycle PASS_SCOPED | NOT_RUN |

11/22 자동 `HOLD_RAW_REVIEW_AND_VISUAL_PENDING` 원본은 유지합니다. 코드와 CI 환경이 다른 두 버전의 단순 diff는 FastDDS 근본원인 입증이 아닙니다. 소프트웨어 STOP을 인증된 E-Stop이라 소개하지 않습니다.

## 실제 수업 명령 (성공 / 실패 두 런타임 별도 준비)
```bash
cd ~
git clone --single-branch --branch release/day02-g07-accepted-20261126 \
  https://github.com/silverbjin/axia-robot-safety-student.git axia-day02-success
cd ~/axia-day02-success
git checkout --detach 045afa5658045ce150effc242443f6fb8fa5c53f
python3 special_lecture/day02/scripts/verify_release.py
bash special_lecture/day02/scripts/prepare_dual_mvp.sh "$HOME/axia-day02-failed"
python3 "$HOME/axia-day02-failed/special_lecture/day02/scripts/verify_failed_case.py"
```
위 명령은 **원본 소스 SHA와 배포 파일의 무결성 L0 확인**이며 자동 Moving Goal·Gazebo를 수행하지 않습니다. 성공본 주행·안전 시나리오 카드에는 [별도 읽기 전용 시나리오 브랜치](https://github.com/silverbjin/axia-robot-safety-student/tree/feat/day02-g07-scenario-demo-20261126)를 사용합니다.

## 교육 자료와 QA
- [워크북 v4 원본 기획](https://github.com/silverbjin/axia-robot-safety-student/blob/045afa5658045ce150effc242443f6fb8fa5c53f/special_lecture/day02/workbook/DUAL_MVP_WORKBOOK_PLAN_v4_KO.md)
- [듀얼 MVP 완성 Master Prompt](https://github.com/silverbjin/axia-robot-safety-student/blob/045afa5658045ce150effc242443f6fb8fa5c53f/special_lecture/day02/workbook/MASTER_PROMPT_DAY02_DUAL_MVP_KO.txt)
- [심화 실패 분석 가이드](https://github.com/silverbjin/axia-robot-safety-student/blob/d9ba3f78ae701697a5986a2bc856e4d856a73dd9/special_lecture/day02/workbook/ADVANCED_FAILURE_ANALYSIS_KO.md)
- [시나리오 S01~S06 강사용 운영 가이드](https://github.com/silverbjin/axia-robot-safety-student/blob/f43df3132c8c1dac29f7c980274cd85bcdda02fc/special_lecture/day02/scenarios/SCENARIO_OPERATION_GUIDE_KO.md)
- 이 디렉터리의 `WORKBOOK_SLIDE_INDEX_KO.md`와 `WORKBOOK_RELEASE_MANIFEST.json`, `verify_workbook_manifest.py`로 40면 구성·릴리스 경계를 검수합니다.

**PPTX/PDF 실제 파일**은 제작 대화에서 전달한 정확한 SHA256(Manifest 참조)의 첨부 아티팩트입니다. **이 Git 커밋에는 PPTX 바이너리가 포함되지 않았으므로 GitHub에서 이를 다운로드할 수 있다고 표시하지 않습니다.** 다운로드한 파일은 `sha256sum <file>`로 대조하십시오. 본 GitHub main에는 교육 통합 문서와 SHA 검증 계약을 게시합니다.

## 검증 상태
- 실제 제작 PPTX 40/40, PDF 40/40, 발표자 노트 40/40, 전체 슬라이드 렌더 QA 경계 초과 0 — **로컬 파일 검수**.
- 학생 메인 브랜치에서 신규 Moving Gazebo L2 또는 WSL2 L3를 수행한 것은 **NOT_RUN**. 이전 성공·실패 SHA 원본을 인용합니다.
- `main` 반영은 **기존 G07 운영 런타임을 수정하지 않는 교재 문서만** 대상으로 합니다. 강사 정답·raw rosbag·Owner 개인 로그는 포함하지 않습니다.
