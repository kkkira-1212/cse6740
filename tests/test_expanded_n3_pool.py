"""Keep sample quality control separate from per-row human approval."""
from copy import deepcopy
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/negatives/reciprocal'))
import build_expanded_n3 as expanded
from build_training_pool import build_pool,paired_rows


class ExpandedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=ROOT/'data/reviews/n3-reciprocal-dev-v1'
        cls.new=ROOT/'data/reviews/n3-reciprocal-expanded-dev-v2'
        cls.items=expanded.read(ROOT/'data/releases/abo-home-v2-20261103/items.csv')
        cls.ledger=expanded.read(ROOT/'data/releases/abo-home-v2-20261103/n3_audit.csv')
        cls.args=[expanded.read(p) for p in [cls.old/'review_sample.csv',cls.old/'review_completed.csv',
            cls.new/'n3_candidates.csv',cls.new/'review_sample.csv',cls.new/'review_completed.csv']]

    def test_expanded_candidates_reproduce_without_prior_anchors(self):
        rows,_=expanded.generate(self.items,self.ledger,self.args[1])
        reverse,_=expanded.generate(self.items[::-1],self.ledger[::-1],self.args[1][::-1])
        self.assertEqual(rows,self.args[2]);self.assertEqual(rows,reverse)
        self.assertEqual(len(rows),208)
        self.assertTrue({r['anchor_item_id'] for r in rows}.isdisjoint({r['anchor_item_id'] for r in self.args[1]}))
        self.assertEqual({r['split'] for r in rows},{'train'})
        expanded.validate(rows,self.items)

    def test_unsampled_rows_are_allowed_but_never_human_approved(self):
        pool,reviewed,excluded,summary=build_pool(*self.args)
        self.assertEqual((len(pool),len(reviewed),len(excluded)),(266,158,2))
        self.assertEqual(Counter(r['review_status'] for r in pool),Counter(reviewed_mismatch=158,unreviewed=108))
        self.assertTrue(all(r['review_decision']=='' and r['label_status']=='generated_unreviewed' for r in pool if r['review_status']=='unreviewed'))
        self.assertEqual(pool,expanded.read(self.new/'training_negatives.csv'))
        self.assertEqual(reviewed,expanded.read(self.new/'reviewed_negatives.csv'))
        self.assertTrue({r['exchange_id'] for r in excluded}.isdisjoint({r['exchange_id'] for r in pool}))
        for cat in {r['category'] for r in pool}:
            rows=[r for r in pool if r['category']==cat]
            self.assertEqual(Counter(r['old_value'].casefold() for r in rows),Counter(r['new_value'].casefold() for r in rows))

    def test_pending_audit_cannot_enable_unsampled_pool(self):
        args=deepcopy(self.args);args[-1][0]['review_decision']=''
        with self.assertRaises(ValueError):build_pool(*args)

    def test_known_match_excludes_reverse_direction_too(self):
        args=deepcopy(self.args);args[-1][0]['review_decision']='match'
        pool,_,excluded,_=build_pool(*args)
        exchange=args[-1][0]['exchange_id']
        self.assertEqual(sum(r['exchange_id']==exchange for r in excluded),2)
        self.assertFalse(any(r['exchange_id']==exchange for r in pool))

    def test_changed_source_or_duplicate_candidate_is_rejected(self):
        args=deepcopy(self.args);args[2][0]['text']='changed'
        with self.assertRaises(ValueError):build_pool(*args)
        args=deepcopy(self.args);args[2].append(args[2][0])
        with self.assertRaises(ValueError):build_pool(*args)

    def test_paired_train_is_balanced_and_has_no_validation_or_test(self):
        pool,*_=build_pool(*self.args);rows=paired_rows(pool,self.items)
        self.assertEqual(len(rows),532)
        self.assertEqual(Counter(r['label'] for r in rows),Counter({'0':266,'1':266}))
        self.assertEqual({r['split'] for r in rows},{'train'})
        self.assertEqual(len({r['anchor_item_id'] for r in rows}),266)
        self.assertTrue(all(r['label_status']=='original_listing_unverified' for r in rows if r['label']=='1'))


if __name__=='__main__':unittest.main()
