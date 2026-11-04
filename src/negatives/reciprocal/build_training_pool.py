"""Build a reviewed N3 subset and an explicitly partially reviewed train pool.

Never treats an unsampled candidate as human-approved. Excludes an entire
reciprocal exchange if either direction has a known match/uncertain judgment.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path

from build_balanced_n3 import FIELDS,digest,read,write
from summarize_review import summarize

POOL_FIELDS=['pair_id','item_id','image_path','text','label','neg_type','category','year','split',
    'anchor_item_id','image_item_id','text_item_id','anchor_group_id','text_group_id','dataset_version',
    'label_status','review_status','review_decision','reason','notes','exchange_id',
    'source_pair_id','source_dataset_id','source_neg_type','donor_item_id','original_text','old_value','new_value']
VERSION='n3-train-supplement-v2'


def build_pool(previous_sample,previous_reviews,candidates,sample,reviews):
    _,old_retained=summarize(previous_sample,previous_reviews)
    report,reviewed_retained=summarize(sample,reviews)
    if any(not r['review_decision'] for r in reviews):
        raise ValueError('Complete the audit sample before enabling unsampled training candidates')
    ix={r['pair_id']:r for r in candidates}
    if len(ix)!=len(candidates):raise ValueError('Duplicate candidate IDs')
    for r in candidates:
        if any(k not in r for k in FIELDS) or digest({k:v for k,v in r.items() if k not in {'dataset_id','pair_sha256'}})!=r['pair_sha256']:
            raise ValueError('Candidate content fingerprint mismatch: '+r['pair_id'])
    if {r['anchor_item_id'] for r in previous_reviews}&{r['anchor_item_id'] for r in candidates}:
        raise ValueError('Expanded pool reuses previously reviewed anchors')
    if any(r['review_decision'] or r['reason'] or r['notes'] for r in candidates):
        raise ValueError('Expected immutable blank candidate table')
    for r in sample:
        if r['pair_id'] not in ix or any(r[k]!=ix[r['pair_id']][k] for k in FIELDS):
            raise ValueError('Sample differs from exact candidate table')
    judged={r['pair_id']:r for r in reviews};groups=defaultdict(list)
    for r in candidates:groups[r['exchange_id']].append(r)
    expanded=[];excluded=[]
    for exchange,rows in groups.items():
        if len(rows)!=2:raise ValueError('Incomplete exchange: '+exchange)
        if any(judged.get(r['pair_id'],{}).get('review_decision') in {'match','uncertain'} for r in rows):
            excluded.extend(judged.get(r['pair_id'],r) for r in rows)
        else:
            expanded.extend(judged.get(r['pair_id'],r) for r in rows)
    pool=[*old_retained,*expanded]
    if any(r['split']!='train' for r in pool):raise ValueError('Training pool must contain train only')
    if len({r['anchor_item_id'] for r in pool})!=len(pool):raise ValueError('Repeated training anchor')
    normalized=[]
    for r in pool:
        decision=r['review_decision']
        reviewed=decision=='mismatch'
        if decision not in {'','mismatch'}:raise ValueError('Known bad/uncertain row retained')
        normalized.append(dict(pair_id=r['anchor_item_id']+'_N3',item_id=r['anchor_item_id'],
            image_path=r['image_path'],text=r['text'],label='0',neg_type='N3',category=r['category'],year='',split='train',
            anchor_item_id=r['anchor_item_id'],image_item_id=r['image_item_id'],text_item_id=r['text_item_id'],
            anchor_group_id=r['anchor_group_id'],text_group_id=r['text_group_id'],dataset_version=VERSION,
            label_status='reviewer_accepted' if reviewed else 'generated_unreviewed',
            review_status='reviewed_mismatch' if reviewed else 'unreviewed',review_decision=decision,
            reason=r['reason'],notes=r['notes'],exchange_id=r['exchange_id'],source_pair_id=r['pair_id'],
            source_dataset_id=r['dataset_id'],source_neg_type=r['neg_type'],donor_item_id=r['donor_item_id'],
            original_text=r['original_text'],old_value=r['old_value'],new_value=r['new_value']))
    normalized.sort(key=lambda r:r['pair_id'])
    for category in {r['category'] for r in normalized}:
        rr=[r for r in normalized if r['category']==category]
        assert Counter(r['old_value'].casefold() for r in rr)==Counter(r['new_value'].casefold() for r in rr)
    reviewed=[r for r in normalized if r['review_status']=='reviewed_mismatch']
    assert len(reviewed)==len(old_retained)+len(reviewed_retained)
    summary=dict(version=VERSION,split='train',expanded_audit=report,
        previous_reviewed=len(old_retained),expanded_reviewed=len(reviewed_retained),
        reviewed_total=len(reviewed),training_negatives=len(normalized),
        training_status_counts=dict(Counter(r['review_status'] for r in normalized)),
        excluded_expanded_rows=len(excluded),
        note='Unsampled candidates are allowed as generated training data after sample quality control; they are NOT human-approved. Known match/uncertain exchanges are excluded. No val/test pool.')
    return normalized,reviewed,excluded,summary


def paired_rows(negatives,items):
    ix={r['item_id']:r for r in items};result=[]
    for negative in negatives:
        a=ix[negative['anchor_item_id']]
        if a['split']!='train' or a['image_path']!=negative['image_path']:
            raise ValueError('Source image/split mismatch')
        positive=dict(negative,pair_id=a['item_id']+'_pos',text=a['title'],label='1',neg_type='pos',
            label_status='original_listing_unverified',review_status='not_reviewed_as_positive',review_decision='',
            reason='',notes='',source_pair_id=a['item_id']+'_pos',source_neg_type='pos',donor_item_id='',
            source_dataset_id='abo-home-v2-20261103',
            old_value='',new_value='')
        result.extend([positive,negative])
    assert len({r['pair_id'] for r in result})==len(result)
    assert len({(r['image_path'],r['text']) for r in result})==len(result)
    return result


def main():
    root=Path(__file__).resolve().parents[3]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--previous-dir',type=Path,default=root/'data/reviews/n3-reciprocal-dev-v1')
    ap.add_argument('--expanded-dir',type=Path,default=root/'data/reviews/n3-reciprocal-expanded-dev-v2')
    ap.add_argument('--items-csv',type=Path,default=root/'data/releases/abo-home-v2-20261103/items.csv')
    ap.add_argument('--out',type=Path,default=root/'data/reviews/n3-reciprocal-expanded-dev-v2')
    args=ap.parse_args();old=args.previous_dir;new=args.expanded_dir
    sources=[old/'review_sample.csv',old/'review_completed.csv',new/'n3_candidates.csv',new/'review_sample.csv',new/'review_completed.csv']
    pool,reviewed,excluded,summary=build_pool(*(read(p) for p in sources))
    write(args.out/'training_negatives.csv',pool,POOL_FIELDS)
    write(args.out/'reviewed_negatives.csv',reviewed,POOL_FIELDS)
    write(args.out/'excluded_known_exchange.csv',excluded,FIELDS)
    paired=paired_rows(pool,read(args.items_csv))
    write(args.out/'paired_train.csv',paired,POOL_FIELDS)
    summary['paired_train_rows']=len(paired)
    summary['source_sha256']={str(p.relative_to(root)) if p.is_relative_to(root) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,args.items_csv]}
    (args.out/'training_manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
