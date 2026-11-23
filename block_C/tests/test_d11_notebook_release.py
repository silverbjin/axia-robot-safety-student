"""AXIA D11: public STUDENT TODO notebook integrity. No PyTorch download or private AI execution."""
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DAY=ROOT/"day11"
NOTE=DAY/"notebooks"
FILES={
 "wsl2":NOTE/"lesson11-autoencoder-student-wsl2-todo.ipynb",
 "colab":NOTE/"lesson11-autoencoder-student-colab-todo.ipynb"
}

class D11NotebookDistribution(unittest.TestCase):
    def load(self,variant):
        p=FILES[variant]
        self.assertTrue(p.is_file(),f"notebook missing: {p}")
        with p.open(encoding="utf-8") as f:doc=json.load(f)
        self.assertEqual(doc.get("nbformat"),4)
        self.assertEqual(len(doc["cells"]),37)
        code=[c for c in doc["cells"] if c["cell_type"]=="code"]
        self.assertEqual(len(code),7)
        self.assertEqual(sum(bool(c.get("attachments")) for c in doc["cells"]),7)
        self.assertEqual(sum(len(c.get("outputs",[])) for c in code),0)
        self.assertTrue(all(c.get("execution_count") is None for c in code))
        self.assertEqual(doc["metadata"]["course_info"]["distribution"],"PUBLIC_STUDENT_TODO")
        for cell in code:compile("".join(cell["source"]),str(p),"exec")
        return doc,code

    def test_notebooks_are_present_and_compilable(self):
        for v in FILES:self.load(v)

    def test_todo_cells_are_not_falsely_reported_as_green(self):
        for v in FILES:
            doc,code=self.load(v)
            for i in (23,28,33):
                s="".join(doc["cells"][i]["source"])
                self.assertIn("raise NotImplementedError",s)
                self.assertIn("[EXPECTED_RED S",s)
            for i in (0,7,13,18):
                self.assertTrue(doc["cells"][i]["source"])
            all_code="\n".join("".join(c["source"]) for c in code)
            for leaked in ("nn.Sequential(","optimizer.step(","torch.save(","ae_checkpoint.pt",
                           "from autoencoder_pipeline import"):
                self.assertNotIn(leaked,all_code,leaked)
            self.assertIn("train_autoencoder_todo",all_code)

    def test_colab_and_wsl2_device_setup_are_separate(self):
        w,_=self.load("wsl2");c,_=self.load("colab")
        wsource="".join(w["cells"][0]["source"])
        csource="".join(c["cells"][0]["source"])
        self.assertIn("venv",wsource)
        self.assertIn("DEVICE_MODE",wsource)
        self.assertIn("Colab",csource)
        self.assertIn("DEVICE_MODE",csource)
        self.assertIn("cuda",csource)
        self.assertIn("cpu",csource)
        self.assertNotIn("venv.create",csource)

    def test_public_student_contract_and_guide(self):
        t=(NOTE/"STUDENT_NOTEBOOK_GUIDE_KO.md").read_text(encoding="utf-8")
        for word in ("Google Colab","WSL2","EXPECTED_RED","S1","S2","S3","S4","S5","S6",
                     "CUDA","INSUFFICIENT_DATA","데이터 누수","안전","강사 정답 비공개"):
            self.assertIn(word,t,word)
        self.assertTrue((NOTE/"requirements.txt").is_file())
        self.assertTrue((NOTE/"requirements-colab.txt").is_file())
        src=(DAY/"student_ae_todo.py").read_text(encoding="utf-8")
        self.assertIn("NotImplementedError",src)
        self.assertFalse((NOTE/"ae_checkpoint.pt").exists())
        self.assertFalse((NOTE/"autoencoder_pipeline.py").exists())

    def test_existing_toy_is_unchanged(self):
        p=DAY/"mse_toy_practice.py"
        self.assertTrue(p.is_file())
        s=p.read_text(encoding="utf-8")
        self.assertIn("D11_TOY_DEMO_PASS",s)
        self.assertIn("INSUFFICIENT_DATA",s)
if __name__=="__main__":
    unittest.main()
