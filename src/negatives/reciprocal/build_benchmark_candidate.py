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
FALLBACK_SEED = 20261114


def stable(value):
    return hashlib.sha256(f'{FALLBACK_SEED}:{value}'.encode()).hexdigest()


def fallback_negatives(items, negatives, replacements):
    """Keep v2 N1/N2; balance the remainder using only structural constraints."""
    positives = {(r['image_path'], r['title'].strip().casefold()) for r in items}
    result, provenance, reuse = {}, [], []
    for split in ('train', 'val', 'test'):
        pool = [r for r in items if r['split'] == split]
        pending = [r for r in pool if negatives[r['item_id']]['neg_type'] == 'N3'
                   and r['item_id'] not in replacements]
        fixed = [r for r in negatives.values() if r['split'] == split and r['neg_type'] in ('N1', 'N2')]
        used = Counter(r['text_group_id'] for r in fixed)
        target_n2 = (len(pool) - sum(r['split'] == split for r in replacements.values()) + 1) // 2
        need_n2 = target_n2 - sum(r['neg_type'] == 'N2' for r in fixed)
        assert 0 <= need_n2 <= len(pending)
        # Proportional per-category allocation, largest remainders; no scores/mining.
        categories = defaultdict(list)
        for r in sorted(pending, key=lambda r: stable(r['item_id'])):
            categories[r['product_type']].append(r)
        quotas = {cat: len(rs) * need_n2 / max(1, len(pending)) for cat, rs in categories.items()}
        allocation = {cat: int(q) for cat, q in quotas.items()}
        for cat in sorted(quotas, key=lambda cat: (-(quotas[cat] - allocation[cat]), cat))[:need_n2-sum(allocation.values())]:
            allocation[cat] += 1
        n2_ids = {r['item_id'] for cat, rs in categories.items() for r in rs[:allocation[cat]]}
        for anchor in sorted(pending, key=lambda r: stable('order:'+r['item_id'])):
            kind = 'N2' if anchor['item_id'] in n2_ids else 'N1'
            candidates = [r for r in pool if r['group_id'] != anchor['group_id']
                          and r['image_path'] != anchor['image_path']
                          and ((r['product_type'] == anchor['product_type']) == (kind == 'N2'))
                          and (anchor['image_path'], r['title'].strip().casefold()) not in positives]
            if not candidates:
                raise ValueError(f'No legal {kind} donor for {anchor["item_id"]}')
            donor = min(candidates, key=lambda r: (used[r['group_id']], stable(anchor['item_id']+':'+r['item_id'])))
            used[donor['group_id']] += 1
            old = negatives[anchor['item_id']]
            row = dict(old, pair_id=anchor['item_id']+'_'+kind, neg_type=kind, text=donor['title'],
                       text_item_id=donor['item_id'], text_group_id=donor['group_id'], label_status='generated_unreviewed')
            result[anchor['item_id']] = row
            provenance.append(dict(pair_id=row['pair_id'], source_pair_id=old['pair_id'], split=split,
                                   anchor_item_id=anchor['item_id'], donor_item_id=donor['item_id'],
                                   donor_group_id=donor['group_id'], neg_type=kind,
                                   reason='old_N3_without_accepted_reciprocal', review_status='unreviewed'))
        reuse.extend(dict(split=split, text_group_id=gid, uses=count, soft_limit_exceeded=count > 3)
                     for gid, count in sorted(used.items()))
    return result, provenance, reuse


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
    assert all(negatives[a]['neg_type'] == 'N3' for a in replacements)
    fallback, fallback_provenance, reuse = fallback_negatives(items, negatives, replacements)
    rows = []
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
            neg = fallback[anchor]
        rows.extend([dict(pos, dataset_version=VERSION), dict(neg, dataset_version=VERSION)])
    validate(rows, items, replacements)
    assert set(positives) == {r['anchor_item_id'] for r in rows}
    write(out / 'pairs.csv', rows, fields)
    write(out / 'n3_provenance.csv', provenance, list(provenance[0]))
    write(out / 'fallback_provenance.csv', fallback_provenance, list(fallback_provenance[0]))
    write(out / 'title_donor_reuse.csv', reuse, list(reuse[0]))
    # Superseded candidate output: no anchors are excluded under this policy.
    write(out / 'excluded_anchors.csv', [], ['anchor_item_id', 'split', 'reason'])
    manifest = dict(version=VERSION, status='CANDIDATE_NOT_FROZEN_NOT_HUMAN_CERTIFIED',
                    construction=stats, counts=dict(Counter(r['split']+':'+r['neg_type'] for r in rows)),
                    excluded_anchors=0, fallback_seed=FALLBACK_SEED,
                    fallback_counts=dict(Counter(r['split']+':'+r['neg_type'] for r in fallback_provenance)),
                    max_title_donor_uses=max(r['uses'] for r in reuse),
                    title_donor_soft_limit_exceedances=sum(r['soft_limit_exceeded'] for r in reuse),
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
    images = defaultdict(set)
    ix = {r['item_id']: r for r in items}
    for it in items:
        groups[it['group_id']].add(it['split'])
        images[it['image_path']].add(it['split'])
    assert all(len(s) == 1 for s in groups.values())
    assert all(len(s) == 1 for s in images.values())
    anchors = defaultdict(list)
    for r in rows:
        anchors[r['anchor_item_id']].append(r)
    for pair in anchors.values():
        assert len(pair) == 2 and {r['label'] for r in pair} == {'0', '1'}
        assert len({r['image_path'] for r in pair}) == len({r['split'] for r in pair}) == 1
        for r in pair:
            a, d = ix[r['anchor_item_id']], ix[r['text_item_id']]
            assert a['split'] == d['split'] == r['split']
            assert r['anchor_group_id'] == a['group_id'] and r['text_group_id'] == d['group_id']
            if r['neg_type'] in ('N1', 'N2'):
                assert a['group_id'] != d['group_id'] and a['image_path'] != d['image_path']
                assert (a['product_type'] == d['product_type']) == (r['neg_type'] == 'N2')
                assert r['text'] == d['title'] and r['text'].strip().casefold() != a['title'].strip().casefold()
            if r['neg_type'] == 'N3':
                assert r['text'] == replacements[r['anchor_item_id']]['text']
    for split in ('train', 'val', 'test'):
        counts = Counter(r['neg_type'] for r in rows if r['split'] == split)
        assert abs(counts['N1'] - counts['N2']) <= 1


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=root/'data/releases'/VERSION)
    args = parser.parse_args()
    build(root, args.out)
