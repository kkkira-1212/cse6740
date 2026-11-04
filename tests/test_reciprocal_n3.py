"""Protect reviewed input identity, reciprocal retention and split isolation."""
from copy import deepcopy
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/negatives/reciprocal'))
import build_balanced_n3 as n3r
from summarize_review import summarize


class ReciprocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=ROOT/'data/reviews/n3-reciprocal-dev-v1'
        cls.items=n3r.read(ROOT/'data/releases/abo-home-v2-20261103/items.csv')
        cls.ledger=n3r.read(ROOT/'data/releases/abo-home-v2-20261103/n3_audit.csv')
        cls.sample=n3r.read(cls.directory/'review_sample.csv')
        cls.completed=n3r.read(cls.directory/'review_completed.csv')

    def test_reproduction_is_order_independent_and_does_not_generate_test(self):
        first,_=n3r.generate(self.items,self.ledger)
        other,_=n3r.generate(self.items[::-1],self.ledger[::-1])
        self.assertEqual(first,other)
        self.assertEqual(first,n3r.read(self.directory/'n3_candidates.csv'))
        self.assertEqual({r['split'] for r in first},{'train','val'})

    def test_stale_color_eligibility_is_rejected(self):
        ledger=deepcopy(self.ledger)
        row=next(r for r in ledger if r['split']=='train')
        row['original_text']='Changed source title'
        with self.assertRaises(ValueError):n3r.generate(self.items,ledger)

    def test_committed_retained_rows_preserve_balanced_color_counts(self):
        report,retained=summarize(self.sample,self.completed)
        self.assertEqual(report['counts'],dict(mismatch=68,match=2,uncertain=10))
        self.assertEqual(report['retained_complete_exchanges'],30)
        self.assertEqual(retained,n3r.read(self.directory/'retained_complete_exchanges.csv'))
        n3r.validate(retained,self.items)
        for category in {r['category'] for r in retained}:
            rs=[r for r in retained if r['category']==category]
            self.assertEqual(Counter(r['old_value'].casefold() for r in rs),Counter(r['new_value'].casefold() for r in rs))

    def test_one_accepted_direction_never_promotes_its_partner(self):
        rows=deepcopy(self.sample);rows[0]['review_decision']='mismatch'
        self.assertEqual(summarize(self.sample,rows)[1],[])
        rows[1]['review_decision']='mismatch'
        self.assertEqual(len(summarize(self.sample,rows)[1]),2)

    def test_review_cannot_change_input_or_omit_rows(self):
        for field in ['text','dataset_id','donor_item_id','image_path']:
            with self.subTest(field=field):
                rows=deepcopy(self.completed);rows[0][field]='altered'
                with self.assertRaises(ValueError):summarize(self.sample,rows)
        with self.assertRaises(ValueError):summarize(self.sample,self.completed[:-1])
        with self.assertRaises(ValueError):summarize(self.sample,self.completed+[self.completed[0]])


if __name__=='__main__':unittest.main()
