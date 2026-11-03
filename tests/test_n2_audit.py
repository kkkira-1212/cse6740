"""Protect audit orientation, candidate isolation and review provenance."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/negatives'))
from build_n2_audit import (clean_pool, donor_groups, eligible_types, sample_pairs,
                            summarize_review)


def fixture():
    rows = []
    for pt in ['CHAIR', 'SOFA']:
        for split, n in [('train', 4), ('val', 2), ('test', 2)]:
            for i in range(n):
                key = f'{pt}-{split}-{i}'
                rows.append(dict(item_id=key, title=f'{pt} model {split} {i}',
                    image_path=f'small/{key}.jpg', product_type=pt, group_id=key, split=split))
    return rows


class AuditTests(unittest.TestCase):
    def test_fixed_image_same_type_train_and_different_groups(self):
        items = fixture()
        clean, _ = clean_pool(items)
        types, _, positives = eligible_types(items, clean, 6, 2, 2, 2)
        rows, quotas = sample_pairs(items, clean, types, positives, 6, 42)
        lookup = {r['item_id']: r for r in items}
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({r['anchor_group_id'] for r in rows}), 6)
        for r in rows:
            anchor, donor = lookup[r['anchor_item_id']], lookup[r['text_item_id']]
            self.assertEqual(r['image_path'], anchor['image_path'])
            self.assertEqual(r['text'], donor['title'])
            self.assertEqual(r['image_item_id'], anchor['item_id'])
            self.assertEqual(anchor['product_type'], donor['product_type'])
            self.assertEqual((anchor['split'], donor['split']), ('train', 'train'))
            self.assertNotEqual(anchor['group_id'], donor['group_id'])
        reverse, _ = sample_pairs(items, clean[::-1], types, positives, 6, 42)
        self.assertEqual(rows, reverse)

    def test_shared_images_are_removed_before_counting(self):
        items = fixture()
        items[0]['image_path'] = items[4]['image_path']  # train/val overlap
        clean, excluded = clean_pool(items)
        self.assertEqual(len(excluded), 2)
        self.assertTrue(all('image_spans_splits' in r['reason'] for r in excluded))
        types, report, _ = eligible_types(items, clean, 6, 2, 2, 2)
        self.assertNotIn('CHAIR', types)  # only one remaining validation group
        self.assertIn('SOFA', types)

    def test_actual_legal_pool_is_checked_after_title_exclusions(self):
        items = fixture()
        val = [r for r in items if r['product_type'] == 'CHAIR' and r['split'] == 'val']
        val[1]['title'] = val[0]['title']
        clean, _ = clean_pool(items)
        types, report, _ = eligible_types(items, clean, 6, 2, 2, 2)
        self.assertNotIn('CHAIR', types)
        r = next(r for r in report if r['product_type'] == 'CHAIR')
        self.assertIn('too_few_valid_val_donor_groups', r['reason'])

    def test_existing_positive_input_cannot_be_relabelled_negative(self):
        items = fixture()
        anchor, donor = items[0], items[1]
        positives = {(anchor['image_path'], donor['title'].casefold())}
        candidates = donor_groups(anchor, items, positives)
        self.assertNotIn(donor['group_id'], candidates)

    def batch(self):
        items = fixture()
        clean, _ = clean_pool(items)
        types, _, positives = eligible_types(items, clean, 6, 2, 2, 2)
        rows, _ = sample_pairs(items, clean, types, positives, 6, 42)
        for r in rows:
            r['dataset_id'] = 'test-batch'
        return rows

    def test_review_counts_do_not_promote_pending_or_uncertain(self):
        sample = self.batch()
        reviews = deepcopy(sample)
        for r, d in zip(reviews, ['mismatch', 'match', 'uncertain', '', '', 'mismatch']):
            r['review_decision'] = d
        result = summarize_review(sample, reviews)['overall']
        self.assertEqual(result['determinate'], 3)
        self.assertAlmostEqual(result['match_flag_rate'], 1 / 3)
        self.assertEqual(result['counts']['pending'], 2)

    def test_wrong_batch_changed_input_and_dropped_rows_are_rejected(self):
        sample = self.batch()
        for field, value in [('dataset_id', 'other'), ('text', 'Changed title'),
                             ('image_path', 'small/other.jpg')]:
            reviews = deepcopy(sample)
            reviews[0][field] = value
            with self.assertRaises(ValueError):
                summarize_review(sample, reviews)
        with self.assertRaises(ValueError):
            summarize_review(sample, sample[:-1])


if __name__ == '__main__':
    unittest.main()
