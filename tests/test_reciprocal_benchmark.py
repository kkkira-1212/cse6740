"""Release-level safeguards for the new candidate and review exclusions."""
import csv
from collections import Counter, defaultdict
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


class ReciprocalBenchmarkTests(unittest.TestCase):
    def test_exchanges_and_review_exclusions(self):
        release = ROOT/'data/releases/abo-home-reciprocal-v3-candidate'
        provenance = read(release/'n3_provenance.csv')
        retained = {r['source_pair_id'] for r in provenance}
        decisions = read(ROOT/'data/reviews/reciprocal-v3-model-assisted/decisions.csv')
        exchanges = defaultdict(list)
        for r in decisions:
            exchanges[r['exchange_id']].append(r)
        for group in exchanges.values():
            self.assertEqual(len(group), 2)
            accepted = all(r['negative_decision'] == 'mismatch' and
                           r['original_color_check'] == 'consistent' for r in group)
            self.assertEqual([r['pair_id'] in retained for r in group], [accepted, accepted])

    def test_no_old_n3_and_balanced_color_phrases(self):
        release = ROOT/'data/releases/abo-home-reciprocal-v3-candidate'
        rows = read(release/'pairs.csv')
        source = {r['pair_id']:r for r in read(release/'heldout_n3_candidates.csv')}
        train = read(ROOT/'data/reviews/n3-reciprocal-expanded-dev-v2/training_negatives.csv')
        by_anchor = {r['anchor_item_id']:r for r in [*train, *source.values()]}
        groups = defaultdict(list)
        for r in rows:
            if r['neg_type'] == 'N3':
                s = by_anchor[r['anchor_item_id']]
                self.assertEqual(s['text'], r['text'])
                groups[(r['split'],r['category'])].append(s)
        for group in groups.values():
            self.assertEqual(Counter(r['old_value'].casefold() for r in group),
                             Counter(r['new_value'].casefold() for r in group))
        self.assertEqual(len({r['pair_id'] for r in rows}),len(rows))


if __name__ == '__main__':
    unittest.main()
