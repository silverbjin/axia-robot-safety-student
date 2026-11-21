"""D12 offline incident command center: contract & privacy (no ROS/Gazebo)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "day12" / "incident_command_center" / "AXIA_D12_INCIDENT_COMMAND_CENTER.html"
GUIDE = ROOT / "day12" / "INCIDENT_COMMAND_CENTER_STUDENT_GUIDE_KO.md"


def test_single_file_offline_app_has_safety_and_controls():
    src = PAGE.read_text(encoding="utf-8")
    assert "<!doctype html>" in src.lower()
    for key in (
        "AXIA INCIDENT COMMAND CENTER", "SYNTHETIC REPLAY",
        "EDUCATION ONLY", "NO CONTROL AUTHORITY", "NOT LIVE ROS DDS",
        "NORMAL", "CAUTION", "WARNING", "INSUFFICIENT_DATA",
        "source_timestamp_ns", "event_id", "quality_reason",
        "EDUCATION_TRANSPORT_DEMO", "DEMO:TST_N_00:002",
        "operator_feedback.jsonl", "INVESTIGATE", "CHECK_QUALITY",
        "Replay", "일시정지", "다시 시작", "1건 진행", "정답 공개",
        "상태 필터", "피드백 기록", "JSONL 내보내기", "JSONL 불러오기",
    ):
        assert key in src, key
    for id_ in (
        "playBtn", "pauseBtn", "resetBtn", "stepBtn", "speedSelect",
        "timeline", "detail", "guessSelect", "revealBtn", "filterSelect",
        "feedbackAction", "feedbackReason", "saveFeedbackBtn",
        "exportFeedbackBtn", "importEvents", "importFeedback",
        "feedbackList", "modeBadge", "sourceNotice", "caseCounter",
    ):
        assert f'id="{id_}"' in src, id_
    assert not re.search(r'<script[^>]+src=', src, re.I)
    assert not re.search(r'<link[^>]+(?:https?:)?//', src, re.I)
    for forbidden in (
        "fetch(", "XMLHttpRequest(", "WebSocket(", "EventSource(",
        "create_publisher(", "send_goal_async(", "/cmd_vel",
        "certified_estop: true", "control_authority: true",
    ):
        assert forbidden not in src, forbidden
    assert "textContent" in src and "Blob(" in src
    assert src.count("<script>") == 1 and src.count("</script>") == 1


def test_beginner_and_instructor_separation():
    s = GUIDE.read_text(encoding="utf-8")
    for phrase in (
        "git clone https://github.com/silverbjin/axia-robot-safety-student.git",
        "AXIA_D12_INCIDENT_COMMAND_CENTER.html", "file://",
        "12건", "8건", "operator_feedback.jsonl", "미구현",
        "SYNTHETIC_COURSE_FIXTURE", "인증된 E-Stop",
        "예상 결과", "오류", "제출", "시연", "정답 공개",
    ):
        assert phrase in s, phrase
    assert not (ROOT / "day12" / "D12_SOLUTION_GUIDE_KO.md").exists()
