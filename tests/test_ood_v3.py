import copy
import csv
from collections import Counter,defaultdict
from pathlib import Path
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/negatives'))
from build_ood_v3 import global_groups,validate,TIERS
from finalize_ood_v3 import screen


def read(p):
    with p.open(encoding='utf-8') as f:return list(csv.DictReader(f))


class OODV3Tests(unittest.TestCase):
    def setUp(self):
        self.data=ROOT/'data/releases/abo-ood-v3-20261115-candidate'
        self.items=read(self.data/'items.csv');self.pairs=read(self.data/'pairs.csv')
        self.id_items=read(ROOT/'data/releases/abo-home-v2-20261103/items.csv')

    def test_complete_fixed_image_layout_and_isolation(self):
        validate(self.items,self.pairs,self.id_items)
        self.assertEqual(len(self.items),300);self.assertEqual(len(self.pairs),600)
        self.assertEqual(Counter(r['split'] for r in self.items),{'ood_near':150,'ood_far':150})

    def test_cross_tier_donor_is_rejected(self):
        bad=copy.deepcopy(self.pairs)
        r=next(r for r in bad if r['neg_type']=='N1')
        donor=next(i for i in self.items if i['split']!=r['split'])
        r.update(text_item_id=donor['item_id'],text_group_id=donor['group_id'],text=donor['title'])
        with self.assertRaises(AssertionError):validate(self.items,bad,self.id_items)

    def test_global_equivalence_connects_indirect_image_and_title(self):
        def row(i,image,title):return dict(item_id=i,main_image_id=image,title=title,normalization_terms=[],product_type='LAMP')
        rows=[row('a','1','One distinctive lamp'),row('b','1','Other distinctive lamp'),row('c','2','Other distinctive lamp')]
        gids,_=global_groups(rows)
        self.assertEqual(len(set(gids.values())),1)

    def test_screening_is_exact_reproducible_and_keeps_whole_exchanges(self):
        n3=read(self.data/'n3_provenance.csv');sample=read(self.data/'review_sample.csv')
        reviews=read(ROOT/'data/reviews/ood-v3-model-assisted/decisions.csv')
        rows,excluded,retained=screen(self.pairs,n3,sample,reviews)
        self.assertEqual(rows,read(self.data/'eval_pairs.csv'))
        self.assertEqual(len(excluded),16)
        by=defaultdict(list)
        for r in retained:by[r['exchange_id']].append(r)
        self.assertTrue(all(len(rs)==2 for rs in by.values()))
        self.assertEqual(len(rows),568)
        anchors=Counter(r['anchor_item_id'] for r in rows)
        self.assertTrue(all(n==2 for n in anchors.values()))
        with self.assertRaises(ValueError):screen(self.pairs,n3,sample,reviews[:-1])
        changed=copy.deepcopy(reviews);changed[0]['text']='changed'
        with self.assertRaises(ValueError):screen(self.pairs,n3,sample,changed)


if __name__=='__main__':unittest.main()
