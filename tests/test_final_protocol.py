import unittest

from src.eval.final_protocol import (matched_metrics, n3_exchange_bootstrap,
                                     prediction_transitions, ranking_transitions)


def row(pair_id, anchor, label, kind, score):
    return {"pair_id": pair_id, "anchor_item_id": anchor, "label": label,
            "neg_type": kind, "score": score}


class FinalProtocolTests(unittest.TestCase):
    def setUp(self):
        self.reference = [row("a_pos", "a", 1, "pos", .8), row("a_N3", "a", 0, "N3", .7),
                          row("b_pos", "b", 1, "pos", .4), row("b_N3", "b", 0, "N3", .5)]
        self.candidate = [row("a_pos", "a", 1, "pos", .9), row("a_N3", "a", 0, "N3", .2),
                          row("b_pos", "b", 1, "pos", .8), row("b_N3", "b", 0, "N3", .1)]

    def test_matched_metrics_use_corresponding_positives(self):
        result = matched_metrics(self.reference, "N3", .6)
        self.assertEqual(result["n_pos"], 2)
        self.assertEqual(result["paired_ranking_wins"], 1)
        self.assertEqual(result["paired_ranking_ties"], 0)
        self.assertAlmostEqual(result["positive_recall"], .5)
        self.assertAlmostEqual(result["negative_recall"], .5)

    def test_paired_error_and_ranking_transitions(self):
        result = prediction_transitions(self.reference, self.candidate, .6, .6, {"N3"})
        self.assertEqual(result["wrong_to_correct"], 2)
        ranking = ranking_transitions(self.reference, self.candidate, {"N3"})["N3"]
        self.assertEqual(ranking["loss_to_win"], 1)
        self.assertEqual(ranking["win_to_win"], 1)

    def test_exchange_bootstrap_is_deterministic(self):
        exchange = {"a_N3": "x", "b_N3": "x"}
        first = n3_exchange_bootstrap(self.reference, exchange, .6, 20, 7)
        second = n3_exchange_bootstrap(self.reference, exchange, .6, 20, 7)
        self.assertEqual(first, second)
        self.assertEqual(first["n_exchanges"], 1)


if __name__ == "__main__":
    unittest.main()
