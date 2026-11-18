"""Unit checks for the paired corrected/introduced error analysis."""
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
    "paired_errors", ROOT / "src/eval/paired_errors.py"
)
paired = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paired)

PAIR_ROWS = [
    # anchor, kind, label, baseline score, adapted score, text
    ("A", "pos", 1, 0.9, 0.9, "A positive title"),
    ("A", "N1", 0, 0.8, 0.2, "donor A N1 title"),
    ("B", "pos", 1, 0.4, 0.6, "B positive title"),
    ("B", "N2", 0, 0.1, 0.8, "donor B N2 title"),
    ("C", "pos", 1, 0.9, 0.9, "C positive title"),
    ("C", "N3", 0, 0.1, 0.1, "C rewritten N3 title"),
    ("D", "pos", 1, 0.9, 0.2, "D positive title"),
    ("D", "N3", 0, 0.8, 0.9, "D rewritten N3 title"),
]


class PairedErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_fixture(self, drop_adapted=None):
        pairs_csv = self.directory / "pairs.csv"
        baseline_csv = self.directory / "baseline_scores.csv"
        adapted_csv = self.directory / "adapted_scores.csv"
        provenance_csv = self.directory / "n3_provenance.csv"
        with pairs_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow([
                "pair_id", "label", "neg_type", "split", "anchor_item_id",
                "anchor_group_id", "text_item_id", "text", "label_status",
            ])
            for anchor, kind, label, _, _, text in PAIR_ROWS:
                writer.writerow([
                    f"{anchor}_{kind}", label, kind, "test", anchor,
                    f"group_{anchor}", anchor if label else f"donor_{anchor}",
                    text, "original_listing_unverified" if label else "generated_unreviewed",
                ])
        for path, index in ((baseline_csv, 3), (adapted_csv, 4)):
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(["pair_id", "score"])
                for row in PAIR_ROWS:
                    pair_id = f"{row[0]}_{row[1]}"
                    if drop_adapted and path == adapted_csv and pair_id == drop_adapted:
                        continue
                    writer.writerow([pair_id, row[index]])
        with provenance_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["pair_id", "anchor_item_id", "exchange_id"])
            writer.writerow(["C_N3R2", "C", "exchange-1"])
            writer.writerow(["D_N3R2", "D", "exchange-1"])
        return pairs_csv, baseline_csv, adapted_csv, provenance_csv

    def run_main(self, pairs_csv, baseline_csv, adapted_csv, provenance_csv,
                 extra_args=None):
        out_csv = self.directory / "out.csv"
        args = [
            "--pairs-csv", str(pairs_csv),
            "--baseline-scores", str(baseline_csv),
            "--adapted-scores", str(adapted_csv),
            "--baseline-threshold", "0.5",
            "--adapted-threshold", "0.5",
            "--test-splits", "test",
            "--n3-provenance", str(provenance_csv),
            "--out-csv", str(out_csv),
        ]
        args.extend(extra_args or [])
        paired.main(args)
        return out_csv

    def test_summary_counts(self):
        pairs_csv, baseline_csv, adapted_csv, provenance_csv = self.write_fixture()
        out_csv = self.run_main(
            pairs_csv, baseline_csv, adapted_csv, provenance_csv
        )
        with out_csv.open(newline="", encoding="utf-8") as stream:
            rows = {
                (row["scope"], row["neg_type"]): row
                for row in csv.DictReader(stream)
            }

        all_pairs = rows[("all_pairs", "all")]
        self.assertEqual(all_pairs["n_pairs"], "8")
        self.assertEqual(all_pairs["n_pos"], "4")
        self.assertEqual(all_pairs["n_neg"], "4")
        self.assertEqual(all_pairs["corrected"], "2")
        self.assertEqual(all_pairs["introduced"], "2")
        self.assertEqual(all_pairs["both_correct"], "3")
        self.assertEqual(all_pairs["both_wrong"], "1")
        self.assertAlmostEqual(float(all_pairs["baseline_accuracy"]), 0.625)
        self.assertAlmostEqual(float(all_pairs["adapted_accuracy"]), 0.625)

        n1 = rows[("matched_anchor", "N1")]
        self.assertEqual(n1["n_pairs"], "2")
        self.assertEqual(n1["corrected"], "1")
        self.assertEqual(n1["introduced"], "0")

        n2 = rows[("matched_anchor", "N2")]
        self.assertEqual(n2["corrected"], "1")
        self.assertEqual(n2["introduced"], "1")

        n3 = rows[("matched_anchor", "N3")]
        self.assertEqual(n3["n_pairs"], "4")
        self.assertEqual(n3["n_clusters"], "1")
        self.assertEqual(n3["n_exchanges"], "1")
        self.assertEqual(n3["corrected"], "0")
        self.assertEqual(n3["introduced"], "1")
        self.assertEqual(n3["both_correct"], "2")
        self.assertEqual(n3["both_wrong"], "1")

    def test_ranking_matrix_and_changed_export(self):
        pairs_csv, baseline_csv, adapted_csv, provenance_csv = self.write_fixture()
        out_csv = self.run_main(
            pairs_csv, baseline_csv, adapted_csv, provenance_csv
        )
        ranking_csv = out_csv.with_name(f"{out_csv.stem}_ranking.csv")
        with ranking_csv.open(newline="", encoding="utf-8") as stream:
            ranking = list(csv.DictReader(stream))

        def count(split, neg_type, baseline, adapted):
            return sum(
                int(row["count"]) for row in ranking
                if row["split"] == split and row["neg_type"] == neg_type
                and row["baseline_outcome"] == baseline
                and row["adapted_outcome"] == adapted
            )

        self.assertEqual(count("test", "N1", "win", "win"), 1)
        self.assertEqual(count("test", "N2", "win", "loss"), 1)
        self.assertEqual(count("test", "N3", "win", "loss"), 1)
        self.assertEqual(count("test", "N3", "tie", "tie"), 0)

        changed_csv = out_csv.with_name(f"{out_csv.stem}_changed.csv")
        with changed_csv.open(newline="", encoding="utf-8") as stream:
            changed = list(csv.DictReader(stream))
        self.assertEqual(len(changed), 4)
        by_type = {
            (row["pair_id"], row["change_type"]) for row in changed
        }
        self.assertIn(("A_N1", "corrected"), by_type)
        self.assertIn(("B_pos", "corrected"), by_type)
        self.assertIn(("B_N2", "introduced"), by_type)
        self.assertIn(("D_pos", "introduced"), by_type)
        by_pair = {row["pair_id"]: row for row in changed}
        self.assertEqual(by_pair["D_pos"]["exchange_id"], "exchange-1")
        self.assertEqual(by_pair["A_N1"]["matched_neg_type"], "N1")
        self.assertEqual(by_pair["A_N1"]["text"], "donor A N1 title")
        self.assertEqual(by_pair["A_N1"]["label_status"], "generated_unreviewed")

        report = json.loads(
            out_csv.with_suffix(".json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["changed_counts"]["total"], 4)
        self.assertEqual(report["changed_counts"]["corrected"], 2)
        self.assertEqual(report["changed_counts"]["introduced"], 2)
        self.assertEqual(report["ranking"]["test"]["N3"]["matrix"]["win"]["loss"], 1)

    def test_missing_adapted_score_is_rejected(self):
        pairs_csv, baseline_csv, adapted_csv, provenance_csv = self.write_fixture(
            drop_adapted="B_pos"
        )
        with self.assertRaises(ValueError):
            self.run_main(pairs_csv, baseline_csv, adapted_csv, provenance_csv)

    def test_threshold_is_required(self):
        pairs_csv, baseline_csv, adapted_csv, provenance_csv = self.write_fixture()
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(io.StringIO()):
                paired.main([
                    "--pairs-csv", str(pairs_csv),
                    "--baseline-scores", str(baseline_csv),
                    "--adapted-scores", str(adapted_csv),
                    "--test-splits", "test",
                    "--n3-provenance", str(provenance_csv),
                ])
        self.assertEqual(raised.exception.code, 2)

    def test_ranking_ties_are_counted(self):
        rows = [
            {
                "pair_id": "E_pos", "label": 1, "neg_type": "pos",
                "split": "test", "anchor_item_id": "E", "anchor_group_id": "gE",
                "baseline_score": 0.5, "adapted_score": 0.5,
            },
            {
                "pair_id": "E_N1", "label": 0, "neg_type": "N1",
                "split": "test", "anchor_item_id": "E", "anchor_group_id": "gE",
                "baseline_score": 0.5, "adapted_score": 0.5,
            },
        ]
        units = paired.matched_metrics.matched_units(rows, "N1")
        result = paired.ranking_summary(units)
        self.assertEqual(result["matrix"]["tie"]["tie"], 1)
        self.assertEqual(result["improved"], 0)
        self.assertEqual(result["worsened"], 0)
        self.assertEqual(result["ties_introduced"], 0)
        self.assertEqual(result["ties_removed"], 0)

    def test_original_title_uses_n3_provenance(self):
        row = {
            "label": 0, "neg_type": "N3", "pair_id": "F_N3",
            "anchor_item_id": "F", "text": "rewritten title",
        }
        provenance = {
            "pair_id": "F_N3R2", "anchor_item_id": "F",
            "original_text": "original title",
        }
        self.assertEqual(
            paired.original_title(row, {}, {"F": provenance}),
            "original title",
        )
        self.assertEqual(
            paired.original_title({**row, "label": 1}, {}, {}),
            "rewritten title",
        )


ID_PAIRS = ROOT / "data/releases/abo-home-reciprocal-v3-candidate/pairs.csv"
ID_WORD_SCORES = ROOT / "scores/control_v3_text_word.csv"
ID_CHAR_SCORES = ROOT / "scores/control_v3_text_char.csv"
ID_N3_PROVENANCE = ROOT / "data/releases/abo-home-reciprocal-v3-candidate/n3_provenance.csv"
OOD_DIR = ROOT / "data/releases/abo-ood-v3-20261115-candidate"


@unittest.skipUnless(
    all(path.is_file() for path in (
        ID_PAIRS, ID_WORD_SCORES, ID_CHAR_SCORES, ID_N3_PROVENANCE
    )),
    "ID v3 data or control scores are not present in this checkout",
)
class RealIdIntegrationTests(unittest.TestCase):
    def test_real_id_counts_are_internally_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            out_csv = Path(directory) / "word_vs_char.csv"
            paired.main([
                "--pairs-csv", str(ID_PAIRS),
                "--baseline-scores", str(ID_WORD_SCORES),
                "--adapted-scores", str(ID_CHAR_SCORES),
                "--baseline-threshold", "0.5222853016651217",
                "--adapted-threshold", "0.49939115",
                "--test-splits", "test",
                "--n3-provenance", str(ID_N3_PROVENANCE),
                "--out-csv", str(out_csv),
            ])
            with out_csv.open(newline="", encoding="utf-8") as stream:
                summary = {
                    (row["scope"], row["neg_type"]): row
                    for row in csv.DictReader(stream)
                }
            all_pairs = summary[("all_pairs", "all")]
            self.assertEqual(all_pairs["n_pairs"], "686")
            parts = sum(int(all_pairs[key]) for key in (
                "corrected", "introduced", "both_correct", "both_wrong"
            ))
            self.assertEqual(parts, 686)
            self.assertEqual(summary[("matched_anchor", "N3")]["n_clusters"], "15")

            changed_csv = out_csv.with_name(f"{out_csv.stem}_changed.csv")
            with changed_csv.open(newline="", encoding="utf-8") as stream:
                changed = list(csv.DictReader(stream))
            self.assertEqual(
                len(changed),
                int(all_pairs["corrected"]) + int(all_pairs["introduced"]),
            )


@unittest.skipUnless(
    (OOD_DIR / "eval_pairs.csv").is_file(),
    "OOD candidate is not present in this checkout",
)
class RealOodIntegrationTests(unittest.TestCase):
    def test_ood_splits_and_exchange_counts(self):
        with (OOD_DIR / "eval_pairs.csv").open(
            newline="", encoding="utf-8-sig"
        ) as stream:
            rows = list(csv.DictReader(stream))
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            scores_csv = directory / "scores.csv"
            with scores_csv.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(["pair_id", "score"])
                for row in rows:
                    writer.writerow([
                        row["pair_id"],
                        "1.0" if row["label"] == "1" else "0.0",
                    ])
            out_csv = directory / "ood.csv"
            paired.main([
                "--pairs-csv", str(OOD_DIR / "eval_pairs.csv"),
                "--baseline-scores", str(scores_csv),
                "--adapted-scores", str(scores_csv),
                "--baseline-threshold", "0.5",
                "--adapted-threshold", "0.5",
                "--test-splits", "ood_near", "ood_far",
                "--n3-provenance", str(OOD_DIR / "eval_n3_provenance.csv"),
                "--out-csv", str(out_csv),
            ])
            with out_csv.open(newline="", encoding="utf-8") as stream:
                summary = {
                    (row["split"], row["scope"], row["neg_type"]): row
                    for row in csv.DictReader(stream)
                }
            self.assertEqual(
                summary[("ood_near", "all_pairs", "all")]["n_pairs"], "276"
            )
            self.assertEqual(
                summary[("ood_far", "all_pairs", "all")]["n_pairs"], "292"
            )
            self.assertEqual(
                summary[("ood_near", "matched_anchor", "N3")]["n_clusters"], "6"
            )
            self.assertEqual(
                summary[("ood_far", "matched_anchor", "N3")]["n_clusters"], "5"
            )
            self.assertEqual(
                summary[("ood_near", "matched_anchor", "N3")]["corrected"], "0"
            )


if __name__ == "__main__":
    unittest.main()
