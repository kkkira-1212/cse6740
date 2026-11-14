"""Release-level safeguards for the new candidate and review exclusions."""
import csv
from collections import Counter, defaultdict
from pathlib import Path
import unittest
import sys
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/negatives/reciprocal'))
from build_benchmark_candidate import fallback_negatives


def read(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


class ReciprocalBenchmarkTests(unittest.TestCase):
    def test_followup_binds_original_inputs_without_changing_training_labels(self):
        folder = ROOT/'data/reviews/reciprocal-v3-model-assisted'
        manifest = json.loads((folder/'fallback_adjudication_manifest.json').read_text())
        digest = lambda p: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        self.assertEqual(digest(folder/'fallback_train_spotcheck.csv'), manifest['source_ledger_sha256'])
        self.assertEqual(digest(folder/'fallback_train_adjudications.csv'), manifest['adjudications_sha256'])
        pairs_path = ROOT/'data/releases/abo-home-reciprocal-v3-candidate/pairs.csv'
        self.assertEqual(digest(pairs_path), manifest['candidate_pairs_sha256'])
        original = {r['pair_id']:r for r in read(folder/'fallback_train_spotcheck.csv')}
        pairs = {r['pair_id']:r for r in read(pairs_path)}
        followup = read(folder/'fallback_train_adjudications.csv')
        self.assertEqual(len(followup), 6)
        self.assertEqual(len({r['pair_id'] for r in followup}), 6)
        for r in followup:
            old = original[r['pair_id']]
            for key in ('text', 'split', 'image_path', 'image_sha256'):
                self.assertEqual(r[key], old[key])
            self.assertEqual(r['previous_decision'], old['decision'])
            self.assertEqual(r['source_ledger_sha256'], manifest['source_ledger_sha256'])
            self.assertEqual(r['candidate_commit'], manifest['candidate_commit'])
            self.assertEqual(r['candidate_pairs_sha256'], manifest['candidate_pairs_sha256'])
            self.assertEqual(r['reviewer_type'], 'model_assisted')
            self.assertEqual(r['applied_to_training_labels'], 'false')
            self.assertEqual(pairs[r['pair_id']]['label_status'], 'generated_unreviewed')
        current = {k:r['decision'] for k,r in original.items()}
        current.update({r['pair_id']:r['proposed_decision'] for r in followup})
        self.assertEqual(sorted(k for k,v in current.items() if v == 'uncertain'),
                         sorted(manifest['current_proposed_uncertain_pairs']))
        self.assertEqual(Counter(current.values()), {'mismatch':16, 'uncertain':4})

    def test_all_anchors_positives_and_existing_n1_n2_preserved(self):
        old = read(ROOT/'data/releases/abo-home-v2-20261103/pairs.csv')
        new = read(ROOT/'data/releases/abo-home-reciprocal-v3-candidate/pairs.csv')
        self.assertEqual(len(old), len(new))
        self.assertEqual(Counter(r['anchor_item_id'] for r in old), Counter(r['anchor_item_id'] for r in new))
        by_id = {r['pair_id']:r for r in new}
        for r in old:
            if r['neg_type'] in ('pos', 'N1', 'N2'):
                self.assertEqual({k:v for k,v in r.items() if k != 'dataset_version'},
                                 {k:v for k,v in by_id[r['pair_id']].items() if k != 'dataset_version'})

    def test_fallback_donor_legality_and_split_isolation(self):
        items = read(ROOT/'data/releases/abo-home-v2-20261103/items.csv')
        rows = read(ROOT/'data/releases/abo-home-reciprocal-v3-candidate/pairs.csv')
        ix = {r['item_id']:r for r in items}
        by_id = {r['pair_id']:r for r in rows}
        provenance = read(ROOT/'data/releases/abo-home-reciprocal-v3-candidate/fallback_provenance.csv')
        self.assertEqual(len(provenance), 450)
        for p in provenance:
            row = by_id[p['pair_id']]
            a, d = ix[p['anchor_item_id']], ix[p['donor_item_id']]
            self.assertEqual(a['split'], d['split'])
            self.assertNotEqual(a['group_id'], d['group_id'])
            self.assertNotEqual(a['image_path'], d['image_path'])
            self.assertNotEqual(a['title'].strip().casefold(), d['title'].strip().casefold())
            self.assertEqual(a['product_type'] == d['product_type'], row['neg_type'] == 'N2')
            self.assertEqual(row['text'], d['title'])

    def test_no_legal_donor_fails_instead_of_cross_split_fallback(self):
        items = [dict(item_id='a', split='train', group_id='a', product_type='CHAIR', image_path='a', title='chair'),
                 dict(item_id='b', split='test', group_id='b', product_type='CHAIR', image_path='b', title='other chair')]
        negatives = {r['item_id']:dict(neg_type='N3',split=r['split']) for r in items}
        with self.assertRaisesRegex(ValueError, 'No legal'):
            fallback_negatives(items, negatives, {})

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
