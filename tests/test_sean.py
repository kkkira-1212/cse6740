"""Checks for mistakes that would invalidate the data or human-review export."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'negatives'))
from build_n3 import make_candidates, raw_color_safe
from build_ood import select_items, build_pairs
from build_review import sample_review
from finalize_review import finalize, summarize


def item(i='A', title='Brand Navy Blue Velvet Sofa', color='Blue', **kw):
    return dict(item_id=i, title=title, color=color, material='Velvet', image_path=f'small/{i}.jpg',
                product_type='SOFA', group_id='g' + i, split='train', **kw)


class N3Tests(unittest.TestCase):
    def test_longest_span_and_preservation(self):
        it = item()
        pairs, audit, skipped = make_candidates([it])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(audit[0]['old_value'], 'Navy Blue')
        self.assertNotIn('Blue', pairs[0]['text'])
        self.assertEqual(pairs[0]['image_path'], it['image_path'])
        self.assertEqual(pairs[0]['split'], 'train')
        self.assertEqual(pairs[0]['label'], 0)
        self.assertEqual(pairs[0]['text'].split(' Velvet')[1], ' Sofa')
        self.assertFalse(skipped)

    def test_reject_multicolor_mismatch_and_unknown(self):
        for title, color in [('Black Chair with White Cushion', 'Black'),
                             ('Two-Tone Black Chair', 'Black'),
                             ('Blue Chair', 'Black'), ('Natural Wood Chair', 'Natural'),
                             ('Blueblue Chair', 'Blue')]:
            with self.subTest(title=title):
                self.assertFalse(make_candidates([item(title=title, color=color)])[0])

    def test_raw_multivalue_and_pattern_rejected(self):
        good = {'language_tag': 'en_US', 'value': 'Navy', 'standardized_values': ['Blue']}
        self.assertTrue(raw_color_safe([good]))
        self.assertFalse(raw_color_safe([good, good]))
        self.assertFalse(raw_color_safe([{**good, 'value': 'Navy/White'}]))
        self.assertFalse(raw_color_safe([{**good, 'standardized_values': ['Blue', 'White']}]))
        self.assertFalse(make_candidates([item()], raw={})[0])

    def test_repeatability_and_duplicate_ids(self):
        rows = [item('A'), item('B')]
        self.assertEqual(make_candidates(rows)[0], make_candidates(rows[::-1])[0])
        with self.assertRaises(ValueError):
            make_candidates([item(), item()])


class OODTests(unittest.TestCase):
    def record(self, i, pt, image):
        return dict(item_id=i, product_type=[{'value': pt}], main_image_id=image,
                    item_name=[{'value': 'Black ' + pt + i, 'language_tag': 'en_US'}],
                    color=[{'value': 'Black', 'language_tag': 'en_US'}])

    def test_protect_existing_images_and_groups(self):
        existing = [item()]
        records = [self.record('B', 'LAMP', 'shared'), self.record('C', 'LAMP', 'c'),
                   self.record('D', 'SHOES', 'd')]
        selected, raw, skipped = select_items(records, existing,
            {'shared': 'A.jpg', 'c': 'c.jpg', 'd': 'd.jpg'},
            {'ood_near': ['LAMP'], 'ood_far': ['SHOES']}, 10, 42)
        self.assertEqual({r['item_id'] for r in selected}, {'C', 'D'})
        self.assertEqual(skipped['overlap_with_existing_group'], 1)

    def test_category_overlap_rejected(self):
        with self.assertRaises(ValueError):
            select_items([], [item()], {}, {'ood_near': ['SOFA'], 'ood_far': ['SHOES']}, 1, 42)

    def test_negative_mining_stays_in_tier_and_category(self):
        import numpy as np
        rows = [item(str(i)) for i in range(6)]
        for i, r in enumerate(rows):
            r['split'] = 'ood_near' if i < 3 else 'ood_far'
            r['product_type'] = 'LAMP' if i < 3 else 'SHOES'
        pairs, _ = build_pairs(rows, np.eye(6))
        lookup = {r['item_id']: r for r in rows}
        for p in pairs:
            self.assertEqual(lookup[p['item_id']]['split'], p['split'])
            if p['neg_type'] != 'pos':
                source = lookup[p['pair_id'].rsplit('_', 1)[0]]
                self.assertNotEqual(source['group_id'], lookup[p['item_id']]['group_id'])
                self.assertEqual(source['product_type'], lookup[p['item_id']]['product_type'])


class ReviewTests(unittest.TestCase):
    def setup_rows(self):
        items = [item('A'), item('B'), item('C')]
        pairs, audit, _ = make_candidates(items)
        sample = sample_review(items, pairs, audit, 3)
        return pairs, sample

    def test_pending_is_never_approved(self):
        pairs, sample = self.setup_rows()
        approved, summary = finalize(sample, sample, pairs)
        self.assertEqual(approved, [])
        self.assertIsNone(summary['N3']['false_negative_rate'])

    def test_only_individually_accepted_rows_exported(self):
        pairs, sample = self.setup_rows()
        reviews = deepcopy(sample)
        for row, decision in zip(reviews, ['mismatch', 'match', 'uncertain']):
            row['review_decision'] = decision
        approved, summary = finalize(reviews, sample, pairs)
        self.assertEqual([p['pair_id'] for p in approved], [reviews[0]['pair_id']])
        self.assertEqual(summary['N3']['false_negative_rate'], .5)
        self.assertEqual(summary['N3']['determinate'], 2)

    def test_changed_text_and_dropped_rows_rejected(self):
        pairs, sample = self.setup_rows()
        with self.assertRaises(ValueError):
            finalize(sample[:-1], sample, pairs)
        changed = deepcopy(sample)
        changed[0]['text'] = 'tampered'
        with self.assertRaises(ValueError):
            finalize(changed, sample, pairs)


if __name__ == '__main__':
    unittest.main()
