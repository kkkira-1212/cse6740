"""Build a fixed-image OOD candidate aligned with frozen ID v3; no scoring."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'data'))
sys.path.insert(0, str(HERE/'reciprocal'))
from build_home_release import load_records, title_key, ITEM_FIELDS, PAIR_FIELDS
from build_items import UnionFind
from abo_io import load_image_path_map
from build_n3 import make_candidates
from build_expanded_n3 import generate, FIELDS, read, write

VERSION = 'abo-ood-v3-20261115-candidate'
SEED = 20261115
TIERS = {'ood_near': ['LAMP', 'LIGHT_FIXTURE'], 'ood_far': ['SHOES', 'SANDAL', 'BOOT']}


def key(value):
    return hashlib.sha256(f'{SEED}:{value}'.encode()).hexdigest()


def global_groups(records, max_shared=4):
    """Same full-catalog equivalence signals as ID build_home_release."""
    uf = UnionFind(); images = {}; exact = {}; normalized = {}
    frequency = Counter(r['main_image_id'] for r in records)
    for r in sorted(records, key=lambda r:r['item_id']):
        iid=r['item_id']; uf.find(iid)
        signals=[(exact, ' '.join(r['title'].casefold().split()))]
        if frequency[r['main_image_id']] <= max_shared:
            signals.append((images, r['main_image_id']))
        title=title_key(r)
        if len(title)>=12:
            signals.append((normalized, (r['product_type'],title)))
        for lookup,value in signals:
            if value in lookup: uf.union(iid,lookup[value])
            else: lookup[value]=iid
    members=defaultdict(list)
    for r in records:members[uf.find(r['item_id'])].append(r['item_id'])
    gids={root:'home_'+hashlib.sha256(min(ids).encode()).hexdigest()[:16] for root,ids in members.items()}
    return {r['item_id']:gids[uf.find(r['item_id'])] for r in records},frequency


def select(records, id_items, n=150):
    gids,frequency=global_groups(records)
    protected={gids[r['item_id']] for r in id_items}
    if any(gids[r['item_id']]!=r['group_id'] for r in id_items):
        raise ValueError('Full-catalog group identity differs from frozen ID source')
    blocked_images={r['image_path'] for r in id_items}
    blocked_titles={' '.join(r['title'].casefold().split()) for r in id_items}
    result=[]; used=set(); stats=Counter()
    for tier,types in TIERS.items():
        pool=[]
        for r in records:
            if r['product_type'] not in types:continue
            if gids[r['item_id']] in protected or r['image_path'] in blocked_images or ' '.join(r['title'].casefold().split()) in blocked_titles:
                stats['ID_overlap']+=1;continue
            if not r['image_path'] or frequency[r['main_image_id']]>4 or 'swatch' in r['title'].casefold():
                stats['missing_shared_or_swatch']+=1;continue
            pool.append(r)
        # Round-robin types ensures cross-type N1 donors, unlike global random imbalance.
        queues={pt:sorted([r for r in pool if r['product_type']==pt],key=lambda r:key(r['item_id'])) for pt in types}
        chosen=[]
        while len(chosen)<n:
            progress=False
            for pt in types:
                while queues[pt] and gids[queues[pt][0]['item_id']] in used: queues[pt].pop(0)
                if queues[pt] and len(chosen)<n:
                    r=queues[pt].pop(0);used.add(gids[r['item_id']]);chosen.append(dict(r,group_id=gids[r['item_id']],split=tier));progress=True
            if not progress:break
        if len(chosen)!=n:raise ValueError(f'Insufficient independent {tier} items')
        result.extend(chosen)
    return result,dict(stats)


def pair_items(items,n3):
    replacements={r['anchor_item_id']:r for r in n3}
    result=[]; reuse=[]
    for tier in TIERS:
        pool=sorted([r for r in items if r['split']==tier],key=lambda r:key('order:'+r['item_id']))
        remaining=[r for r in pool if r['item_id'] not in replacements]
        n2_ids={r['item_id'] for r in sorted(remaining,key=lambda r:key('kind:'+r['item_id']))[:(len(remaining)+1)//2]}
        used=Counter()
        for a in pool:
            iid=a['item_id'];base=dict(item_id=iid,image_path=a['image_path'],category=a['product_type'],year='',split=tier,
                anchor_item_id=iid,image_item_id=iid,anchor_group_id=a['group_id'],dataset_version=VERSION)
            result.append(dict(base,pair_id=iid+'_pos',text=a['title'],label='1',neg_type='pos',text_item_id=iid,text_group_id=a['group_id'],label_status='original_listing_unverified'))
            if iid in replacements:
                donor=a;kind='N3';text=replacements[iid]['text']
            else:
                kind='N2' if iid in n2_ids else 'N1'
                legal=[d for d in pool if d['group_id']!=a['group_id'] and d['image_path']!=a['image_path']
                       and ((d['product_type']==a['product_type'])==(kind=='N2'))
                       and d['title'].strip().casefold()!=a['title'].strip().casefold()]
                if not legal:raise ValueError('No legal '+kind+' donor for '+iid)
                donor=min(legal,key=lambda d:(used[d['group_id']],key(iid+':'+d['item_id'])))
                used[donor['group_id']]+=1;text=donor['title']
            result.append(dict(base,pair_id=iid+'_'+kind,text=text,label='0',neg_type=kind,text_item_id=donor['item_id'],text_group_id=donor['group_id'],label_status='generated_unreviewed'))
        reuse.extend(dict(split=tier,text_group_id=g,uses=c) for g,c in sorted(used.items()))
    return result,reuse


def validate(items,pairs,id_items):
    assert len({r['group_id'] for r in items})==len(items)
    for field in ('item_id','image_path','group_id'):
        assert not ({r[field] for r in items}&{r[field] for r in id_items})
    assert not ({r['product_type'] for r in items}&{r['product_type'] for r in id_items})
    ix={r['item_id']:r for r in items};by=defaultdict(list)
    assert len({r['pair_id'] for r in pairs})==len(pairs)
    assert len({(r['image_path'],r['text'].strip().casefold()) for r in pairs})==len(pairs)
    for r in pairs:
        a,d=ix[r['anchor_item_id']],ix[r['text_item_id']]
        assert a['split']==d['split']==r['split']
        assert r['image_path']==a['image_path'] and r['image_item_id']==a['item_id']
        assert r['text_group_id']==d['group_id'] and r['anchor_group_id']==a['group_id']
        if r['neg_type'] in ('N1','N2'):
            assert a['group_id']!=d['group_id'] and a['image_path']!=d['image_path']
            assert (a['product_type']==d['product_type'])==(r['neg_type']=='N2')
            assert r['text']==d['title']
        by[a['item_id']].append(r)
    assert set(by)==set(ix)
    assert all(len(rs)==2 and {r['label'] for r in rs}=={'0','1'} for rs in by.values())


def main():
    root=HERE.parents[1];ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=Path,default=root/'data/raw')
    ap.add_argument('--out',type=Path,default=root/'data/releases'/VERSION)
    ap.add_argument('--download-images',action='store_true');args=ap.parse_args()
    id_path=root/'data/releases/abo-home-v2-20261103/items.csv';id_items=read(id_path)
    records,raw,total,shards=load_records(args.raw/'listings/metadata',load_image_path_map(args.raw/'images/metadata/images.csv.gz'))
    items,excluded=select(records,id_items)
    _,ledger,skipped=make_candidates(items,SEED,raw)
    ledger=[{k:str(v) for k,v in r.items()} for r in ledger]
    candidates,stats=generate(items,ledger,[],splits=tuple(TIERS))
    # Whole exchanges only; cap at one-third of negatives as in ID construction.
    selected=[]
    for tier in TIERS:
        exchanges=defaultdict(list)
        for r in candidates:
            if r['split']==tier:exchanges[r['exchange_id']].append(r)
        for eid in sorted(exchanges,key=key)[:(sum(r['split']==tier for r in items)//3)//2]:selected.extend(exchanges[eid])
    pairs,reuse=pair_items(items,selected);validate(items,pairs,id_items)
    out=args.out;write(out/'items.csv',items,ITEM_FIELDS);write(out/'pairs.csv',pairs,PAIR_FIELDS)
    write(out/'n3_candidates.csv',candidates,FIELDS);write(out/'n3_provenance.csv',selected,FIELDS)
    write(out/'title_donor_reuse.csv',reuse,['split','text_group_id','uses'])
    # A fixed train-free semantic review batch; it never changes model thresholds.
    sample=[]
    for tier in TIERS:
        for kind in ('N1','N2'):
            sample.extend(sorted([r for r in pairs if r['split']==tier and r['neg_type']==kind],key=lambda r:key('review:'+r['pair_id']))[:10])
        ids={r['anchor_item_id'] for r in selected if r['split']==tier}
        sample.extend(r for r in pairs if r['neg_type']=='N3' and r['anchor_item_id'] in ids)
    write(out/'review_sample.csv',sample,PAIR_FIELDS)
    manifest=dict(version=VERSION,status='CANDIDATE_UNREVIEWED_NOT_FROZEN',seed=SEED,categories=TIERS,
        source_records=total,grouping='Full-catalog ID-v3 equivalence rules',selection='150 per tier, round-robin product types; one representative per global group',
        excluded=excluded,n3_generation=stats,counts=dict(Counter(r['split']+':'+r['neg_type'] for r in pairs)),
        review_rows=len(sample),max_title_donor_uses=max(r['uses'] for r in reuse),
        source_sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*shards,args.raw/'images/metadata/images.csv.gz']},
        id_items_sha256_lf=hashlib.sha256(id_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        id_release='abo-home-v3-20261115',
        id_pairs_sha256_lf=hashlib.sha256((root/'data/releases/abo-home-reciprocal-v3-candidate/pairs.csv').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        note='No training, OOD threshold tuning or semantic certification. Old pilot review labels are not transferred to changed inputs.',
        output_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in
                       ['items.csv','pairs.csv','n3_candidates.csv','n3_provenance.csv','title_donor_reuse.csv','review_sample.csv']})
    if args.download_images:
        def download(r):
            p=out/'images'/r['image_path'];p.parent.mkdir(parents=True,exist_ok=True)
            if not p.exists():p.write_bytes(urllib.request.urlopen('https://amazon-berkeley-objects.s3.amazonaws.com/images/'+r['image_path'],timeout=45).read())
            from PIL import Image
            with Image.open(p) as im:im.verify()
            return dict(image_path=r['image_path'],sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
        with ThreadPoolExecutor(max_workers=12) as executor:image_rows=list(executor.map(download,items))
        write(out/'image_manifest.csv',image_rows,['image_path','sha256','bytes'])
        manifest['output_sha256']['image_manifest.csv']=hashlib.sha256((out/'image_manifest.csv').read_bytes()).hexdigest()
    elif (out/'image_manifest.csv').exists():
        manifest['output_sha256']['image_manifest.csv']=hashlib.sha256((out/'image_manifest.csv').read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':main()
