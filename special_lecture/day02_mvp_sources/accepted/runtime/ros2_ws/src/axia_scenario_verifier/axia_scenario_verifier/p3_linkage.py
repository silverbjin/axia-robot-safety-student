"""Read-only P3 provenance crosswalk annotation, not a gate/Goal/Fault executor.

Only summarizes separate evidence sources. Earlier S02 offline fixture remains
the historic no-Goal capture, never mutated or substituted with latest G07.
"""
import json
from pathlib import Path

from .runner import sha256

CROSSWALK="docs/reports/p3_integrated_evidence_crosswalk_20261113.json"
EXPECTED=("S01","S02","S03","S04","S05")
FORMAL=("G08","G09","G10","G11")
OWNER_G07_SHA="eb984b73138e592caa67426eed9c60dde2ca2ebd"
OWNER_G07_ARCHIVE_SHA256="fc99c9a26f2832ba4cb8f5b55b922b47f69ca6f2fcc4c1fe07b3eb43ec1b0862"


def read_linkage(root: Path) -> tuple[dict, str]:
    path=root/CROSSWALK
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema")!="axia_p1_p2_p3_evidence_crosswalk_v1":
        raise ValueError("INVALID_P3_LINKAGE_SCHEMA")
    if any(data.get(flag) is not False for flag in
           ("p1_p2_formal_accepted","hardware_estop_certified","student_release_ready")):
        raise ValueError("FORBIDDEN_P3_LINKAGE_ACCEPTANCE_OR_ESTOP")
    if data.get("formal_gates")!={g:"NOT_ACCEPTED" for g in FORMAL}:
        raise ValueError("FORBIDDEN_P3_LINKAGE_G08_G11_GATE_PROMOTION")
    scenarios=data.get("scenarios")
    if not isinstance(scenarios,dict) or tuple(sorted(scenarios))!=EXPECTED:
        raise ValueError("INVALID_P3_LINKAGE_SCENARIOS")
    result={}
    for sid,row in sorted(scenarios.items()):
        if row.get("formal_accepted") is not False or not row.get("source_ref"):
            raise ValueError("FORBIDDEN_P3_LINKAGE_SCENARIO_PROMOTION")
        if row.get("evidence_level") not in (
                "OWNER_REPORT","OWNER_L3_SCOPED_RAW_REVIEW","PUBLIC_L0_SYNTHETIC"):
            raise ValueError("UNKNOWN_P3_LINKAGE_EVIDENCE_LEVEL")
        result[sid]={
            "evidence_level":row["evidence_level"],
            "source_ref":row["source_ref"],
            "capture_source_sha":row["capture_source_sha"],
            "scoped_raw_reviewed":bool(row.get("scoped_raw_reviewed",False)),
            "formal_accepted":False
        }
    g07=scenarios["S02"]
    report=root/g07["source_ref"]
    if (g07.get("evidence_level")!="OWNER_L3_SCOPED_RAW_REVIEW"
        or g07.get("capture_source_sha")!=OWNER_G07_SHA
        or g07.get("archive_sha256")!=OWNER_G07_ARCHIVE_SHA256
        or g07.get("scoped_raw_reviewed") is not True
        or g07.get("contact_ground_truth_verified") is not False
        or g07.get("formal_accepted") is not False
        or not report.is_file()):
        raise ValueError("G07_SCOPED_OWNER_SOURCE_MISMATCH")
    report_text=report.read_text(encoding="utf-8")
    if OWNER_G07_SHA not in report_text or OWNER_G07_ARCHIVE_SHA256 not in report_text:
        raise ValueError("G07_OWNER_RAW_REPORT_NOT_LINKED")
    if scenarios["S04"].get("real_overlap_measured") is not False:
        raise ValueError("SYNTHETIC_PNU_FALSE_L3")
    return result, sha256(path)
