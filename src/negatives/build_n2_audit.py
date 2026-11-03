"""Build a train-only, fixed-image/random-title N2 development audit.

This is an isolated audit version, not a replacement for the pilot schema or
its published scores. Sampling is uniform over eligible donor groups, then
over eligible products within the selected group. No model scores are used.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random

from sean_common import read_csv, validate_items, write_csv, write_json

DECISIONS = {'', 'match', 'mismatch', 'uncertain'}
MUTABLE = {'review_decision', 'reason', 'notes'}
FIELDS = ['dataset_id', 'pair_sha256', 'pair_id', 'neg_type', 'split', 'category',
          'anchor_item_id', 'image_item_id', 'text_item_id', 'image_path',
          'anchor_group_id', 'text_group_id', 'original_text', 'text',
          'review_decision', 'reason', 'notes']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def clean_pool(items, max_shared=4):
    validate_items(items)
    paths, groups = defaultdict(set), defaultdict(set)
    frequency = Counter(r['image_path'] for r in items)
    for r in items:
        paths[r['image_path']].add(r['split'])
        groups[r['group_id']].add(r['split'])
    kept, rejected = [], []
    for r in items:
        reasons = []
        if len(groups[r['group_id']]) > 1:
            reasons.append('group_spans_splits')
        if len(paths[r['image_path']]) > 1:
            reasons.append('image_spans_splits')
        if frequency[r['image_path']] > max_shared:
            reasons.append('high_frequency_shared_image')
        if reasons:
            rejected.append(dict(item_id=r['item_id'], product_type=r['product_type'],
                                 split=r['split'], image_path=r['image_path'],
                                 reason=';'.join(reasons)))
        else:
            kept.append(r)
    return kept, rejected


def donor_groups(anchor, pool, positives):
    result = defaultdict(list)
    for donor in pool:
        if donor['split'] != anchor['split'] or donor['product_type'] != anchor['product_type']:
            continue
        if donor['group_id'] == anchor['group_id'] or donor['image_path'] == anchor['image_path']:
            continue
        if donor['title'].strip().casefold() == anchor['title'].strip().casefold():
            continue
        if (anchor['image_path'], donor['title'].strip().casefold()) in positives:
            continue
        result[donor['group_id']].append(donor)
    return result


def eligible_types(items, clean, min_total=100, min_train=50, min_val=10, min_test=10):
    positives = {(r['image_path'], r['title'].strip().casefold()) for r in items}
    pools = defaultdict(list)
    for r in clean:
        pools[(r['product_type'], r['split'])].append(r)
    limits = {'train': min_train, 'val': min_val, 'test': min_test}
    report, eligible = [], []
    for pt in sorted({r['product_type'] for r in items}):
        rows = [r for r in clean if r['product_type'] == pt]
        counts = {s: len({r['group_id'] for r in pools[(pt, s)]}) for s in limits}
        total = len({r['group_id'] for r in rows})
        reasons = []
        if total < min_total:
            reasons.append('too_few_total_groups')
        for split, minimum in limits.items():
            if counts[split] < minimum:
                reasons.append('too_few_' + split + '_groups')
        minima = {}
        # Check actual legal candidate groups, not just pre-filter counts.
        if not reasons:
            for split, minimum in limits.items():
                pool = pools[(pt, split)]
                minima[split] = min(len(donor_groups(r, pool, positives)) for r in pool)
                if minima[split] < minimum - 1:
                    reasons.append('too_few_valid_' + split + '_donor_groups')
        if not reasons:
            eligible.append(pt)
        report.append(dict(product_type=pt, items_before=sum(r['product_type'] == pt for r in items),
                           items_after=len(rows), total_groups=total,
                           **{s + '_groups': n for s, n in counts.items()},
                           **{s + '_min_valid_donor_groups': minima.get(s, '') for s in limits},
                           eligible=not reasons, reason=';'.join(reasons)))
    return eligible, report, positives


def allocate(counts, size):
    total = sum(counts.values())
    if size < len(counts) or size > total:
        raise ValueError('Sample size must cover every retained type and not exceed available groups.')
    exact = {pt: size * count / total for pt, count in counts.items()}
    result = {pt: int(n) for pt, n in exact.items()}
    for pt in sorted(counts, key=lambda p: (-(exact[p] - result[p]), p))[:size - sum(result.values())]:
        result[pt] += 1
    if any(n == 0 for n in result.values()):
        raise ValueError('A type received zero samples; increase sample size.')
    return result


def sample_pairs(items, clean, types, positives, size=100, seed=20261102):
    train = [r for r in clean if r['split'] == 'train' and r['product_type'] in types]
    by_type = defaultdict(lambda: defaultdict(list))
    for r in train:
        by_type[r['product_type']][r['group_id']].append(r)
    quotas = allocate({pt: len(groups) for pt, groups in by_type.items()}, size)
    rng, result = random.Random(seed), []
    for pt in sorted(quotas):
        groups = by_type[pt]
        pool = [r for group in sorted(groups) for r in sorted(groups[group], key=lambda r: r['item_id'])]
        for gid in rng.sample(sorted(groups), quotas[pt]):
            anchor = rng.choice(sorted(groups[gid], key=lambda r: r['item_id']))
            choices = donor_groups(anchor, pool, positives)
            donor = rng.choice(sorted(choices[rng.choice(sorted(choices))], key=lambda r: r['item_id']))
            row = dict(pair_id='n2v2_' + anchor['item_id'] + '_N2', neg_type='N2', split='train',
                       category=pt, anchor_item_id=anchor['item_id'], image_item_id=anchor['item_id'],
                       text_item_id=donor['item_id'], image_path=anchor['image_path'],
                       anchor_group_id=gid, text_group_id=donor['group_id'],
                       original_text=anchor['title'], text=donor['title'],
                       review_decision='', reason='', notes='')
            row['pair_sha256'] = digest({k: v for k, v in row.items() if k not in MUTABLE})
            result.append(row)
    rng.shuffle(result)
    return result, quotas


def summarize_review(sample, reviews):
    def index(rows):
        result = {r['pair_id']: r for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate review pair IDs.')
        return result
    source, incoming = index(sample), index(reviews)
    if source.keys() != incoming.keys():
        raise ValueError('Review must retain every sample ID, including pending rows.')
    for pid, original in source.items():
        row = incoming[pid]
        for field in FIELDS:
            if field not in row or (field not in MUTABLE and row[field] != original[field]):
                raise ValueError('Missing or changed source field: ' + pid + '/' + field)
        if row['review_decision'] not in DECISIONS:
            raise ValueError('Invalid decision: ' + pid)
    def statistics(rows):
        counts = Counter(r['review_decision'] or 'pending' for r in rows)
        determinate = counts['match'] + counts['mismatch']
        return dict(n=len(rows), counts=dict(counts), determinate=determinate,
                    match_flag_rate=counts['match'] / determinate if determinate else None,
                    uncertain_rate=counts['uncertain'] / len(rows) if rows else None,
                    note='Reviewer judgments, not independently adjudicated ground truth.')
    rows = list(incoming.values())
    return dict(overall=statistics(rows), by_product_type={
        pt: statistics([r for r in rows if r['category'] == pt]) for pt in sorted({r['category'] for r in rows})})


def render(rows, image_root, output):
    from build_review import create_page
    result = create_page(rows, image_root, output, title=f'N2 v2 · 固定图片／同类随机标题 · {len(rows)} 条抽检')
    text = Path(output).read_text(encoding='utf-8')
    # Use one batch ID consistently in the manifest, CSV, browser storage and
    # JSON backups. The base template computes its own fingerprint otherwise.
    batch_id = rows[0]['dataset_id']
    if any(r['dataset_id'] != batch_id for r in rows):
        raise ValueError('Mixed review batch IDs.')
    text = text.replace(result['dataset_id'], batch_id)
    result['dataset_id'] = batch_id
    text = text.replace('CSE 6740 · SEAN / WP3 · HUMAN REVIEW', 'CSE 6740 · N2 v2 · DEVELOPMENT AUDIT')
    text = text.replace('N2 换图片，N3 改颜色。', '本批固定图片，在同 product type、同 train split 内随机替换不同商品组的真实标题。')
    text = text.replace('假负例率：', '初审匹配标记率：')
    text = text.replace('sean-review-', 'n2v2-review-')
    old = "const fields=['pair_id','neg_type','split','category','text_item_id','image_item_id','image_path','original_text','text','attribute','old_value','new_value','review_decision','reason','notes'];"
    if old not in text:
        raise ValueError('Review template export format changed; refusing to silently lose provenance.')
    text = text.replace(old, 'const fields=' + json.dumps(FIELDS) + ';')
    text = text.replace('sean_review_completed.csv', 'n2_v2_review_completed.csv')
    text = text.replace('sean_review_backup.json', 'n2_v2_review_backup.json')
    Path(output).write_text(text, encoding='utf-8')
    if result['image_failures']:
        write_json(Path(output).with_name('image_failures.json'), result['image_failures'])
        raise ValueError('Images missing or invalid. Retry rendering before starting review.')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--items-csv', default='docs/mini_version/items.csv')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--sample-size', type=int, default=100)
    ap.add_argument('--seed', type=int, default=20261102)
    ap.add_argument('--min-total-groups', type=int, default=100)
    ap.add_argument('--min-train-groups', type=int, default=50)
    ap.add_argument('--min-val-groups', type=int, default=10)
    ap.add_argument('--min-test-groups', type=int, default=10)
    ap.add_argument('--max-shared-image', type=int, default=4)
    ap.add_argument('--render', action='store_true')
    ap.add_argument('--image-root', default='data/images')
    ap.add_argument('--review-csv', help='Validate and summarize an exported review instead of generating data.')
    args = ap.parse_args()
    out = Path(args.out_dir)
    if args.review_csv:
        result = summarize_review(read_csv(out / 'review_sample.csv'), read_csv(args.review_csv))
        write_json(out / 'review_summary.json', result)
        print(json.dumps(result, indent=2))
        return
    if min(args.min_train_groups, args.min_val_groups, args.min_test_groups) < 2:
        ap.error('Every split must require at least two independent groups.')
    if min(args.sample_size, args.min_total_groups, args.max_shared_image) < 1:
        ap.error('Counts must be positive.')
    if (out / 'review_sample.csv').exists():
        # Never regenerate or overwrite an existing review batch under changed rules.
        if not args.render:
            ap.error('Batch already exists. Choose a new output directory.')
        rows = read_csv(out / 'review_sample.csv')
        manifest = json.loads((out / 'manifest.json').read_text())
        if digest(rows) != manifest['sample_content_sha256']:
            raise ValueError('Existing sample changed; refusing to render.')
    else:
        source = Path(args.items_csv)
        items = read_csv(source)
        clean, excluded = clean_pool(items, args.max_shared_image)
        types, report, positives = eligible_types(items, clean, args.min_total_groups,
            args.min_train_groups, args.min_val_groups, args.min_test_groups)
        rows, quotas = sample_pairs(items, clean, types, positives, args.sample_size, args.seed)
        rules = dict(seed=args.seed, min_total_groups=args.min_total_groups,
                     min_groups_by_split=dict(train=args.min_train_groups, val=args.min_val_groups, test=args.min_test_groups),
                     max_shared_image=args.max_shared_image, anchor_split='train',
                     direction='fixed image, random unmodified donor title',
                     donor_sampling='uniform eligible group, then uniform eligible item',
                     anchor_sampling='proportional allocation by train group count, uniform groups without replacement')
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        dataset_id = digest(dict(source_sha256=source_hash, rules=rules, rows=rows))[:20]
        for row in rows:
            row['dataset_id'] = dataset_id
        manifest = dict(dataset_id=dataset_id, status='UNREVIEWED_DEVELOPMENT_CANDIDATES',
                        source=str(source), source_sha256=source_hash,
                        source_scope='Existing furniture pilot; no fresh raw-ABO rebuild or split reassignment.',
                        rules=rules, source_items=len(items), clean_items=len(clean), excluded_items=len(excluded),
                        retained_types=types, sample_counts=quotas, rows=len(rows),
                        sample_content_sha256=digest(rows),
                        note='No model-based selection. No N1/N3 generation. Existing source group IDs/splits retained. Not a final benchmark or drop-in legacy evaluator input.')
        write_csv(out / 'review_sample.csv', rows, FIELDS)
        write_csv(out / 'eligibility.csv', report, list(report[0]))
        write_csv(out / 'excluded_items.csv', excluded, ['item_id', 'product_type', 'split', 'image_path', 'reason'])
        write_json(out / 'manifest.json', manifest)
    if args.render:
        result = render(rows, args.image_root, out / 'N2_v2_review.html')
        write_json(out / 'image_validation.json', result)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
