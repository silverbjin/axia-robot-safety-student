#!/usr/bin/env python3
"""DAY3 workbook plan L0 contract. No ROS, Gazebo, Nav2 or Goal execution."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
LESSON=ROOT/"special_lecture/day03_mvp_workbook"
SRC=ROOT/"special_lecture/day02_mvp_sources"
PACKAGES=("axia_fault_injector","axia_safety_bringup","axia_safety_supervisor","axia_scenario_verifier")

class Day03WorkbookContract(unittest.TestCase):
    def test_existing_public_dual_mvp_is_reused_exactly(self):
        data=json.loads((SRC/"DUAL_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(data["accepted"]["runtime_source_sha"],"f7edb2d126502eeeed58ae014adadc7a2096d41b")
        self.assertEqual(data["failed"]["runtime_source_sha"],"a04f9a7da8d54bbd9f944d05388792cb706adf28")
        self.assertEqual(data["packages"],list(PACKAGES))
        self.assertEqual(data["accepted"]["native_moving_l2"],"2_OF_2_PASS")
        self.assertEqual(data["failed"]["native_moving_l2"],"0_OF_2_FAIL")
        for label in ("accepted","failed"):
            for p in PACKAGES:
                self.assertTrue((SRC/label/"runtime/ros2_ws/src"/p/"package.xml").is_file())

    def test_actual_mvp_components_exist(self):
        base=SRC/"accepted/runtime/tools"
        for filename in ("p2_g07_health_first_boundary.py",
                         "test_g07_health_first_boundary.py",
                         "p2_g07_scan_rmw_first_pair.py",
                         "test_g07_scan_rmw_first_pair.py",
                         "p2_g07_ordered_shutdown.py",
                         "test_g07_context_graph_shutdown.py",
                         "p2_g07_ci_moving_goal_oracle.py"):
            self.assertTrue((base/filename).is_file(),filename)

    def test_workbook_plan_is_actionable_and_scope_locked(self):
        text=(LESSON/"DAY3_MVP_WORKBOOK_PLAN_KO.md").read_text(encoding="utf-8")
        for marker in ("180분","U00","U13","개발","통합","인수",
                       "RED","GREEN","REFACTOR","REVIEW","COMMIT",
                       "first_timing_violation","first_safety_transition",
                       "NOT_RUN","HOLD","/scan","/safety/scan"):
            self.assertIn(marker,text,marker)
        self.assertIn("release/day02-dual-mvp-full-source-build-20261126",text)
        self.assertIn("96be43164fab3f15025edd59279bcfd50b6232cd",text)

    def test_master_prompt_keeps_evidence_boundaries(self):
        text=(LESSON/"MASTER_PROMPT_DAY3_MVP_KO.txt").read_text(encoding="utf-8")
        for marker in ("Run ID","SHA","first_timing_violation",
                       "first_safety_transition","RMW","Callback",
                       "RED","GREEN","REFACTOR","REVIEW","COMMIT",
                       "L0","L1","L2","L3","NOT_RUN","HOLD"):
            self.assertIn(marker,text,marker)
        self.assertIn("300ms",text)
        self.assertIn("150ms",text)
        self.assertIn("120ms",text)

    def test_rendered_release_matches_manifest_and_52_slides(self):
        import hashlib, zipfile, re
        pptx=LESSON/"AXIA_DAY3_MVP_MASTER_FIRST_WORKBOOK_52_KO.pptx"
        pdf=LESSON/"AXIA_DAY3_MVP_MASTER_FIRST_WORKBOOK_52_KO.pdf"
        sheet=LESSON/"AXIA_DAY3_MVP_52_ContactSheet.png"
        manifest=json.loads((LESSON/"WORKBOOK_RENDER_MANIFEST.json").read_text())
        self.assertEqual(manifest["pptx_slides"],52)
        self.assertEqual(manifest["pdf_pages"],52)
        self.assertEqual(manifest["notes"],52)
        self.assertEqual(manifest["unit_faces"],28)
        self.assertEqual(manifest["units"],14)
        self.assertEqual(manifest["pdf_text_boundary_errors"],0)
        for f,key in ((pptx,"pptx_sha256"),(pdf,"pdf_sha256"),(sheet,"contact_sheet_sha256")):
            self.assertTrue(f.is_file(),str(f))
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),manifest[key])
        with zipfile.ZipFile(pptx) as z:
            slide_count=sum(bool(re.fullmatch(r"ppt/slides/slide\d+\.xml",p)) for p in z.namelist())
            notes_count=sum(bool(re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml",p)) for p in z.namelist())
            self.assertEqual(slide_count,52)
            self.assertEqual(notes_count,52)
        self.assertFalse((LESSON/"INSTRUCTOR_GUIDE_KO.md").exists())

    def test_slide_index_has_all_52_rows(self):
        text=(LESSON/"WORKBOOK_SLIDE_INDEX_KO.md").read_text()
        rows=[line for line in text.splitlines() if line.startswith("| ") and line[2:4].isdigit()]
        self.assertEqual(len(rows),52)
        for i in range(14):
            self.assertIn("U"+str(i).zfill(2),text)

    def test_readme_contains_one_shot_verifier_and_private_boundary(self):
        text=(LESSON/"README_KO.md").read_text(encoding="utf-8")
        self.assertIn("verify_dual_source.py",text)
        self.assertIn("강사 정답",text)
        self.assertIn("main",text)

if __name__=="__main__":
    unittest.main()
