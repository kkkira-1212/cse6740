"""Release-level safeguards for splits, grouping, pair direction and allocation."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/data'))
from build_home_release import group_records, split_and_filter, assign_negatives, validate


def config():
    return dict(version='test',seed=42,furniture_types=['CHAIR','SOFA'],decor_types=[],
                mixed_types_require_node=[],allowed_node_segments=['furniture'],held_out_types=['LAMP'],
                max_shared_image_records=4,min_total_groups=6,min_groups_by_split=dict(train=2,val=2,test=2),
                split_ratios=[.5,.25,.25],title_group_soft_limit=3)


def row(i,pt='CHAIR',split='train'):
    return dict(item_id=i,title='Black '+pt+' product '+i,main_image_id=i,image_path='small/'+i+'.jpg',
                product_type=pt,node='',nodes=[],color='Black',material='',normalization_terms=['Black'],
                group_id='g_'+i,split=split)


class ReleaseTests(unittest.TestCase):
    def test_shared_image_group_cannot_leak_from_heldout_lighting(self):
        a,b=row('A'),row('B','LAMP')
        b['main_image_id']=a['main_image_id'];b['image_path']=a['image_path']
        chosen,excluded,groups=group_records([a,b],config())
        self.assertEqual(chosen,[])
        self.assertIn('connected_to_heldout_group',{r['reason'] for r in excluded})

    def test_one_representative_and_group_ids_are_order_independent(self):
        a,b,c=row('A'),row('B'),row('C')
        b['main_image_id']=a['main_image_id'];b['image_path']=a['image_path']
        first,_,_=group_records([a,b,c],config())
        other,_,_=group_records([c,b,a],config())
        self.assertEqual([(r['item_id'],r['group_id']) for r in first],[(r['item_id'],r['group_id']) for r in other])
        self.assertEqual(len(first),2)

    def test_small_types_are_reported_and_excluded(self):
        rows=[row(str(i)) for i in range(8)]+[row('s','SOFA')]
        chosen,report=split_and_filter(rows,config())
        self.assertEqual(len(chosen),8)
        self.assertFalse(next(r for r in report if r['product_type']=='SOFA')['retained'])
        self.assertEqual({s:sum(r['split']==s for r in chosen) for s in ['train','val','test']},dict(train=4,val=2,test=2))

    def data(self):
        items=[row(pt+'_'+s+'_'+str(i),pt,s) for pt in ['CHAIR','SOFA'] for s in ['train','val','test'] for i in range(8)]
        raw={r['item_id']:[dict(language_tag='en_US',value='Black',standardized_values=['Black'])] for r in items}
        return items,raw

    def test_balanced_fixed_image_pairs_and_candidate_n3_cap(self):
        items,raw=self.data();pairs,alloc,reuse,relax,*_=assign_negatives(items,raw,config())
        checks=validate(items,pairs,config())
        self.assertEqual(checks['pairs'],2*len(items))
        for r in alloc:
            self.assertEqual(r['anchors'],r['N1']+r['N2']+r['N3'])
            self.assertLessEqual(r['N3'],min(r['N1'],r['N2']))
        again=assign_negatives(items[::-1],raw,config())[0]
        self.assertEqual(pairs,again)

    def test_validation_rejects_changed_image_or_split(self):
        items,raw=self.data();pairs=assign_negatives(items,raw,config())[0]
        changed=deepcopy(pairs);changed[0]['image_path']='small/wrong.jpg'
        with self.assertRaises(AssertionError):validate(items,changed,config())
        changed=deepcopy(pairs);changed[0]['split']='outside'
        with self.assertRaises(AssertionError):validate(items,changed,config())

    def test_soft_limit_relaxations_are_explicit(self):
        items,raw=self.data();c=config();c['title_group_soft_limit']=0
        pairs,alloc,reuse,relax,*_=assign_negatives(items,raw,c)
        self.assertTrue(relax)
        self.assertEqual(len(relax),sum(r['neg_type'] in ['N1','N2'] for r in pairs))


if __name__=='__main__':unittest.main()
