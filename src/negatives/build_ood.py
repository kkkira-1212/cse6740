"""WP10: provisional near/far ABO OOD sets; categories are configurable.

Reuse Kira's title normalization, schema, image metadata, and same-product-type
MiniLM nearest-neighbor N2 rule. Candidates never come from a different split.
Existing Kira items and their groups are all protected (not just train).
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'data'))
from abo_io import en_us_standardized, en_us_value, first_node_name, iter_listings, load_image_path_map
from build_items import normalize_title, UnionFind
from build_n3 import make_candidates
from minilm_onnx import encode
from sean_common import PAIR_FIELDS, REVIEW_FIELDS, pair, read_csv, stable_key, validate_items, write_csv, write_json

ITEM_FIELDS = ['item_id', 'title', 'image_path', 'product_type', 'node', 'color', 'material', 'group_id', 'split']


def select_items(records, existing, image_map, categories, max_per_tier, seed):
    validate_items(existing)
    if set(categories['ood_near']) & set(categories['ood_far']):
        raise ValueError('near/far categories must be disjoint')
    known_types = {r['product_type'] for r in existing}
    wanted_types = {pt for values in categories.values() for pt in values}
    if known_types & wanted_types:
        raise ValueError('OOD product_type appears in existing data: ' + str(known_types & wanted_types))
    candidates, raw = {}, {}
    pt_to_split = {pt: tier for tier, pts in categories.items() for pt in pts}
    for r in records:
        pt = r.get('product_type', [{}])[0].get('value', '')
        title = en_us_value(r.get('item_name'))
        image = image_map.get(r.get('main_image_id'))
        if pt not in wanted_types or not title or not image or 'swatch' in title.lower():
            continue
        color_val, color_std = en_us_standardized(r.get('color'))
        material, _ = en_us_standardized(r.get('material'))
        item_id = r['item_id']
        candidates[item_id] = dict(item_id=item_id, title=title, image_path='small/' + image,
                                   product_type=pt, node=first_node_name(r.get('node')) or '',
                                   color=color_std or color_val or '', material=material or '',
                                   split=pt_to_split[pt])
        raw[item_id] = r.get('color', [])

    # Group globally BEFORE tier sampling. Union original groups as well as the
    # image/title keys, so an OOD-relative renumbering cannot hide overlap.
    uf, images, titles, known_groups = UnionFind(), {}, {}, {}
    combined = list(existing) + list(candidates.values())
    frequencies = Counter(r['image_path'] for r in combined)
    for r in sorted(combined, key=lambda r: r['item_id']):
        item_id = r['item_id']
        uf.find(item_id)
        norm = normalize_title(r['title'], r.get('color', ''), r.get('material', ''))
        signals = [(images, r['image_path'])]
        if len(norm) > 3:
            signals.append((titles, (r['product_type'], norm)))
        for lookup, key in signals:
            if key in lookup:
                uf.union(item_id, lookup[key])
            lookup[key] = item_id
        if r.get('group_id'):
            if r['group_id'] in known_groups:
                uf.union(item_id, known_groups[r['group_id']])
            known_groups[r['group_id']] = item_id
    protected_roots = {uf.find(r['item_id']) for r in existing}
    members = defaultdict(list)
    for r in combined:
        members[uf.find(r['item_id'])].append(r['item_id'])
    stable_group = {root: 'ood_' + stable_key(0, min(ids))[:16] for root, ids in members.items()}
    pool, skipped = defaultdict(list), Counter()
    for r in candidates.values():
        root = uf.find(r['item_id'])
        if root in protected_roots:
            skipped['overlap_with_existing_group'] += 1
        elif frequencies[r['image_path']] > 4:
            skipped['high_frequency_shared_image'] += 1
        else:
            r['group_id'] = stable_group[root]
            pool[r['split']].append(r)
    # One representative per group keeps the mini test diverse. If any group
    # spans near/far, keep it in only one tier, never silently duplicate it.
    selected, used = [], set()
    for tier in sorted(categories):
        chosen = 0
        for r in sorted(pool[tier], key=lambda r: stable_key(seed, r['item_id'])):
            if r['group_id'] in used:
                continue
            selected.append(r)
            used.add(r['group_id'])
            chosen += 1
            if chosen >= max_per_tier:
                break
    return selected, raw, dict(skipped)


def build_pairs(items, embeddings, seed=42):
    import numpy as np
    validate_items(items)
    rows, skipped = [], Counter()
    for i, r in enumerate(items):
        rows.append(pair(r, 'pos'))
        eligible = [j for j, other in enumerate(items) if other['split'] == r['split'] and other['group_id'] != r['group_id']]
        if not eligible:
            skipped['N1_no_candidate'] += 1
        else:
            j = min(eligible, key=lambda j: stable_key(seed, r['item_id'] + ':' + items[j]['item_id']))
            rows.append(pair(r, 'N1', image=items[j]))
        eligible = sorted([j for j in eligible if items[j]['product_type'] == r['product_type']],
                          key=lambda j: items[j]['item_id'])
        if not eligible:
            skipped['N2_no_candidate'] += 1
        else:
            scores = embeddings[eligible] @ embeddings[i]
            j = eligible[int(np.argmax(scores))]
            rows.append(pair(r, 'N2', image=items[j]))
    return rows, dict(skipped)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--existing-items-csv', required=True)
    ap.add_argument('--listings-dir', required=True)
    ap.add_argument('--images-csv', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--near-types', nargs='+', default=['LAMP', 'LIGHT_FIXTURE'])
    ap.add_argument('--far-types', nargs='+', default=['SHOES', 'SANDAL', 'BOOT'])
    ap.add_argument('--max-per-tier', type=int, default=150)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--model-cache', default='data/processed/sean/model_cache')
    ap.add_argument('--model-revision', help='HF commit SHA; resolved SHA is saved if omitted')
    args = ap.parse_args()
    if args.max_per_tier < 1:
        ap.error('--max-per-tier must be positive')
    categories = dict(ood_near=args.near_types, ood_far=args.far_types)
    items, raw, excluded = select_items(iter_listings(args.listings_dir), read_csv(args.existing_items_csv),
                                        load_image_path_map(args.images_csv), categories, args.max_per_tier, args.seed)
    if {r['split'] for r in items} != set(categories):
        raise ValueError('Could not construct both OOD tiers; check metadata and categories')
    print(f'encoding {len(items)} OOD titles with MiniLM', flush=True)
    embeddings, model = encode([r['title'] for r in items], args.model_cache, args.model_revision)
    pairs, skipped = build_pairs(items, embeddings, args.seed)
    n3, audit, n3_skipped = make_candidates(items, args.seed, raw)
    pairs += n3
    out = Path(args.out_dir)
    write_csv(out / 'ood_items.csv', items, ITEM_FIELDS)
    write_csv(out / 'ood_pairs_candidates.csv', pairs, PAIR_FIELDS)
    write_csv(out / 'ood_n3_audit.csv', audit, REVIEW_FIELDS + ['group_id', 'raw_color_checked'])
    write_csv(out / 'ood_n3_skipped.csv', n3_skipped, ['item_id', 'split', 'reason'])
    summary = dict(status='PROVISIONAL_CATEGORIES_UNREVIEWED', seed=args.seed, categories=categories,
                   max_per_tier=args.max_per_tier, model=model, excluded=excluded, skipped_pairs=skipped,
                   item_counts=dict(Counter(r['split'] for r in items)),
                   pair_counts=dict(Counter(r['split'] + '/' + r['neg_type'] for r in pairs)),
                   group_overlap_with_existing=0,
                   note='No training on OOD; thresholds must come from ID validation. N3 coverage is unequal; no final class balance claimed.')
    write_json(out / 'ood_summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
