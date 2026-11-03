"""Build an isolated fixed-image ABO furniture/decor candidate release.

Reads every official metadata shard. Does not alter pilot inputs or user PRs.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'negatives'))
from abo_io import iter_listings, en_us_value, en_us_standardized, load_image_path_map
from build_items import UnionFind
from build_n3 import make_candidates
from build_n2_audit import FIELDS as REVIEW_FIELDS, digest, render, summarize_review
from sean_common import read_csv, write_csv, write_json, stable_key

ITEM_FIELDS = ['item_id','title','image_path','product_type','node','color','material','group_id','split','main_image_id']
PAIR_FIELDS = ['pair_id','item_id','image_path','text','label','neg_type','category','year','split',
               'anchor_item_id','image_item_id','text_item_id','anchor_group_id','text_group_id','dataset_version','label_status']


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if not unicodedata.combining(c))


def title_key(row):
    text = row['title'].casefold()
    for attr in sorted(set(row['normalization_terms']), key=len, reverse=True):
        if attr.strip():
            text = re.sub(r'(?<!\w)' + re.escape(attr.casefold()) + r'(?!\w)', ' ', text)
    text = re.sub(r'\b(?:\d+(?:\.\d+)?\s*(?:inches|inch|in|cm|ft|feet)|twin|full|queen|king|small|medium|large)\b', ' ', text)
    text = re.sub(r'\b\d+(?:\.\d+)?\s*["\u2033]', ' ', text)
    text = re.sub(r'\b(?:set\s+of\s+\d+|\d+\s*[- ]?\s*(?:pack|piece|pc)s?)\b', ' ', text)
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def load_records(root, image_map):
    files = sorted(Path(root).glob('listings_*.json.gz'))
    if {p.name for p in files} != {f'listings_{c}.json.gz' for c in '0123456789abcdef'}:
        raise ValueError('All 16 official listing shards are required.')
    rows, raw_colors, seen = [], {}, set()
    total = 0
    for raw in iter_listings(root):
        total += 1
        title = en_us_value(raw.get('item_name'))
        mid = raw.get('main_image_id')
        iid = raw.get('item_id')
        if not title or not mid or iid in seen:
            continue
        seen.add(iid)
        pt = (raw.get('product_type') or [{}])[0].get('value', 'UNKNOWN')
        cv, cs = en_us_standardized(raw.get('color'))
        mv, ms = en_us_standardized(raw.get('material'))
        terms = [v for v in [cv, cs, mv, ms] if v]
        nodes = [n.get('node_name') or '' for n in raw.get('node', [])]
        rows.append(dict(item_id=iid, title=title.strip(), main_image_id=mid,
                         image_path='small/' + image_map[mid] if mid in image_map else '',
                         product_type=pt, node=' | '.join(nodes), nodes=nodes,
                         color=cs or cv or '', material=mv or '', normalization_terms=terms))
        raw_colors[iid] = raw.get('color', [])
    return rows, raw_colors, total, files


def scope_reason(row, config):
    pt = row['product_type']
    if pt in config['held_out_types']:
        return 'held_out_type'
    if 'swatch' in row['title'].casefold():
        return 'swatch'
    if pt in config['furniture_types'] + config['decor_types']:
        return ''
    if pt in config['mixed_types_require_node']:
        segments = {normalized(s.strip()) for path in row['nodes'] for s in path.split('/')}
        if segments.intersection(config['allowed_node_segments']):
            if re.search(r'\b(lamp|chandelier|sconce|pendant light|ceiling light)\b', row['title'], re.I):
                return 'mixed_type_lighting_held_out'
            return ''
        return 'mixed_type_without_target_node'
    return 'out_of_scope_type'


def group_records(rows, config):
    uf = UnionFind()
    frequency = Counter(r['main_image_id'] for r in rows)
    images, exact, norms = {}, {}, {}
    for r in sorted(rows, key=lambda r: r['item_id']):
        iid = r['item_id']; uf.find(iid)
        signals = [(exact, ' '.join(r['title'].casefold().split()))]
        if frequency[r['main_image_id']] <= config['max_shared_image_records']:
            signals.append((images, r['main_image_id']))
        key = title_key(r)
        if len(key) >= 12:
            signals.append((norms, (r['product_type'], key)))
        for lookup, key in signals:
            if key in lookup:
                uf.union(iid, lookup[key])
            else:
                lookup[key] = iid
    members = defaultdict(list)
    for r in rows:
        members[uf.find(r['item_id'])].append(r['item_id'])
    gid = {root: 'home_' + hashlib.sha256(min(ids).encode()).hexdigest()[:16] for root, ids in members.items()}
    heldout = {uf.find(r['item_id']) for r in rows if r['product_type'] in config['held_out_types']}
    selected, excluded, groups = [], [], defaultdict(list)
    for r in rows:
        reason = scope_reason(r, config)
        if not reason and not r['image_path']:
            reason = 'missing_image_mapping'
        if not reason and frequency[r['main_image_id']] > config['max_shared_image_records']:
            reason = 'high_frequency_shared_image'
        if not reason and uf.find(r['item_id']) in heldout:
            reason = 'connected_to_heldout_group'
        if reason:
            excluded.append(dict(item_id=r['item_id'], product_type=r['product_type'], reason=reason))
        else:
            r = dict(r, group_id=gid[uf.find(r['item_id'])])
            groups[r['group_id']].append(r)
    for key, group in sorted(groups.items()):
        representative = min(group, key=lambda r: stable_key(config['seed'], r['item_id']))
        selected.append(representative)
    return selected, excluded, groups


def split_and_filter(representatives, config):
    types = defaultdict(list)
    for r in representatives: types[r['product_type']].append(r)
    kept, report = [], []
    for pt, rows in sorted(types.items(), key=lambda v: (-len(v[1]), v[0])):
        rows = sorted(rows, key=lambda r: stable_key(config['seed'], r['group_id']))
        n = len(rows); a = int(n * config['split_ratios'][0]); b = int(n * config['split_ratios'][1])
        counts = dict(train=a, val=b, test=n-a-b)
        reasons = []
        if n < config['min_total_groups']: reasons.append('below_total_group_threshold')
        for s, minimum in config['min_groups_by_split'].items():
            if counts[s] < minimum: reasons.append('below_' + s + '_threshold')
        report.append(dict(product_type=pt, groups=n, **counts, retained=not reasons, reason=';'.join(reasons)))
        if not reasons:
            for i, r in enumerate(rows):
                kept.append(dict(r, split='train' if i < a else 'val' if i < a+b else 'test'))
    return kept, report


def assign_negatives(items, raw, config):
    n3, audit, skipped = make_candidates(items, config['seed'], raw)
    n3_map = {r['item_id']: r for r in n3}
    details = {r['item_id']: r for r in audit}
    positives = {(r['image_path'], r['title'].strip().casefold()) for r in items}
    pairs, allocations, reuse, relaxation = [], [], [], []
    for split in ['train','val','test']:
        pool = sorted([r for r in items if r['split']==split], key=lambda r: r['item_id'])
        eligible = sorted([r for r in pool if r['item_id'] in n3_map], key=lambda r: stable_key(config['seed']+1,r['item_id']))
        q = min(len(eligible),len(pool)//3)
        use_n3 = {r['item_id'] for r in eligible[:q]}
        remaining = sorted([r for r in pool if r['item_id'] not in use_n3],key=lambda r:stable_key(config['seed']+2,r['item_id']))
        # Allocate N2 proportionally within types, with exact split-wide half.
        n2_target = (len(remaining)+1)//2
        by_type = defaultdict(list)
        for r in remaining: by_type[r['product_type']].append(r)
        quotas = {pt:len(rs)*n2_target/len(remaining) for pt,rs in by_type.items()}
        alloc = {pt:int(x) for pt,x in quotas.items()}
        for pt in sorted(quotas,key=lambda p:(-(quotas[p]-alloc[p]),p))[:n2_target-sum(alloc.values())]:alloc[pt]+=1
        n2_ids = {r['item_id'] for pt,rs in by_type.items() for r in rs[:alloc[pt]]}
        used = Counter(); rng=random.Random(config['seed']+['train','val','test'].index(split))
        for anchor in sorted(pool,key=lambda r:stable_key(config['seed']+3,r['item_id'])):
            iid=anchor['item_id'];kind='N3' if iid in use_n3 else 'N2' if iid in n2_ids else 'N1'
            base=dict(item_id=iid,image_path=anchor['image_path'],category=anchor['product_type'],year='',split=split,
                      anchor_item_id=iid,image_item_id=iid,anchor_group_id=anchor['group_id'],dataset_version=config['version'])
            pairs.append(dict(base,pair_id=f'{iid}_pos',text=anchor['title'],label=1,neg_type='pos',text_item_id=iid,text_group_id=anchor['group_id'],label_status='original_listing_unverified'))
            if kind=='N3':
                donor=anchor;text=n3_map[iid]['text']
                if (anchor['image_path'],text.strip().casefold()) in positives:
                    raise ValueError('N3 positive input collision: '+iid)
            else:
                candidates=[r for r in pool if r['group_id']!=anchor['group_id'] and r['image_path']!=anchor['image_path']
                            and ((r['product_type']==anchor['product_type']) == (kind=='N2'))
                            and (anchor['image_path'],r['title'].strip().casefold()) not in positives]
                if not candidates:raise ValueError(f'No legal {kind} donor for {iid}; release not written.')
                least=min(used[r['group_id']] for r in candidates)
                donor=rng.choice([r for r in candidates if used[r['group_id']]==least])
                used[donor['group_id']]+=1;text=donor['title']
                if used[donor['group_id']]>config['title_group_soft_limit']:
                    relaxation.append(dict(split=split,pair_id=f'{iid}_{kind}',text_group_id=donor['group_id'],use_count=used[donor['group_id']]))
            pairs.append(dict(base,pair_id=f'{iid}_{kind}',text=text,label=0,neg_type=kind,text_item_id=donor['item_id'],text_group_id=donor['group_id'],label_status='unreviewed_candidate'))
        allocations.append(dict(split=split,anchors=len(pool),N3_eligible=len(eligible),N3=q,N2=n2_target,N1=len(remaining)-n2_target))
        reuse.extend(dict(split=split,text_group_id=gid,uses=n) for gid,n in sorted(used.items()))
    return pairs, allocations, reuse, relaxation, audit, skipped


def validate(items, pairs, config):
    ix={r['item_id']:r for r in items};images=defaultdict(set);groups=defaultdict(set);by_anchor=defaultdict(list)
    for r in items:images[r['image_path']].add(r['split']);groups[r['group_id']].add(r['split'])
    assert all(len(v)==1 for v in images.values())
    assert all(len(v)==1 for v in groups.values())
    assert len({r['group_id'] for r in items})==len(items)
    assert len({r['pair_id'] for r in pairs})==len(pairs)
    assert len({(r['image_path'],r['text']) for r in pairs})==len(pairs)
    for r in pairs:
        a=ix[r['anchor_item_id']];d=ix[r['text_item_id']]
        assert r['image_path']==a['image_path'] and r['item_id']==a['item_id']
        assert a['split']==d['split']==r['split']
        if r['neg_type'] in ['N1','N2']:
            assert a['group_id']!=d['group_id']
            assert (a['product_type']==d['product_type']) == (r['neg_type']=='N2')
            assert r['text']==d['title']
        by_anchor[a['item_id']].append(r)
    assert all(len(rs)==2 and sum(int(r['label']) for r in rs)==1 for rs in by_anchor.values())
    for s in ['train','val','test']:
        c=Counter(r['neg_type'] for r in pairs if r['split']==s)
        assert c['pos']==c['N1']+c['N2']+c['N3'] and abs(c['N1']-c['N2'])<=1
        assert c['N3']<=min(c['N1'],c['N2'])
    return dict(status='STRUCTURAL_CHECKS_PASSED_NOT_SEMANTIC_CERTIFICATION',items=len(items),pairs=len(pairs),
                cross_split_images=0,cross_split_groups=0,duplicate_pairs=0,positive_input_collisions=0,
                one_positive_and_one_negative_per_anchor=True)


def download_images(items, root, workers=12):
    from PIL import Image
    def one(r):
        path=Path(root)/r['image_path'];path.parent.mkdir(parents=True,exist_ok=True)
        error=None
        for attempt in range(3):
            try:
                if not path.exists():
                    with urllib.request.urlopen('https://amazon-berkeley-objects.s3.amazonaws.com/images/'+r['image_path'],timeout=35) as response:
                        data=response.read()
                    temp=path.with_suffix('.part');temp.write_bytes(data);temp.replace(path)
                with Image.open(path) as image:image.verify()
                return dict(image_path=r['image_path'],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,error='')
            except Exception as exc:
                error=str(exc)
                if path.exists():path.unlink()
        return dict(image_path=r['image_path'],sha256='',bytes=0,error=error)
    result=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(one,r) for r in items]
        for future in as_completed(futures):
            result.append(future.result())
            if len(result)%250==0:print('images verified',len(result),'/',len(items),flush=True)
    return sorted(result,key=lambda r:r['image_path'])


def create_audit(items,pairs,release,audit_dir,config):
    anchors={r['item_id']:r for r in items}
    eligible=[r for r in pairs if r['split']=='train' and r['neg_type']=='N2']
    by_type=defaultdict(list)
    for r in eligible:by_type[r['category']].append(r)
    n=config['audit_size'];total=len(eligible)
    if total<n:raise ValueError('Too few train N2 pairs for requested audit.')
    exact={pt:n*len(rs)/total for pt,rs in by_type.items()};alloc={pt:int(x) for pt,x in exact.items()}
    for pt in sorted(exact,key=lambda p:(-(exact[p]-alloc[p]),p))[:n-sum(alloc.values())]:alloc[pt]+=1
    selected=[]
    for pt,rs in sorted(by_type.items()):
        selected.extend(sorted(rs,key=lambda r:stable_key(config['seed']+4,r['pair_id']))[:alloc[pt]])
    selected.sort(key=lambda r:stable_key(config['seed']+5,r['pair_id']))
    rows=[]
    for p in selected:
        a=anchors[p['anchor_item_id']]
        row=dict(pair_id=p['pair_id'],neg_type='N2',split='train',category=p['category'],anchor_item_id=p['anchor_item_id'],
                 image_item_id=p['image_item_id'],text_item_id=p['text_item_id'],image_path=p['image_path'],anchor_group_id=p['anchor_group_id'],text_group_id=p['text_group_id'],
                 original_text=a['title'],text=p['text'],review_decision='',reason='',notes='')
        row['pair_sha256']=digest(row);rows.append(row)
    batch=digest(dict(version=config['version'],rows=rows))[:20]
    for row in rows:row['dataset_id']=batch
    write_csv(audit_dir/'review_sample.csv',rows,REVIEW_FIELDS)
    write_json(audit_dir/'manifest.json',dict(dataset_id=batch,source_release=config['version'],status='AWAITING_HUMAN_REVIEW',
        rows=len(rows),counts_by_type=dict(Counter(r['category'] for r in rows)),
        note='Sampled from exact train N2 pairs in the main candidate release; no fresh resampling of titles. No val/test judgments used.'))
    result=render(rows,release/'images',audit_dir/'N2_v2_review.html')
    write_json(audit_dir/'image_validation.json',result)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',default='configs/abo_home_v2.json');ap.add_argument('--raw-dir',default='data/raw')
    ap.add_argument('--out-dir',default='data/releases/abo-home-v2-20261103')
    ap.add_argument('--audit-dir',default='../output/n2_home_v2_20261103')
    ap.add_argument('--download-images',action='store_true');ap.add_argument('--resume-images',action='store_true')
    args=ap.parse_args();out=Path(args.out_dir);config=json.loads(Path(args.config).read_text())
    if args.resume_images:
        items=read_csv(out/'items.csv');pairs=read_csv(out/'pairs.csv')
    else:
        if (out/'manifest.json').exists():raise ValueError('Release exists; choose new version or --resume-images.')
        mapping=load_image_path_map(Path(args.raw_dir)/'images/metadata/images.csv.gz')
        rows,raw,total,files=load_records(Path(args.raw_dir)/'listings/metadata',mapping)
        print('raw records',total,'English image records',len(rows),flush=True)
        representatives,excluded,groups=group_records(rows,config)
        items,counts=split_and_filter(representatives,config)
        print('scope groups',len(representatives),'retained groups',len(items),flush=True)
        pairs,allocation,reuse,relaxation,n3audit,n3skips=assign_negatives(items,raw,config)
        checks=validate(items,pairs,config)
        write_csv(out/'items.csv',items,ITEM_FIELDS);write_csv(out/'pairs.csv',pairs,PAIR_FIELDS)
        for split in ['train','val','test']:write_csv(out/f'pairs_{split}.csv',[r for r in pairs if r['split']==split],PAIR_FIELDS)
        write_csv(out/'category_ranking.csv',counts,list(counts[0]));write_csv(out/'scope_exclusions.csv',excluded,['item_id','product_type','reason'])
        write_csv(out/'allocations.csv',allocation,list(allocation[0]));write_csv(out/'title_source_reuse.csv',reuse,['split','text_group_id','uses'])
        write_csv(out/'reuse_relaxations.csv',relaxation,['split','pair_id','text_group_id','use_count'])
        write_csv(out/'n3_audit.csv',n3audit,list(n3audit[0]));write_csv(out/'n3_skipped.csv',n3skips,['item_id','split','reason'])
        memberrows=[dict(group_id=gid,item_id=r['item_id'],representative_item_id=next(i['item_id'] for i in representatives if i['group_id']==gid)) for gid,rs in groups.items() for r in rs]
        write_csv(out/'group_members.csv',memberrows,['group_id','item_id','representative_item_id'])
        write_json(out/'config.json',config);write_json(out/'validation.json',checks)
        write_json(out/'manifest.json',dict(version=config['version'],status='UNREVIEWED_CANDIDATE_RELEASE',raw_records=total,
             english_image_records=len(rows),scope_groups=len(representatives),retained_groups=len(items),pairs=len(pairs),
             allocations=allocation,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
             generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),n3_rule_sha256=hashlib.sha256((Path(__file__).resolve().parents[1]/'negatives/build_n3.py').read_bytes()).hexdigest(),
             images_complete=False,scope='All 16 official shards scanned; explicit type/node scope, group and size filters applied. Not all Amazon home products.',
             legacy_note='Old pilot/train/val/test have already been inspected. v2 is a new candidate split, not independently pristine of earlier project exploration.'))
    if args.download_images or args.resume_images:
        results=download_images(items,out/'images')
        write_csv(out/'image_manifest.csv',results,['image_path','sha256','bytes','error'])
        errors=[r for r in results if r['error']]
        manifest=json.loads((out/'manifest.json').read_text());manifest['images_complete']=not errors;manifest['image_failures']=len(errors)
        write_json(out/'manifest.json',manifest)
        if errors:raise ValueError(f'{len(errors)} image failures; retry --resume-images.')
        create_audit(items,pairs,out,Path(args.audit_dir),config)
    print(json.dumps(json.loads((out/'manifest.json').read_text()),indent=2),flush=True)


if __name__=='__main__':main()
