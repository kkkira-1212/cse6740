"""Apply explicit semantic-QC exclusions; never resample candidate rows."""
import argparse
from collections import Counter,defaultdict
import hashlib,json
from pathlib import Path
from build_ood_v3 import read,write,PAIR_FIELDS,FIELDS,VERSION


def screen(pairs,n3,sample,decisions):
    expected={r['pair_id']:r for r in sample};judged={r['pair_id']:r for r in decisions}
    if len(judged)!=len(decisions) or set(judged)!=set(expected):raise ValueError('Incomplete/duplicate review')
    for pid,r in judged.items():
        if r['decision'] not in ('mismatch','match','uncertain'):raise ValueError('Invalid decision')
        for k in ('text','split','image_path','neg_type'):
            if r[k]!=expected[pid][k]:raise ValueError('Changed reviewed input')
    neg={r['pair_id']:r for r in pairs if r['label']=='0'}
    blocked={neg[pid]['anchor_item_id']:'review_'+r['decision'] for pid,r in judged.items()
             if r['decision']!='mismatch' or r['original_color_check']=='uncertain'}
    exchanges=defaultdict(list)
    for r in n3:exchanges[r['exchange_id']].append(r)
    for eid,rs in exchanges.items():
        if any(r['anchor_item_id'] in blocked for r in rs):
            for r in rs:blocked[r['anchor_item_id']]='exchange_QC_exclusion:'+eid
    rows=[r for r in pairs if r['anchor_item_id'] not in blocked]
    excluded=[dict(anchor_item_id=a,reason=why) for a,why in sorted(blocked.items())]
    retained=[r for r in n3 if r['anchor_item_id'] not in blocked]
    return rows,excluded,retained


def main():
    root=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,default=root/'data/releases'/VERSION)
    ap.add_argument('--review',type=Path,default=root/'data/reviews/ood-v3-model-assisted/decisions.csv');a=ap.parse_args()
    pairs=read(a.data/'pairs.csv');n3=read(a.data/'n3_provenance.csv');sample=read(a.data/'review_sample.csv');decisions=read(a.review)
    rows,excluded,retained=screen(pairs,n3,sample,decisions)
    images={r['image_path']:r['sha256'] for r in read(a.data/'image_manifest.csv')}
    if any(r['image_sha256']!=images[r['image_path']] for r in decisions):raise ValueError('Review image hash differs')
    write(a.data/'eval_pairs.csv',rows,PAIR_FIELDS);write(a.data/'eval_n3_provenance.csv',retained,FIELDS)
    write(a.data/'eval_excluded_anchors.csv',excluded,['anchor_item_id','reason'])
    sha=lambda p:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    summary=dict(status='MODEL_ASSISTED_QC_CANDIDATE_NOT_FROZEN_NOT_HUMAN_CERTIFIED',review_counts=dict(Counter(r['decision'] for r in decisions)),
        reviewed_rows=len(decisions),excluded_anchors=len(excluded),counts=dict(Counter(r['split']+':'+r['neg_type'] for r in rows)),
        input_sha256={p.name:sha(p) for p in [a.data/'pairs.csv',a.data/'n3_provenance.csv',a.data/'review_sample.csv',a.data/'image_manifest.csv',a.review]},
        output_sha256={name:sha(a.data/name) for name in ['eval_pairs.csv','eval_n3_provenance.csv','eval_excluded_anchors.csv']},
        note='Whole-anchor exclusion, whole reciprocal exchange when flagged; no resampling or OOD model scores. Unreviewed rows are still generated candidates.')
    (a.data/'screening_manifest.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
