"""Validate extracted release files, pair structure and optional image hashes."""
import argparse,csv,collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(name):
    with (ROOT/name).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def check(images=False):
    sums=json.loads((ROOT/'checksums.json').read_text())
    for name,expected in sums.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
    items=rows('items.csv');pairs=rows('pairs.csv');ix={r['item_id']:r for r in items}
    assert len(ix)==len(items)==len({r['group_id'] for r in items})
    assert len({r['image_path'] for r in items})==len(items)
    assert len({r['pair_id'] for r in pairs})==len(pairs)
    assert len({(r['image_path'],r['text']) for r in pairs})==len(pairs)
    per=collections.defaultdict(list)
    for r in pairs:
        a=ix[r['anchor_item_id']];d=ix[r['text_item_id']]
        assert a['split']==d['split']==r['split']
        assert r['image_path']==a['image_path'] and r['image_item_id']==r['item_id']==a['item_id']
        if r['neg_type'] in ['N1','N2']:
            assert a['group_id']!=d['group_id']
            assert (a['product_type']==d['product_type'])==(r['neg_type']=='N2')
            assert r['text']==d['title']
        per[r['anchor_item_id']].append(r)
    assert all(len(rs)==2 and sorted(r['label'] for r in rs)==['0','1'] for rs in per.values())
    for split in ['train','val','test']:
        part=rows('pairs_'+split+'.csv')
        assert part==[r for r in pairs if r['split']==split]
        c=collections.Counter(r['neg_type'] for r in part)
        assert c['pos']==c['N1']+c['N2']+c['N3']
        assert abs(c['N1']-c['N2'])<=1 and c['N3']<=min(c['N1'],c['N2'])
    if images:
        for r in rows('image_manifest.csv'):
            assert not r['error']
            assert hashlib.sha256((ROOT/'images'/r['image_path']).read_bytes()).hexdigest()==r['sha256'],r['image_path']
    print('PASS:',len(items),'anchors,',len(pairs),'pairs; structural validation only, not human label certification.')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--images',action='store_true');a=ap.parse_args();check(a.images)
