"""Offline checks: regenerated pairs must not reuse stale API judgments."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/baselines"))
import luna_baseline as luna


class ResumeTests(unittest.TestCase):
    def test_key_changes_with_pair_image_prompt_and_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.jpg"
            path.write_bytes(b"first image")
            rows = [dict(pair_id="A_N2", image_path="image.jpg", text="Black chair")]
            args = SimpleNamespace(image_root=directory, model="test-model", prompt="P1",
                                   reasoning_effort="low", detail="auto", base_url="https://example.test/v1")
            original = luna.run_key(rows, args)
            self.assertEqual(original, luna.run_key(rows, args))
            changed = deepcopy(rows)
            changed[0]["text"] = "Blue chair"
            self.assertNotEqual(original, luna.run_key(changed, args))
            path.write_bytes(b"different image, same filename")
            self.assertNotEqual(original, luna.run_key(rows, args))
            path.write_bytes(b"first image")
            with patch.dict(luna.PROMPTS, P1={"instructions": "changed prompt"}):
                self.assertNotEqual(original, luna.run_key(rows, args))
            args.base_url = "https://other.example.test/v1"
            self.assertNotEqual(original, luna.run_key(rows, args))

    def test_legacy_log_key_does_not_load_into_new_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log.jsonl"
            path.write_text('{"key":"old","pair_id":"A_N2","probability":95}\n')
            self.assertEqual(luna.load_log(path, "new", False), ({}, []))


if __name__ == "__main__":
    unittest.main()
