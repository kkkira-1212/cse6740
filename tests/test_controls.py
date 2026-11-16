"""Unit checks for the fixed-image shortcut controls."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

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


class MatchedAnchorTests(unittest.TestCase):
    def test_uses_own_anchor_positive_not_all_positives(self):
        rows = [
            row("A", "pos", 1, "A pos", "a.jpg"),
            row("A", "N3", 0, "A neg", "a.jpg"),
            row("B", "pos", 1, "B pos", "b.jpg"),
            row("B", "N1", 0, "B neg", "b.jpg"),
        ]
        scores = {"A_pos": 0.9, "A_N3": 0.2, "B_pos": 0.1, "B_N1": 0.8}

        n3 = controls.matched_auc(rows, scores, "N3", {}, 0, 0)
        self.assertEqual(n3["auc"], 1.0)
        self.assertEqual(n3["n_pos"], 1)
        self.assertEqual(n3["n_neg"], 1)

        n1 = controls.matched_auc(rows, scores, "N1", {}, 0, 0)
        self.assertEqual(n1["auc"], 0.0)
        self.assertEqual(n1["n_pos"], 1)

    def test_n3_uses_exchange_clusters(self):
        rows = [
            row("A", "pos", 1, "A pos", "a.jpg"),
            row("A", "N3", 0, "A neg", "a.jpg"),
            row("B", "pos", 1, "B pos", "b.jpg"),
            row("B", "N3", 0, "B neg", "b.jpg"),
        ]
        scores = {"A_pos": 0.9, "A_N3": 0.2, "B_pos": 0.8, "B_N3": 0.1}
        exchange_map = {"A_N3": "exchange-1", "B_N3": "exchange-1"}
        result = controls.matched_auc(rows, scores, "N3", exchange_map, 0, 0)
        self.assertEqual(result["auc"], 1.0)
        self.assertEqual(result["cluster"], "reciprocal_exchange")
        self.assertEqual(result["n_clusters"], 1)
        self.assertEqual(result["n_pos"], 2)


class CacheBindingTests(unittest.TestCase):
    def test_cache_must_match_dataset_and_pairs_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache.npz"
            np.savez_compressed(
                cache,
                paths=np.array(["a.jpg"]),
                features=np.array([[1.0, 2.0]], dtype=np.float32),
                dataset_version=np.array("v3"),
                pairs_sha256=np.array("abc"),
            )
            features, source = controls.load_or_compute_features(
                ["a.jpg"], "unused", cache, 1, "cpu", False, "v3", "abc",
            )
            self.assertEqual(source, "cache")
            self.assertEqual(features["a.jpg"].tolist(), [1.0, 2.0])
            with self.assertRaises(ValueError):
                controls.load_or_compute_features(
                    ["a.jpg"], "unused", cache, 1, "cpu", False, "v2", "abc",
                )
            with self.assertRaises(ValueError):
                controls.load_or_compute_features(
                    ["a.jpg"], "unused", cache, 1, "cpu", False, "v3", "different",
                )


class UncertaintyTests(unittest.TestCase):
    def test_v3_four_uncertain_cases(self):
        cases = controls.load_uncertain_cases([])
        self.assertEqual(
            {case["pair_id"] for case in cases},
            {"B07Q88MYL4_N1", "B07TTCHRB2_N2", "B07JD7RFRN_N2", "B075H8JNZT_N2"},
        )
        self.assertTrue(all(case["split"] == "train" for case in cases))
        self.assertTrue(all(case["neg_type"] in {"N1", "N2"} for case in cases))


if __name__ == "__main__":
    unittest.main()
