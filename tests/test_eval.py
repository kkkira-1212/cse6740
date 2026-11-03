"""Regression checks for ranking semantics and cluster resampling."""
import importlib.util
import csv
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

spec = importlib.util.spec_from_file_location(
    "shared_eval", Path(__file__).resolve().parents[1] / "src/eval/eval.py"
)
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


def row(item, kind, score, split="test"):
    return dict(text_item_id=item, neg_type=kind, label=int(kind == "pos"),
                score=score, split=split)


class RankingTests(unittest.TestCase):
    def test_rewritten_n3_is_not_an_image_retrieval_candidate(self):
        rows = [row("A", "pos", .8), row("A", "N1", .1),
                row("A", "N2", .2), row("A", "N3", .9)]
        self.assertEqual(evaluator.within_title_r_at_1(rows), 1.)

    def test_incomplete_retrieval_group_is_not_a_three_way_query(self):
        rows = [row("A", "pos", .8), row("A", "N1", .1)]
        self.assertIsNone(evaluator.within_title_r_at_1(rows))

    def test_bootstrap_preserves_repeated_cluster_weight(self):
        rows = [row("A", "pos", .9), row("A", "N1", .1), row("A", "N2", .2),
                row("B", "pos", .8), row("B", "N1", .1), row("B", "N2", .2),
                row("C", "pos", .1), row("C", "N1", .8), row("C", "N2", .9)]

        class FixedDraw:
            def choice(self, *args, **kwargs):
                return np.array([0, 0, 2])

        with patch.object(evaluator.np.random, "default_rng", return_value=FixedDraw()):
            result = evaluator.bootstrap_ci(rows, .5, 1, 0, True)
        self.assertAlmostEqual(result["r_at_1"]["low"], 2 / 3)

    def test_equal_item_ids_across_test_splits_are_separate_queries(self):
        rows = [row("A", "pos", .9), row("A", "N1", .1), row("A", "N2", .2),
                row("A", "pos", .1, "ood_near"), row("A", "N1", .8, "ood_near"),
                row("A", "N2", .9, "ood_near")]
        self.assertEqual(evaluator.within_title_r_at_1(rows), .5)


class V2ValidationTests(unittest.TestCase):
    def files(self, directory):
        pairs = Path(directory) / "pairs.csv"
        fields = ["pair_id", "label", "neg_type", "split", "anchor_item_id", "anchor_group_id", "text_item_id", "image_path"]
        rows = []
        for anchor, split in [("A", "val"), ("B", "test")]:
            for kind, label in [("pos", 1), ("N2", 0)]:
                rows.append(dict(pair_id=anchor+"_"+kind,label=label,neg_type=kind,split=split,
                    anchor_item_id=anchor,anchor_group_id="group_"+anchor,
                    text_item_id=anchor if label else "donor_"+anchor,image_path=anchor+".jpg"))
        with pairs.open("w",newline="") as f:
            w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
        return pairs, rows

    def test_v2_explicit_title_source_and_image_cluster_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            pairs,_=self.files(directory)
            loaded=evaluator.load_pairs(pairs)
            negative=loaded[1]
            self.assertEqual(negative["text_item_id"],"donor_A")
            self.assertEqual(negative["query_id"],"A")
            self.assertEqual(negative["cluster_id"],"group_A")
            with self.assertRaises(ValueError):
                evaluator.within_title_r_at_1(loaded)

    def test_validation_threshold_does_not_depend_on_test_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            pairs,rows=self.files(directory)
            scores=Path(directory)/"scores.csv"
            result=Path(directory)/"result.json"
            thresholds=[]
            for value in [.01,.99]:
                with scores.open("w",newline="") as f:
                    w=csv.writer(f);w.writerow(["pair_id","score"])
                    for r in rows:
                        score=(.8 if r["label"] else .2) if r["split"]=="val" else value
                        w.writerow([r["pair_id"],score])
                evaluator.main(["--pairs-csv",str(pairs),"--scores-csv",str(scores),
                    "--out-json",str(result),"--out-csv",str(Path(directory)/"metrics.csv"),
                    "--out-md",str(Path(directory)/"metrics.md"),"--bootstrap","3"])
                report=json.loads(result.read_text())
                thresholds.append(report["threshold"])
                self.assertEqual(report["bootstrap"]["cluster"],"image_anchor_group")
                self.assertEqual(report["pair_layout"],"fixed_image_v2")
            self.assertEqual(thresholds,[.8,.8])

    def test_cli_rejects_v2_ranking_before_reading_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            pairs,_=self.files(directory)
            with self.assertRaises(SystemExit) as error:
                evaluator.main(["--pairs-csv",str(pairs),"--scores-csv","not-needed.csv","--r-at-1"])
            self.assertEqual(error.exception.code,2)


if __name__ == "__main__":
    unittest.main()
