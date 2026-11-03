"""Subset sampling must retain v2 anchor pairs, not group by donor titles."""
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/baselines'))
from common import source_query_key

class SubsetTests(unittest.TestCase):
    def test_explicit_v2_group_takes_precedence_over_title_donor(self):
        positive=dict(pair_id='A_pos',neg_type='pos',split='test',anchor_item_id='A',anchor_group_id='gA',text_item_id='A')
        negative=dict(positive,pair_id='A_N2',neg_type='N2',text_item_id='B')
        self.assertEqual(source_query_key(positive),source_query_key(negative))
        self.assertNotEqual(source_query_key(positive),source_query_key(dict(positive,split='val')))

    def test_cli_keeps_positive_and_negative_together(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'pairs.csv';output=Path(directory)/'subset.csv'
            rows=[]
            for anchor in ['A','B','C','D']:
                for kind in ['pos','N2']:
                    rows.append(dict(pair_id=anchor+'_'+kind,neg_type=kind,split='test',category='CHAIR',
                        anchor_item_id=anchor,anchor_group_id='g'+anchor,text_item_id=anchor if kind=='pos' else 'same-donor'))
            with source.open('w',newline='') as f:
                w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
            script=Path(__file__).resolve().parents[1]/'src/baselines/sample_subset.py'
            subprocess.run([sys.executable,str(script),'--pairs-csv',str(source),'--out-csv',str(output),'--target-pairs','4'],check=True,capture_output=True)
            with output.open(newline='') as f:chosen=list(csv.DictReader(f))
            self.assertEqual(len(chosen),4)
            for group in {r['anchor_group_id'] for r in chosen}:
                self.assertEqual({r['neg_type'] for r in chosen if r['anchor_group_id']==group},{'pos','N2'})

if __name__=='__main__':unittest.main()
