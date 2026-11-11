"""Protect the validation-frozen held-out checkpoint selection."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("selected", ROOT / "src/models/score_selected_checkpoints.py")
selected = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selected)
MANIFEST = ROOT / "configs/clip_v2_selected_test.json"


class SelectionTests(unittest.TestCase):
    def test_exact_selected_matrix(self):
        manifest = selected.load_manifest(MANIFEST)
        self.assertEqual(len(manifest["models"]), 6)

    def test_duplicate_seed_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["models"][1] = manifest["models"][0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                selected.load_manifest(path)

    def test_nonselected_lora_rank_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["models"][0]["config"] = "configs/clip_lora_v2_r8_both_seed0.json"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "rank-16"):
                selected.load_manifest(path)


if __name__ == "__main__":
    unittest.main()
