"""Protect the agreed matrix and prevent replacing incomplete runs."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_lora_ablation", ROOT / "src/models/run_lora_ablation.py")
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)
MANIFEST = ROOT / "configs/clip_lora_v2_ablation.json"


class MatrixTests(unittest.TestCase):
    def test_exact_five_configurations_with_three_seeds(self):
        manifest = matrix.load_manifest(MANIFEST)
        self.assertEqual(len(manifest["runs"]), 15)
        self.assertFalse(manifest["test_inference"])
        self.assertEqual(len(manifest["trainer_sha256"]), 64)

    def test_duplicate_run_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["runs"][-1] = manifest["runs"][0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                matrix.load_manifest(path)

    def test_non_ablation_hyperparameter_change_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            config = json.loads((ROOT / manifest["runs"][-1]["config"]).read_text())
            config["learning_rate"] *= 10
            config_path = directory / "changed.json"
            config_path.write_text(json.dumps(config))
            manifest["runs"][-1]["config"] = str(config_path)
            path = directory / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "hyperparameters differ"):
                matrix.load_manifest(path)

    def test_incomplete_run_is_not_overwritten(self):
        entry = json.loads(MANIFEST.read_text())["runs"][0]
        with tempfile.TemporaryDirectory() as directory:
            entry["run_dir"] = directory
            path = Path(directory) / "training.json"
            original = '{"status": "running"}\n'
            path.write_text(original)
            with self.assertRaisesRegex(ValueError, "not a completed"):
                matrix.export_completed(entry)
            self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
