#!/usr/bin/env python3
"""Offline L0 validation of DAY02 v4 main documentation and published artifact hashes."""
import json,sys,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
def validate():
    m=json.loads((HERE/"WORKBOOK_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    index=(HERE/"WORKBOOK_SLIDE_INDEX_KO.md").read_text(encoding="utf-8")
    readme=(HERE/"README_KO.md").read_text(encoding="utf-8")
    errors=[]
    if m.get("slides")!=40 or m.get("units")!=20 or m.get("pages_per_unit")!=2:errors.append("BAD_PAGE_COUNT")
    ids=[*("U%02d"%i for i in range(14)),*("A%02d"%i for i in range(1,7))]
    if any(re.search(r"\|\s*"+x+r"\s*\|",index) is None for x in ids):errors.append("MISSING_UNIT")
    if sum(1 for row in index.splitlines() if row.startswith("| ") and " | U" in row)!=14 or sum(1 for row in index.splitlines() if row.startswith("| ") and " | A" in row)!=6:errors.append("BAD_UNIT_DISTRIBUTION")
    if m["successful_mvp"]["runtime_source_sha"]!="f7edb2d126502eeeed58ae014adadc7a2096d41b":errors.append("GOOD_SHA_DRIFT")
    if m["failed_mvp"]["runtime_source_sha"]!="a04f9a7da8d54bbd9f944d05388792cb706adf28":errors.append("FAILED_SHA_DRIFT")
    if m["successful_mvp"]["native_run_id"]!=44965035965 or m["failed_mvp"]["native_run_id"]!=44914827138:errors.append("WRONG_L2_RUN")
    if m["failed_mvp"]["native_l2"]!="0_OF_2_FAIL" or m["failed_mvp"]["root_cause"]!="UNDETERMINED":errors.append("OVERCLAIM_FAILURE")
    if m["verification_scope"]["new_ros_gazebo_l2"]!="NOT_RUN" or m["verification_scope"]["certified_estop"] is not False:errors.append("UNSAFE_CERTIFICATION")
    if m["verified_pptx"]["availability"]!="DELIVERED_AS_CONVERSATION_ARTIFACT_NOT_YET_IN_GITHUB_BINARY":errors.append("FALSE_BINARY_PUBLICATION")
    if "PPTX 바이너리가 포함되지" not in readme:errors.append("FALSE_GITHUB_DOWNLOAD_CLAIM")
    return errors
if __name__=="__main__":
    e=validate()
    print("AXIA_DAY02_WORKBOOK_MAIN_DOCS_L0_PASS 20_UNITS 40_PAGES PROVENANCE_SCOPED" if not e else "AXIA_DAY02_WORKBOOK_MAIN_DOCS_L0_FAIL "+" ".join(e))
    sys.exit(bool(e))
