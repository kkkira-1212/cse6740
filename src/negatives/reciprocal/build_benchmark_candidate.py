"""Build a versioned reciprocal benchmark candidate, without modifying v2.

No model scores are used. Existing train QC is preserved; held-out candidates
use the expanded generator's fixed rules independently within each split.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from build_expanded_n3 import FIELDS, generate, read, write

VERSION = 'abo-home-reciprocal-v3-candidate'


def build(root, out):
    source = root / 'data/releases/abo-home-v2-20261103'
    train_path = root / 'data/reviews/n3-reciprocal-expanded-dev-v2/training_negatives.csv'
    items = read(source / 'items.csv')
    heldout, stats = generate(items, read(source / 'n3_audit.csv'), [], splits=('val', 'test'))
    write(out / 'heldout_n3_candidates.csv', heldout, FIELDS)
    review_path = root / 'data/reviews/reciprocal-v3-model-assisted/decisions.csv'
    reviews = read(review_path)
    judged = {r['pair_id']: r for r in reviews}
    assert len(judged) == len(reviews) == len(heldout)
    for r in heldout:
        j = judged[r['pair_id']]
        assert j['pair_sha256'] == r['pair_sha256']
        assert j['negative_decision'] in {'mismatch', 'match', 'uncertain'}
    rejected = {r['exchange_id'] for r in heldout
                if judged[r['pair_id']]['negative_decision'] != 'mismatch'
                or judged[r['pair_id']]['original_color_check'] != 'consistent'}
    heldout = [dict(r, label_status='model_assisted_mismatch_not_human_verified',
                    review_status='model_assisted_mismatch', review_decision='mismatch')
               for r in heldout if r['exchange_id'] not in rejected]
    train = read(train_path)
    replacements = {r['anchor_item_id']: r for r in [*train, *heldout]}
    old = read(source / 'pairs.csv')
    fields = list(old[0])
    positives = {r['anchor_item_id']: r for r in old if r['label'] == '1'}
    negatives = {r['anchor_item_id']: r for r in old if r['label'] == '0'}
    rows, excluded = [], []
    provenance = []
    for anchor, pos in positives.items():
        neg = negatives[anchor]
        replacement = replacements.get(anchor)
        if replacement:
            neg = dict(pos, pair_id=anchor+'_N3', text=replacement['text'], label='0', neg_type='N3',
                       label_status=replacement['label_status'])
            provenance.append(dict(pair_id=neg['pair_id'], source_pair_id=replacement['pair_id'],
                                   exchange_id=replacement['exchange_id'], donor_item_id=replacement['donor_item_id'],
                                   review_status=replacement.get('review_status', 'unreviewed'),
                                   review_decision=replacement['review_decision']))
        elif neg['neg_type'] == 'N3':
            excluded.append(dict(anchor_item_id=anchor, split=pos['split'], reason='old_N3_without_reciprocal_replacement'))
            continue
        rows.extend([dict(pos, dataset_version=VERSION), dict(neg, dataset_version=VERSION)])
    validate(rows, items, replacements)
    write(out / 'pairs.csv', rows, fields)
    write(out / 'n3_provenance.csv', provenance, list(provenance[0]))
    write(out / 'excluded_anchors.csv', excluded, ['anchor_item_id', 'split', 'reason'])
    manifest = dict(version=VERSION, status='CANDIDATE_NOT_FROZEN_NOT_HUMAN_CERTIFIED',
                    construction=stats, counts=dict(Counter(r['split']+':'+r['neg_type'] for r in rows)),
                    excluded_anchors=dict(Counter(r['split'] for r in excluded)),
                    input_hash_policy='SHA-256 of text bytes with CRLF normalized to LF',
                    input_sha256={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                  for p in [source/'items.csv', source/'pairs.csv', source/'n3_audit.csv', train_path, review_path]},
                    rejected_heldout_exchanges=len(rejected),
                    output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.csv'))})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(manifest, indent=2))


def validate(rows, items, replacements):
    assert len({r['pair_id'] for r in rows}) == len(rows)
    assert len({(r['image_path'], r['text']) for r in rows}) == len(rows)
    groups = defaultdict(set)
    for it in items:
        groups[it['group_id']].add(it['split'])
    assert all(len(s) == 1 for s in groups.values())
    anchors = defaultdict(list)
    for r in rows:
        anchors[r['anchor_item_id']].append(r)
    for pair in anchors.values():
        assert len(pair) == 2 and {r['label'] for r in pair} == {'0', '1'}
        assert len({r['image_path'] for r in pair}) == len({r['split'] for r in pair}) == 1
        for r in pair:
            if r['neg_type'] == 'N3':
                assert r['text'] == replacements[r['anchor_item_id']]['text']


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=root/'data/releases'/VERSION)
    args = parser.parse_args()
    build(root, args.out)
