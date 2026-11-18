"""Unit and integration checks for the ID-fitted OOD shortcut probe."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "ood_shortcut", ROOT / "src/eval/ood_shortcut.py"
)
ood = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ood)

VERSION = "abo-ood-v3-20261115-candidate"
FIELDS = [
    "pair_id", "label", "neg_type", "split", "anchor_item_id",
    "anchor_group_id", "text_item_id", "text", "label_status",
    "dataset_version", "image_path", "category", "year",
]
PAIR_ROWS = [
    ("A", "pos", 1, "ood_near", "Amazon Brand Rivet table lamp with linen shade", "LAMP"),
    ("A", "N1", 0, "ood_near", "Amazon Brand Stone Beam accent chair with wood legs", "LAMP"),
    ("B", "pos", 1, "ood_near", "Amazon Brand Rivet ceiling light fixture matte black", "LIGHT_FIXTURE"),
    ("B", "N3", 0, "ood_near", "Amazon Brand Rivet ceiling light fixture matte white", "LIGHT_FIXTURE"),
    ("E", "pos", 1, "ood_near", "Amazon Brand Stone Beam ceiling fixture matte white", "LIGHT_FIXTURE"),
    ("E", "N3", 0, "ood_near", "Amazon Brand Stone Beam ceiling fixture matte black", "LIGHT_FIXTURE"),
    ("C", "pos", 1, "ood_far", "Amazon Essentials mens running shoe black", "SHOES"),
    ("C", "N1", 0, "ood_far", "Amazon Essentials womens sandal brown", "SHOES"),
    ("D", "pos", 1, "ood_far", "Amazon Essentials mens leather boot brown", "BOOT"),
    ("D", "N3", 0, "ood_far", "Amazon Essentials mens leather boot black", "BOOT"),
    ("F", "pos", 1, "ood_far", "Amazon Essentials womens leather boot black", "BOOT"),
    ("F", "N3", 0, "ood_far", "Amazon Essentials womens leather boot brown", "BOOT"),
]
PROVENANCE_ROWS = [
    ("B_N3R2", "B", "exchange-1", "Amazon Brand Rivet ceiling light fixture matte black"),
    ("E_N3R2", "E", "exchange-1", "Amazon Brand Stone Beam ceiling fixture matte white"),
    ("D_N3R2", "D", "exchange-2", "Amazon Essentials mens leather boot brown"),
    ("F_N3R2", "F", "exchange-2", "Amazon Essentials womens leather boot black"),
]


def write_fixture(directory, version=VERSION):
    directory = Path(directory)
    pairs_csv = directory / "eval_pairs.csv"
    provenance_csv = directory / "eval_n3_provenance.csv"
    with pairs_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        for anchor, kind, label, split, text, category in PAIR_ROWS:
            writer.writerow([
                f"{anchor}_{kind}", label, kind, split, anchor, f"group_{anchor}",
                anchor if label else f"donor_{anchor}", text,
                "original_listing_unverified" if label else "generated_unreviewed",
                version, f"small/{anchor.lower()}/{anchor.lower()}.jpg", category, "",
            ])
    with provenance_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["pair_id", "anchor_item_id", "exchange_id", "original_text"])
        writer.writerows(PROVENANCE_ROWS)
    return pairs_csv, provenance_csv


class OodShortcutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_probe(self, pairs_csv, provenance_csv, extra_args=None):
        out_dir = self.directory / "out"
        args = [
            "--ood-pairs-csv", str(pairs_csv),
            "--ood-n3-provenance", str(provenance_csv),
            "--out-dir", str(out_dir),
            "--output-prefix", "probe",
            "--text-features", "word",
            "--bootstrap", "10",
        ]
        args.extend(extra_args or [])
        ood.main(args)
        return out_dir

    def test_probe_uses_id_threshold_and_writes_outputs(self):
        pairs_csv, provenance_csv = write_fixture(self.directory)
        out_dir = self.run_probe(pairs_csv, provenance_csv)

        expected = {
            "probe_text_word.csv",
            "probe_text_word_eval.csv",
            "probe_text_word_eval.json",
            "probe_text_word_eval_matched.csv",
            "probe_image_identity.csv",
            "probe_image_identity_eval.json",
            "probe_meta.json",
            "probe_summary.md",
        }
        self.assertTrue(expected.issubset({path.name for path in out_dir.iterdir()}))

        meta = json.loads((out_dir / "probe_meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["protocol"]["ood_fitting"], False)
        self.assertEqual(meta["ood"]["splits"], ["ood_near", "ood_far"])
        self.assertEqual(meta["ood"]["n_pairs"], 12)
        text_probe = next(
            probe for probe in meta["probes"] if probe["name"] == "text-only word"
        )
        # Frozen ID v3 word control's ID-val threshold.
        self.assertAlmostEqual(text_probe["threshold"], 0.5222853016651217, places=10)
        self.assertEqual(meta["protocol"]["selection_split"], "ID v3 val")

        report = json.loads(
            (out_dir / "probe_text_word_eval.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["selection_split"], "fixed")
        self.assertEqual(report["threshold"], text_probe["threshold"])
        self.assertEqual(
            set(report["matched_types"]), {"ood_near", "ood_far"}
        )
        self.assertEqual(report["matched_types"]["ood_near"]["N3"]["n_clusters"], 1)
        self.assertEqual(report["matched_types"]["ood_far"]["N3"]["n_clusters"], 1)

        summary = (out_dir / "probe_summary.md").read_text(encoding="utf-8")
        self.assertIn("no OOD fitting or tuning", summary)
        self.assertIn("structural null", summary)

    def test_image_probe_is_constant_and_ties(self):
        pairs_csv, provenance_csv = write_fixture(self.directory)
        out_dir = self.run_probe(pairs_csv, provenance_csv)
        with (out_dir / "probe_image_identity.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        self.assertTrue(rows)
        self.assertEqual({float(row["score"]) for row in rows}, {0.5})

        report = json.loads(
            (out_dir / "probe_image_identity_eval.json").read_text(encoding="utf-8")
        )
        for split in ("ood_near", "ood_far"):
            self.assertEqual(report["test_by_split"][split]["auc"], 0.5)
            for metrics in report["matched_types"][split].values():
                self.assertEqual(metrics["auc"], 0.5)
                self.assertEqual(metrics["paired_ranking_accuracy"], 0)
                self.assertEqual(
                    metrics["paired_ranking_ties"], metrics["n_neg"]
                )

    def test_missing_n3_provenance_is_rejected(self):
        pairs_csv, _ = write_fixture(self.directory)
        with self.assertRaises(ValueError):
            ood.main([
                "--ood-pairs-csv", str(pairs_csv),
                "--ood-n3-provenance", "",
                "--out-dir", str(self.directory / "out"),
                "--text-features", "word",
                "--bootstrap", "10",
            ])

    def test_ood_version_mismatch_is_rejected(self):
        pairs_csv, provenance_csv = write_fixture(self.directory, version="wrong")
        with self.assertRaises(ValueError):
            ood.main([
                "--ood-pairs-csv", str(pairs_csv),
                "--ood-n3-provenance", str(provenance_csv),
                "--out-dir", str(self.directory / "out"),
                "--text-features", "word",
                "--bootstrap", "10",
            ])


OOD_DIR = ROOT / "data/releases/abo-ood-v3-20261115-candidate"


@unittest.skipUnless(
    (OOD_DIR / "eval_pairs.csv").is_file(),
    "OOD candidate is not present in this checkout",
)
class RealOodProbeTests(unittest.TestCase):
    def test_real_ood_split_and_exchange_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory) / "out"
            ood.main([
                "--out-dir", str(out_dir),
                "--output-prefix", "probe",
                "--text-features", "word",
                "--bootstrap", "10",
            ])
            meta = json.loads((out_dir / "probe_meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["ood"]["n_pairs"], 568)
            report = json.loads(
                (out_dir / "probe_text_word_eval.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                report["matched_types"]["ood_near"]["N3"]["n_clusters"], 6
            )
            self.assertEqual(
                report["matched_types"]["ood_far"]["N3"]["n_clusters"], 5
            )


if __name__ == "__main__":
    unittest.main()
