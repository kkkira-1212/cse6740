"""Protect the frozen three-seed V3 LoRA protocol."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v3_lora", ROOT / "src/models/run_v3_lora.py")
protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)
MANIFEST = ROOT / "configs/clip_lora_v3_fixed_runs.json"


class ProtocolTests(unittest.TestCase):
    def test_frozen_three_seed_protocol(self):
        manifest = protocol.load_manifest(MANIFEST)
        self.assertEqual(len(manifest["runs"]), 3)
        self.assertFalse(manifest["test_inference"])

    def test_duplicate_seed_is_rejected(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["runs"][1]["config"] = manifest["runs"][0]["config"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "duplicate seed"):
                protocol.load_manifest(path)


if __name__ == "__main__":
    unittest.main()
