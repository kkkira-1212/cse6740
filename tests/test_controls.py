"""Unit checks for the v2 shortcut controls."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "controls", Path(__file__).resolve().parents[1] / "src/eval/controls.py"
)
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


def row(anchor, kind, label, text, image):
    return {
        "pair_id": f"{anchor}_{kind}",
        "anchor_item_id": anchor,
        "anchor_group_id": "group_" + anchor,
        "text_item_id": anchor if label else "donor_" + anchor,
        "label": label,
        "neg_type": kind,
        "image_path": image,
        "text": text,
        "split": "train",
        "dataset_version": "test",
    }


class FixedImageLayoutTests(unittest.TestCase):
    def test_accepts_same_image_per_anchor(self):
        rows = [
            row("A", "pos", 1, "red chair", "a.jpg"),
            row("A", "N1", 0, "blue sofa", "a.jpg"),
            row("B", "pos", 1, "green table", "b.jpg"),
            row("B", "N2", 0, "white lamp", "b.jpg"),
        ]
        self.assertEqual(controls.check_fixed_image_layout(rows), 2)

    def test_rejects_different_image(self):
        rows = [
            row("A", "pos", 1, "red chair", "a.jpg"),
            row("A", "N1", 0, "blue sofa", "different.jpg"),
        ]
        with self.assertRaises(ValueError):
            controls.check_fixed_image_layout(rows)

    def test_rejects_missing_negative(self):
        rows = [row("A", "pos", 1, "red chair", "a.jpg")]
        with self.assertRaises(ValueError):
            controls.check_fixed_image_layout(rows)


class ValidationTests(unittest.TestCase):
    def test_label_and_negative_type_must_agree(self):
        rows = [
            row("A", "pos", 1, "red chair", "a.jpg"),
            row("A", "N1", 0, "blue sofa", "a.jpg"),
        ]
        controls.validate_rows(rows)
        rows[1]["label"] = 1
        with self.assertRaises(ValueError):
            controls.validate_rows(rows)


class ImageNullTests(unittest.TestCase):
    def test_identity_scores_are_constant_per_anchor(self):
        rows = [
            row("A", "pos", 1, "red chair", "a.jpg"),
            row("A", "N1", 0, "blue sofa", "a.jpg"),
            row("B", "pos", 1, "green table", "b.jpg"),
            row("B", "N2", 0, "white lamp", "b.jpg"),
        ]
        scores = controls.identity_scores(rows)
        self.assertEqual(scores["A_pos"], scores["A_N1"])
        self.assertEqual(scores["B_pos"], scores["B_N2"])
        controls.assert_constant_per_anchor(rows, scores)

    def test_constant_assertion_rejects_leak(self):
        rows = [
            row("A", "pos", 1, "red chair", "a.jpg"),
            row("A", "N1", 0, "blue sofa", "a.jpg"),
        ]
        with self.assertRaises(ValueError):
            controls.assert_constant_per_anchor(rows, {"A_pos": 0.9, "A_N1": 0.1})


class TextOnlyTests(unittest.TestCase):
    def test_text_scores_do_not_depend_on_image_or_pair_id(self):
        rows = [
            row("A", "pos", 1, "red chair", "a.jpg"),
            row("A", "N1", 0, "red chair", "a.jpg"),
            row("B", "pos", 1, "blue sofa", "b.jpg"),
            row("B", "N1", 0, "blue sofa", "b.jpg"),
        ]
        vectorizer, classifier = controls.fit_text(rows, seed=0)
        scores = controls.score_text(rows, vectorizer, classifier)
        self.assertAlmostEqual(scores["A_pos"], scores["A_N1"])
        self.assertAlmostEqual(scores["B_pos"], scores["B_N1"])


if __name__ == "__main__":
    unittest.main()
