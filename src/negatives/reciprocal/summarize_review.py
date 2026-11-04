"""Validate the whole exported batch; retain only fully accepted exchanges."""
import argparse
import json
from pathlib import Path
from collections import Counter,defaultdict
from build_balanced_n3 import read,write,FIELDS,MUTABLE

def summarize(source,incoming):
    a={r['pair_id']:r for r in source};b={r['pair_id']:r for r in incoming}
    if len(a)!=len(source) or len(b)!=len(incoming) or a.keys()!=b.keys():
        raise ValueError('Missing, extra or duplicate pair IDs; keep all pending rows in export.')
    for pid,original in a.items():
        for field in FIELDS:
            if field not in b[pid] or (field not in MUTABLE and b[pid][field]!=original[field]):
                raise ValueError('Source field changed: '+pid+'/'+field)
        if b[pid]['review_decision'] not in {'','match','mismatch','uncertain'}:
            raise ValueError('Invalid decision: '+pid)
    groups=defaultdict(list)
    for r in incoming:groups[r['exchange_id']].append(r)
    if any(len(g)!=2 for g in groups.values()):raise ValueError('Incomplete reciprocal exchange')
    retained=[r for g in groups.values() if all(r['review_decision']=='mismatch' for r in g) for r in g]
    def counts(rs):return dict(Counter(r['review_decision'] or 'pending' for r in rs))
    report=dict(rows=len(incoming),counts=counts(incoming),
        by_category={c:counts([r for r in incoming if r['category']==c]) for c in sorted({r['category'] for r in incoming})},
        retained_complete_exchanges=len(retained)//2,retained_candidates=len(retained),
        note='Retain both directions only when each independently receives mismatch. Never approve pending/uncertain rows. Reviewer judgments are not independent adjudication.')
    return report,retained

def main():
    p=argparse.ArgumentParser();p.add_argument('review_csv',type=Path);p.add_argument('--sample-csv',type=Path,default=Path(__file__).resolve().parents[3]/'data/reviews/n3-reciprocal-dev-v1/review_sample.csv');p.add_argument('--out',type=Path,default=Path('review_results'));a=p.parse_args()
    report,retained=summarize(read(a.sample_csv),read(a.review_csv))
    a.out.mkdir(parents=True,exist_ok=True)
    write(a.out/'retained_complete_exchanges.csv',retained,FIELDS)
    (a.out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
