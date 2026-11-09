from pathlib import Path
import shutil

import pytest

from block_B.fixture_io import load_fixtures

ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_original_fixture_manifest():
    rows, depth = load_fixtures(ROOT)
    assert len(rows) == 4
    assert len(depth["samples"]) == 3


def test_tampered_fixture_rejected(tmp_path):
    dest = tmp_path / "fixtures"
    shutil.copytree(ROOT, dest)
    (dest / "detections.csv").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_fixtures(dest)


def test_wrong_checksum_inventory_rejected(tmp_path):
    dest = tmp_path / "fixtures"
    shutil.copytree(ROOT, dest)
    with (dest / "SHA256SUMS").open("a", encoding="ascii") as fp:
        fp.write("0" * 64 + "  unexpected.json\n")
    with pytest.raises(ValueError, match="inventory"):
        load_fixtures(dest)


def test_symlink_rejected(tmp_path):
    link = tmp_path / "linked"
    link.symlink_to(ROOT, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked"):
        load_fixtures(link)
