"""Unit checks for the shared matched-anchor metrics."""
import contextlib
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "matched_metrics", ROOT / "src/eval/matched_metrics.py"
)
matched = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matched)

spec = importlib.util.spec_from_file_location(
    "shared_eval", ROOT / "src/eval/eval.py"
)
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


def row(anchor, kind, label, score=0.0, split="test", group=None, pair_id=None):
    return {
        "pair_id": pair_id or f"{anchor}_{kind}",
        "label": label,
        "neg_type": kind,
        "split": split,
        "anchor_item_id": anchor,
        "anchor_group_id": group or "group_" + anchor,
        "text_item_id": anchor if label else "donor_" + anchor,
        "score": score,
    }


class MatchedMetricsTests(unittest.TestCase):
    def test_uses_own_anchor_positive_not_all_positives(self):
        rows = [
            row("A", "pos", 1, 0.9),
            row("A", "N3", 0, 0.2),
            row("B", "pos", 1, 0.1),
            row("B", "N1", 0, 0.8),
        ]

        n3 = matched.matched_metrics(matched.matched_units(rows, "N3"), 0.5)
        self.assertEqual(n3["auc"], 1.0)
        self.assertEqual(n3["n_pos"], 1)
        self.assertEqual(n3["n_neg"], 1)
        self.assertEqual(n3["positive_recall"], 1.0)
        self.assertEqual(n3["negative_recall"], 1.0)
        self.assertEqual(n3["balanced_accuracy"], 1.0)
        self.assertEqual(n3["paired_ranking_accuracy"], 1.0)
        self.assertEqual(n3["n_clusters"], 1)
        self.assertEqual(n3["cluster"], matched.ANCHOR_CLUSTER)

        n1 = matched.matched_metrics(matched.matched_units(rows, "N1"), 0.5)
        self.assertEqual(n1["auc"], 0.0)
        self.assertEqual(n1["positive_recall"], 0.0)
        self.assertEqual(n1["negative_recall"], 0.0)
        self.assertEqual(n1["balanced_accuracy"], 0.0)
        self.assertEqual(n1["paired_ranking_accuracy"], 0.0)

    def test_paired_ranking_ties_are_failures(self):
        rows = [
            row("A", "pos", 1, 0.5),
            row("A", "N2", 0, 0.5),
        ]
        metrics = matched.matched_metrics(matched.matched_units(rows, "N2"), 0.5)
        self.assertEqual(metrics["positive_recall"], 1.0)
        self.assertEqual(metrics["negative_recall"], 0.0)
        self.assertEqual(metrics["balanced_accuracy"], 0.5)
        self.assertEqual(metrics["paired_ranking_accuracy"], 0.0)
        self.assertEqual(metrics["paired_ranking_ties"], 1)

    def test_exchange_bootstrap_resamples_complete_exchanges(self):
        rows = [
            row("A", "pos", 1, 0.9), row("A", "N3", 0, 0.2),
            row("B", "pos", 1, 0.8), row("B", "N3", 0, 0.1),
            row("C", "pos", 1, 0.2), row("C", "N3", 0, 0.7),
            row("D", "pos", 1, 0.1), row("D", "N3", 0, 0.6),
        ]
        exchange_map = {
            "A_N3": "exchange-1", "B_N3": "exchange-1",
            "C_N3": "exchange-2", "D_N3": "exchange-2",
        }
        units = matched.matched_units(rows, "N3", exchange_map)
        metrics = matched.matched_metrics(units, 0.5)
        self.assertEqual(metrics["n_clusters"], 2)
        self.assertEqual(metrics["n_exchanges"], 2)
        self.assertEqual(metrics["cluster"], matched.EXCHANGE_CLUSTER)
        self.assertEqual(metrics["paired_ranking_accuracy"], 0.5)

        first = matched.matched_bootstrap(units, 0.5, 50, 3)
        second = matched.matched_bootstrap(units, 0.5, 50, 3)
        self.assertEqual(first, second)
        self.assertEqual(first["auc"]["valid_resamples"], 50)
        self.assertLessEqual(first["auc"]["low"], first["auc"]["high"])

    def test_partial_exchange_is_rejected(self):
        rows = [
            row("A", "pos", 1, 0.9),
            row("A", "N3", 0, 0.2),
        ]
        with self.assertRaises(ValueError):
            matched.matched_units(rows, "N3", {"A_N3": "exchange-1"})


class ProvenanceJoinTests(unittest.TestCase):
    def test_ood_pair_ids_join_by_anchor(self):
        rows = [row("A", "pos", 1, 0.9), row("A", "N3", 0, 0.2)]
        provenance = [{
            "pair_id": "A_N3R2",
            "anchor_item_id": "A",
            "exchange_id": "exchange-1",
        }]
        self.assertEqual(
            matched.build_exchange_map(rows, provenance), {"A_N3": "exchange-1"}
        )

    def test_id_pair_ids_join_directly(self):
        rows = [row("A", "pos", 1, 0.9), row("A", "N3", 0, 0.2)]
        provenance = [{"pair_id": "A_N3", "exchange_id": "exchange-1"}]
        self.assertEqual(
            matched.build_exchange_map(rows, provenance), {"A_N3": "exchange-1"}
        )

    def test_missing_provenance_is_rejected(self):
        rows = [row("A", "pos", 1, 0.9), row("A", "N3", 0, 0.2)]
        with self.assertRaises(ValueError):
            matched.build_exchange_map(rows, [])


class EvaluatorCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_fixture(self, stem, include_n3_provenance=True):
        pairs_csv = self.directory / f"{stem}_pairs.csv"
        scores_csv = self.directory / f"{stem}_scores.csv"
        provenance_csv = self.directory / f"{stem}_n3_provenance.csv"
        pair_rows = [
            ("A", "pos", 1, 0.9), ("A", "N1", 0, 0.1),
            ("B", "pos", 1, 0.9), ("B", "N3", 0, 0.4),
            ("C", "pos", 1, 0.9), ("C", "N3", 0, 0.1),
        ]
        with pairs_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow([
                "pair_id", "label", "neg_type", "split",
                "anchor_item_id", "anchor_group_id", "text_item_id",
            ])
            for anchor, kind, label, _ in pair_rows:
                writer.writerow([
                    f"{anchor}_{kind}", label, kind, "test", anchor,
                    f"group_{anchor}", anchor if label else f"donor_{anchor}",
                ])
        with scores_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["pair_id", "score"])
            for anchor, kind, _, score in pair_rows:
                writer.writerow([f"{anchor}_{kind}", score])
        if include_n3_provenance:
            with provenance_csv.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(["pair_id", "anchor_item_id", "exchange_id"])
                writer.writerow(["B_N3R2", "B", "exchange-1"])
                writer.writerow(["C_N3R2", "C", "exchange-1"])
        return pairs_csv, scores_csv, provenance_csv

    def test_cli_writes_matched_csv_and_metadata(self):
        pairs_csv, scores_csv, provenance_csv = self.write_fixture("matched")
        evaluator.main([
            "--pairs-csv", str(pairs_csv),
            "--scores-csv", str(scores_csv),
            "--test-splits", "test",
            "--fixed-threshold", "0.5",
            "--matched-type-metrics",
            "--n3-provenance", str(provenance_csv),
            "--bootstrap", "20",
        ])
        matched_csv = self.directory / "matched_scores_eval_matched.csv"
        self.assertTrue(matched_csv.is_file())
        with matched_csv.open(newline="", encoding="utf-8") as stream:
            rows = {row["neg_type"]: row for row in csv.DictReader(stream)}
        n1 = rows["N1"]
        self.assertEqual(n1["n_pos"], "1")
        self.assertEqual(n1["n_neg"], "1")
        self.assertEqual(n1["n_clusters"], "1")
        self.assertEqual(n1["cluster"], matched.ANCHOR_CLUSTER)
        self.assertEqual(float(n1["auc"]), 1.0)
        self.assertEqual(float(n1["paired_ranking_accuracy"]), 1.0)
        n3 = rows["N3"]
        self.assertEqual(n3["n_pos"], "2")
        self.assertEqual(n3["n_neg"], "2")
        self.assertEqual(n3["n_clusters"], "1")
        self.assertEqual(n3["n_exchanges"], "1")
        self.assertEqual(n3["cluster"], matched.EXCHANGE_CLUSTER)
        self.assertEqual(float(n3["balanced_accuracy"]), 1.0)
        self.assertEqual(float(n3["paired_ranking_accuracy"]), 1.0)
        self.assertEqual(n3["paired_ranking_ties"], "0")

        report = json.loads(
            (self.directory / "matched_scores_eval.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["matched_types"]["test"]["N3"]["n_clusters"], 1)
        self.assertEqual(
            report["matched_metadata"]["n3_exchanges_by_split"], {"test": 1}
        )
        markdown = (self.directory / "matched_scores_eval.md").read_text(encoding="utf-8")
        self.assertIn("Matched-anchor type metrics", markdown)

    def test_matched_output_is_opt_in(self):
        pairs_csv, scores_csv, _ = self.write_fixture(
            "plain", include_n3_provenance=False
        )
        evaluator.main([
            "--pairs-csv", str(pairs_csv),
            "--scores-csv", str(scores_csv),
            "--test-splits", "test",
            "--fixed-threshold", "0.5",
        ])
        self.assertFalse(
            (self.directory / "plain_scores_eval_matched.csv").exists()
        )

    def test_n3_requires_provenance(self):
        pairs_csv, scores_csv, _ = self.write_fixture(
            "missing", include_n3_provenance=False
        )
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(io.StringIO()):
                evaluator.main([
                    "--pairs-csv", str(pairs_csv),
                    "--scores-csv", str(scores_csv),
                    "--test-splits", "test",
                    "--fixed-threshold", "0.5",
                    "--matched-type-metrics",
                ])
        self.assertEqual(raised.exception.code, 2)


OOD_DIR = ROOT / "data/releases/abo-ood-v3-20261115-candidate"


@unittest.skipUnless(
    (OOD_DIR / "eval_pairs.csv").is_file(),
    "OOD candidate is not present in this checkout",
)
class RealOodTableTests(unittest.TestCase):
    def test_every_retained_n3_pair_maps_to_a_complete_exchange(self):
        with (OOD_DIR / "eval_pairs.csv").open(
            newline="", encoding="utf-8-sig"
        ) as stream:
            rows = list(csv.DictReader(stream))
        with (OOD_DIR / "eval_n3_provenance.csv").open(
            newline="", encoding="utf-8-sig"
        ) as stream:
            provenance = list(csv.DictReader(stream))
        for row in rows:
            row["label"] = int(row["label"])
            row["score"] = 1.0 if row["label"] == 1 else 0.0
        exchange_map = matched.build_exchange_map(rows, provenance)
        n3_rows = [row for row in rows if row["neg_type"] == "N3"]
        self.assertEqual(len(exchange_map), len(n3_rows))
        for split in ("ood_near", "ood_far"):
            split_rows = [row for row in rows if row["split"] == split]
            units = matched.matched_units(split_rows, "N3", exchange_map)
            metrics = matched.matched_metrics(units, 0.5)
            expected = len({
                exchange_map[row["pair_id"]] for row in n3_rows
                if row["split"] == split
            })
            self.assertEqual(metrics["n_clusters"], expected)
            self.assertEqual(metrics["auc"], 1.0)


if __name__ == "__main__":
    unittest.main()
