"""Reciprocal N3 development candidates; no test generation by default.

Uses the published v2 raw-color-checked eligibility ledger, not new loose
metadata parsing. Does not change upstream pairs or their negative allocation.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

SEED = 20261104
VERSION = 'n3-reciprocal-expanded-dev-v2'
MIN_CONTEXT_SIMILARITY = None
ALIASES = {
    'black':['black'], 'white':['white','ivory','cream','off white','off-white'],
    'gray':['gray','grey','light gray','light grey','dark gray','dark grey'],
    'blue':['blue','navy','navy blue','light blue','dark blue'],
    'red':['red','burgundy','wine red'], 'green':['green','dark green','light green'],
    'yellow':['yellow'], 'pink':['pink','light pink'], 'purple':['purple'],
    'orange':['orange'], 'brown':['brown','dark brown','light brown','chocolate brown'],
    'beige':['beige','tan'], 'silver':['silver'], 'gold':['gold','golden'],
}
FAMILY = {a:f for f,aa in ALIASES.items() for a in aa}
COLOR = re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(x) for x in sorted(FAMILY,key=lambda x:(-len(x),x)))+r')(?!\w)',re.I)
# The old ledger may identify only "Gray" inside an unparsed "Ash Gray".
# Do not transplant just the suffix of a commercial shade expression.
SHADE_PREFIX = re.compile(r'\b(ash|slate|storm|charcoal|heather|antique|brushed|dusty|midnight|dove|espresso|cognac|taupe|washed|distressed|faded|pearl|smoky|smoke|steel|slate|stone|sand|ocean|royal|sky|aqua|teal|sage|olive|mint|forest|emerald|rust|burnt|rose)\s*$',re.I)
# Symmetric conservative exclusions, fixed before any validation diagnostic.
NEAR = [
    {'black','gray','blue','brown'}, {'white','beige','yellow','gold','pink'},
    {'brown','beige','orange','gold','red'}, {'red','pink','purple','orange'},
    {'blue','green','purple'}, {'green','yellow'}, {'gray','silver'},
    {'gold','silver'}, {'gray','white','beige','silver'}, {'gray','green'}, {'white','silver'},
]
FIELDS = ['dataset_id','pair_sha256','pair_id','neg_type','split','category',
          'anchor_item_id','image_item_id','text_item_id','image_path',
          'anchor_group_id','text_group_id','original_text','text','attribute',
          'old_value','new_value','source_family','target_family','exchange_id',
          'donor_item_id','donor_original_text','donor_image_path','context_similarity',
          'raw_color_checked','label_status','review_decision','reason','notes']
MUTABLE = {'review_decision','reason','notes'}

def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def write(path,rows,fields):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def key(value):return digest([SEED,value])

def contrast(a,b):
    return a!=b and not any(a in s and b in s for s in NEAR)

def brand(title):
    t=title.lower()
    for b in ['stone & beam','rivet','strathwood','amazon basics','amazonbasics','ravenna home']:
        if b in t:return b
    return 'other'

def material(title):
    t=title.lower()
    return tuple(x for x in ['leather','fabric','velvet','wicker','wood','metal','wool','sisal','jute','cotton'] if re.search(r'\b'+x+r'\b',t))

def eligible(items,ledger,splits):
    proof={r['item_id']:r for r in ledger}
    result=[];skipped=Counter()
    for it in sorted(items,key=lambda r:r['item_id']):
        if it['split'] not in splits:continue
        p=proof.get(it['item_id'])
        if not p or p.get('raw_color_checked')!='True':skipped['not_in_raw_checked_ledger']+=1;continue
        mm=list(COLOR.finditer(it['title']))
        if p['original_text']!=it['title'] or len(mm)!=1:raise ValueError('stale eligibility ledger')
        m=mm[0]
        if p['old_value']!=m.group():raise ValueError('color span differs from source ledger')
        if SHADE_PREFIX.search(it['title'][:m.start()]):
            skipped['unparsed_color_modifier']+=1;continue
        result.append(dict(it,span=(m.start(),m.end()),phrase=m.group(),family=FAMILY[m.group().lower()],
                           context=(it['title'][:m.start()]+' COLOR '+it['title'][m.end():]),
                           style=len(m.group().replace('-',' ').split())))
    return result,skipped

def match_groups(pool):
    groups=defaultdict(list)
    for r in pool:groups[(r['split'],r['product_type'])].append(r)
    chosen=[];unmatched=[]
    for _,rows in sorted(groups.items()):
        rows=sorted(rows,key=lambda r:r['item_id'])
        if len(rows)<2:unmatched.extend(rows);continue
        v=TfidfVectorizer(ngram_range=(1,2),token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z-]+\b')
        x=v.fit_transform([r['context'] for r in rows]);sim=(x@x.T).toarray()
        edges=[]
        for i,a in enumerate(rows):
            for j in range(i+1,len(rows)):
                b=rows[j]
                if (a['group_id']!=b['group_id'] and a['image_path']!=b['image_path']
                    and contrast(a['family'],b['family'])):
                    edges.append((-float(sim[i,j]),key([a['item_id'],b['item_id']]),i,j))
        used=set()
        for negsim,_,i,j in sorted(edges):
            if i in used or j in used:continue
            used.update([i,j]);chosen.append((rows[i],rows[j],-negsim))
        unmatched.extend(r for i,r in enumerate(rows) if i not in used)
    return chosen,unmatched

def replace(a,b):
    old=a['phrase'];new=b['phrase']
    if old.isupper():new=new.upper()
    elif old.islower():new=new.lower()
    elif old.istitle():new=new.title()
    s,e=a['span']
    return a['title'][:s]+new+a['title'][e:],new

def generate(items,ledger,previous_review,splits=('train',)):
    pool,skips=eligible(items,ledger,splits)
    reviewed=previous_review
    seen={r['anchor_item_id'] for r in reviewed}
    skips['previously_reviewed_anchors_excluded']=sum(r['item_id'] in seen for r in pool)
    pool=[r for r in pool if r['item_id'] not in seen]
    exchanges,unmatched=match_groups(pool);rows=[]
    positives={(r['image_path'],r['title'].strip().casefold()) for r in items}
    for a,b,similarity in exchanges:
        changed=[replace(a,b),replace(b,a)]
        if any((r['image_path'],t.strip().casefold()) in positives for r,(t,_) in zip([a,b],changed)):
            skips['reciprocal_pair_positive_collision']+=2;continue
        exchange='swap_'+digest(sorted([a['item_id'],b['item_id']]))[:16]
        for anchor,donor,(text,new) in zip([a,b],[b,a],changed):
            row=dict(pair_id=anchor['item_id']+'_N3R2',neg_type='N3R2',split=anchor['split'],
                category=anchor['product_type'],anchor_item_id=anchor['item_id'],image_item_id=anchor['item_id'],
                text_item_id=anchor['item_id'],image_path=anchor['image_path'],anchor_group_id=anchor['group_id'],
                text_group_id=anchor['group_id'],original_text=anchor['title'],text=text,attribute='color',
                old_value=anchor['phrase'],new_value=new,source_family=anchor['family'],target_family=donor['family'],
                exchange_id=exchange,donor_item_id=donor['item_id'],donor_original_text=donor['title'],
                donor_image_path=donor['image_path'],context_similarity=f'{similarity:.6f}',raw_color_checked='True',
                label_status='unreviewed_candidate',review_decision='',reason='',notes='')
            row['pair_sha256']=digest(row);rows.append(row)
    rows.sort(key=lambda r:(r['split'],r['exchange_id'],r['pair_id']))
    batch=digest(dict(version=VERSION,seed=SEED,rows=rows))[:20]
    for r in rows:r['dataset_id']=batch
    validate(rows,items)
    return rows,dict(eligible=len(pool),unmatched=len(unmatched),skips=dict(skips))

def validate(rows,items):
    ix={r['item_id']:r for r in items};by=defaultdict(list)
    assert len({r['pair_id'] for r in rows})==len(rows)
    assert len({r['anchor_item_id'] for r in rows})==len(rows)
    for r in rows:
        a=ix[r['anchor_item_id']];b=ix[r['donor_item_id']]
        assert a['split']==b['split']==r['split']
        assert a['product_type']==b['product_type']==r['category']
        assert a['group_id']!=b['group_id'] and a['image_path']!=b['image_path']
        assert contrast(r['source_family'],r['target_family'])
        m=list(COLOR.finditer(a['title']))[0]
        assert r['text']==a['title'][:m.start()]+r['new_value']+a['title'][m.end():]
        assert r['new_value'].lower() in b['title'].lower()
        by[r['exchange_id']].append(r)
    for group in by.values():
        assert len(group)==2
        a,b=group
        assert a['anchor_item_id']==b['donor_item_id'] and b['anchor_item_id']==a['donor_item_id']
    for s in {r['split'] for r in rows}:
        for cat in {r['category'] for r in rows if r['split']==s}:
            rr=[r for r in rows if r['split']==s and r['category']==cat]
            assert Counter(r['old_value'].casefold() for r in rr)==Counter(r['new_value'].casefold() for r in rr)

def review_sample(rows,n=100):
    if n%2:raise ValueError('Review size must be even to keep exchanges intact')
    groups=defaultdict(list)
    for r in rows:
        if r['split']=='train':groups[r['exchange_id']].append(r)
    by_cat=defaultdict(list)
    for eid,rs in groups.items():by_cat[rs[0]['category']].append(eid)
    target=min(n//2,len(groups));total=len(groups)
    if not total:raise ValueError('No train reciprocal pairs')
    quotas={c:target*len(ids)/total for c,ids in by_cat.items()};alloc={c:int(q) for c,q in quotas.items()}
    for c in sorted(quotas,key=lambda c:(-(quotas[c]-alloc[c]),c))[:target-sum(alloc.values())]:alloc[c]+=1
    selected=[]
    for c in sorted(by_cat):
        for eid in sorted(by_cat[c],key=key)[:alloc[c]]:selected.extend(groups[eid])
    # Adjacent directions make reciprocal logic inspectable; decisions remain independent.
    return selected

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[3]/'data/releases/abo-home-v2-20261103')
    ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[3]/'data/reviews/n3-reciprocal-expanded-dev-v2')
    ap.add_argument('--previous-review',type=Path,default=Path(__file__).resolve().parents[3]/'data/reviews/n3-reciprocal-dev-v1/review_completed.csv');args=ap.parse_args()
    items=read(args.source/'items.csv');ledger=read(args.source/'n3_audit.csv')
    rows,stats=generate(items,ledger,read(args.previous_review));sample=review_sample(rows)
    existing=args.out/'review_sample.csv'
    if existing.exists() and read(existing)!=[{k:str(r.get(k,'')) for k in FIELDS} for r in sample]:
        raise ValueError('Existing review batch differs; use a new --out directory.')
    write(args.out/'n3_candidates.csv',rows,FIELDS);write(args.out/'review_sample.csv',sample,FIELDS)
    controls=[]
    for r in rows:
        for label,text in [(1,r['original_text']),(0,r['text'])]:
            controls.append(dict(pair_id=r['anchor_item_id']+('_pos' if label else '_N3R2'),anchor_item_id=r['anchor_item_id'],
                image_path=r['image_path'],text=text,label=label,neg_type='pos' if label else 'N3R2',split=r['split'],category=r['category']))
    write(args.out/'n3_with_positives.csv',controls,list(controls[0]))
    summary=dict(version=VERSION,status='UNREVIEWED_DEVELOPMENT_CANDIDATES',source_commit='32b552c0aa20bdf026403b8ebf29e277c3ca68c6',
        seed=SEED,min_context_similarity=None,matching_policy='Same split/category; context similarity ranks partners only; no brand/material/word-count gate',**stats,candidates=len(rows),review_rows=len(sample),
        by_split=dict(Counter(r['split'] for r in rows)),train_review_by_category=dict(Counter(r['category'] for r in sample)),
        color_counts=dict(source=dict(Counter(r['old_value'].casefold() for r in rows)),target=dict(Counter(r['new_value'].casefold() for r in rows))),
        note='Train only. Exclude all prior 80 reviewed anchors; previous 60 accepted rows are preserved separately, not re-approved or replaced. Expanded candidates require a new quality audit. No validation/test generation or tuning.',
        input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.source/'items.csv',args.source/'n3_audit.csv',args.previous_review]})
    (args.out/'manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
