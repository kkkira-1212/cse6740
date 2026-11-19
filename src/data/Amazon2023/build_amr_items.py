"""Filter Amazon Reviews 2023 Home & Kitchen metadata into source items.

This is an intermediate, type-balanced pilot builder. It does not create
near-duplicate groups, splits or negative pairs. Run:

python src/data/Amazon2023/build_amr_items.py \
  --config configs/amr_home_v1.json \
  --meta-jsonl "data/raw/Amazon 2023/meta_Home_and_Kitchen.jsonl" \
  --out-dir data/processed/amr-home-v1 \
  --max-per-type 200
"""
import argparse
from collections import Counter
import hashlib
import heapq
import json
from pathlib import Path, PurePosixPath
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'negatives'))
from sean_common import read_csv, write_csv, write_json, stable_key, validate_items

from abo_overlap import load_abo_overlap_ids, overlap_signals, overlap_summary
from amr_io import (
    ITEM_FIELDS, NO_MAIN_FIELDS, PRODUCT_TYPES, FilterSpec, canonical_json_sha256,
    classify_categories, clean_text, detail_string, image_id_from_url, image_path_for,
    iter_json_records, parse_date_first_available, safe_item_id,
    select_main_image, sha256_file, write_checksums,
)

ABO_OVERLAP_FIELDS = ['item_id', 'product_type', 'signals', 'details', 'source_line']


def write_json_lf(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class TopK:
    """Deterministic hash-priority top-K selection for one product type."""

    def __init__(self, size):
        self.size = size
        self.heap = []
        self.ids = set()
        self.sequence = 0

    def offer(self, priority_hex, item_id, row):
        if item_id in self.ids:
            return 'duplicate'
        if self.size <= 0:
            return 'cap'
        priority = int(priority_hex[:16], 16)
        entry = (-priority, item_id, self.sequence, row)
        self.sequence += 1
        if len(self.heap) < self.size:
            heapq.heappush(self.heap, entry)
            self.ids.add(item_id)
            return 'selected'
        worst = self.heap[0]
        worst_priority = -worst[0]
        if priority < worst_priority or (priority == worst_priority and item_id < worst[1]):
            removed = heapq.heapreplace(self.heap, entry)
            self.ids.discard(removed[1])
            self.ids.add(item_id)
            return 'selected'
        return 'cap'

    def rows(self):
        return sorted((entry[3] for entry in self.heap), key=lambda row: (row['product_type'], row['item_id']))

    def cutoff_hash(self):
        if not self.heap:
            return ''
        return f'{-self.heap[0][0]:016x}'


class AllItems:
    """Memory-heavy fallback for --max-per-type 0."""

    def __init__(self):
        self.rows = []
        self.ids = set()

    def offer(self, priority_hex, item_id, row):
        if item_id in self.ids:
            return 'duplicate'
        self.ids.add(item_id)
        self.rows.append(row)
        return 'selected'

    def rows(self):
        return sorted(self.rows, key=lambda row: (row['product_type'], row['item_id']))

    def cutoff_hash(self):
        return ''


def item_record(obj, product_type, reason, category_l2, category_leaf, rule_id, main, source_file, source_line):
    details = obj.get('details') if isinstance(obj.get('details'), dict) else {}
    raw_categories = obj.get('categories') if isinstance(obj.get('categories'), list) else []
    item_id = clean_text(obj.get('parent_asin'))
    year, year_source, dfa_raw = parse_date_first_available(details)
    urls = main.get('urls', {})
    return {
        'item_id': item_id,
        'title': clean_text(obj.get('title')),
        'image_path': image_path_for(product_type, item_id),
        'product_type': product_type,
        'node': ' | '.join(clean_text(value) for value in raw_categories if clean_text(value)),
        'color': detail_string(details.get('Color')),
        'material': detail_string(details.get('Material')),
        'group_id': 'amr_' + hashlib.sha256(item_id.encode('utf-8')).hexdigest()[:16],
        'split': 'unassigned',
        'main_image_id': main.get('image_id', ''),
        'image_url_large': urls.get('large', ''),
        'image_url_hi_res': urls.get('hi_res', ''),
        'image_url_thumb': urls.get('thumb', ''),
        'year': year,
        'year_source': year_source,
        'date_first_available': dfa_raw,
        'rating_number': '' if obj.get('rating_number') is None else str(obj.get('rating_number')),
        'average_rating': '' if obj.get('average_rating') is None else str(obj.get('average_rating')),
        'price': '' if obj.get('price') is None else str(obj.get('price')),
        'store': clean_text(obj.get('store')),
        'main_category': clean_text(obj.get('main_category')),
        'category_l2': category_l2,
        'category_leaf': category_leaf,
        'classification_rule': rule_id or reason,
        'source_file': str(source_file),
        'source_line': str(source_line),
    }


def scan_and_select(meta_path, config, spec, max_per_type, seed, progress_every=100000,
                    overlap=None, abo_options=None):
    top = {product_type: (TopK(max_per_type) if max_per_type > 0 else AllItems()) for product_type in PRODUCT_TYPES}
    by_type_mapped = Counter()
    by_type_eligible = Counter()
    by_type_dfa = Counter()
    by_type_main = Counter()
    by_second = Counter()
    exclusions = Counter()
    no_main = []
    abo_rows = []
    abo_by_signal = Counter()
    malformed = []
    malformed_examples = []
    duplicates = 0
    abo_options = abo_options or {}
    lines = 0
    json_ok = 0
    started = time.time()

    for line_number, obj, error in iter_json_records(meta_path):
        lines += 1
        if obj is None:
            exclusions['malformed_json'] += 1
            malformed.append(error)
            if len(malformed_examples) < 20:
                malformed_examples.append({'line': line_number, 'error': error})
            continue
        json_ok += 1
        categories = obj.get('categories')
        if isinstance(categories, list) and len(categories) > 1:
            by_second[clean_text(categories[1])] += 1
        elif isinstance(categories, list) and categories:
            by_second[clean_text(categories[0])] += 1
        else:
            by_second['NONE'] += 1

        product_type, reason, category_l2, category_leaf, rule_id = classify_categories(categories, spec)
        if not product_type:
            exclusions[reason] += 1
            continue
        by_type_mapped[product_type] += 1

        item_id = clean_text(obj.get('parent_asin'))
        if not item_id:
            exclusions['missing_parent_asin'] += 1
            continue
        if not safe_item_id(item_id):
            exclusions['invalid_parent_asin'] += 1
            continue
        title = clean_text(obj.get('title'))
        if not title:
            exclusions['missing_title'] += 1
            continue
        main = select_main_image(obj.get('images'), spec.allowed_hosts, spec.variant_order)
        category_path = ' | '.join(clean_text(value) for value in (categories or []) if clean_text(value))
        if overlap:
            image_ids = {
                image_id_from_url(url)
                for url in main.get('urls', {}).values() if url
            }
            image_ids.discard('')
            signals = overlap_signals(item_id, title, image_ids, overlap, abo_options)
            if signals:
                exclusions['abo_overlap'] += 1
                for signal, _ in signals:
                    abo_by_signal[signal] += 1
                if len(abo_rows) < 10000:
                    abo_rows.append({
                        'item_id': item_id,
                        'product_type': product_type,
                        'signals': ';'.join(signal for signal, _ in signals),
                        'details': '; '.join(f'{signal}={detail}' for signal, detail in signals),
                        'source_line': str(line_number),
                    })
                continue
        if main['reason'] == 'no_main_variant':
            exclusions['no_main_image'] += 1
            if len(no_main) < 10000:
                no_main.append({
                    'item_id': item_id, 'product_type': product_type,
                    'category_path': category_path, 'reason': 'no_main_variant',
                    'source_line': str(line_number),
                })
            continue
        if main['reason'] != 'ok':
            exclusions['no_usable_image_url'] += 1
            if len(no_main) < 10000:
                no_main.append({
                    'item_id': item_id, 'product_type': product_type,
                    'category_path': category_path, 'reason': 'no_usable_image_url',
                    'source_line': str(line_number),
                })
            continue

        by_type_eligible[product_type] += 1
        by_type_main[product_type] += 1
        year, _, _ = parse_date_first_available(obj.get('details'))
        if year:
            by_type_dfa[product_type] += 1

        row = item_record(
            obj, product_type, reason, category_l2, category_leaf, rule_id, main,
            Path(meta_path).as_posix(), line_number,
        )
        outcome = top[product_type].offer(stable_key(seed, item_id), item_id, row)
        if outcome == 'duplicate':
            duplicates += 1

        if progress_every and lines % progress_every == 0:
            elapsed = max(time.time() - started, 0.001)
            print(
                f'scanned {lines:,} lines ({lines / elapsed:,.0f}/s); '
                f'mapped={sum(by_type_mapped.values()):,}; '
                f'eligible={sum(by_type_eligible.values()):,}',
                flush=True,
            )

    selected = []
    sampling = []
    for product_type in PRODUCT_TYPES:
        rows = top[product_type].rows()
        selected.extend(rows)
        sampling.append({
            'product_type': product_type,
            'candidates': by_type_eligible[product_type],
            'selected': len(rows),
            'max_per_type': max_per_type,
            'truncated': int(by_type_eligible[product_type] > len(rows)),
            'cutoff_hash': top[product_type].cutoff_hash(),
        })
    selected.sort(key=lambda row: (row['product_type'], row['item_id']))
    eligible = sum(by_type_eligible.values())
    exclusions['output_cap'] = max(0, eligible - len(selected))
    return {
        'items': selected,
        'counters': {
            'lines': lines,
            'json_records': json_ok,
            'malformed_json': exclusions.get('malformed_json', 0),
            'mapped': sum(by_type_mapped.values()),
            'eligible': eligible,
            'selected': len(selected),
            'duplicates': duplicates,
        },
        'by_type_mapped': by_type_mapped,
        'by_type_eligible': by_type_eligible,
        'by_type_dfa': by_type_dfa,
        'by_type_main': by_type_main,
        'by_second': by_second,
        'exclusions': exclusions,
        'sampling': sampling,
        'no_main': no_main,
        'abo_overlap_rows': abo_rows,
        'abo_by_signal': abo_by_signal,
        'malformed_examples': malformed_examples,
        'malformed_messages': malformed[:20],
    }


def validate_source_items(items, config, max_per_type, counts):
    validate_items(items)
    spec = FilterSpec(config)
    seen_paths = set()
    by_type = Counter()
    for row in items:
        product_type = row['product_type']
        if product_type not in PRODUCT_TYPES:
            raise ValueError(f'unknown product_type: {product_type}')
        by_type[product_type] += 1
        if by_type[product_type] > max_per_type and max_per_type > 0:
            raise ValueError(f'{product_type} exceeds max_per_type')
        relative = PurePosixPath(row['image_path'])
        if relative.is_absolute() or '..' in relative.parts or len(relative.parts) != 3:
            raise ValueError(f'unsafe image_path: {row["image_path"]}')
        if relative.parts[0] != product_type.casefold() or relative.suffix != '.jpg':
            raise ValueError(f'image_path does not match product_type: {row["image_path"]}')
        if row['image_path'] in seen_paths:
            raise ValueError(f'duplicate image_path: {row["image_path"]}')
        seen_paths.add(row['image_path'])
        if not row['main_image_id']:
            raise ValueError(f'missing main_image_id: {row["item_id"]}')
        if row['split'] != 'unassigned':
            raise ValueError(f'expected split=unassigned: {row["item_id"]}')
        if not row['group_id'].startswith('amr_'):
            raise ValueError(f'unexpected group_id: {row["item_id"]}')
        if row['year'] and not re.fullmatch(r'(?:19|20)\d{2}', row['year']):
            raise ValueError(f'invalid year: {row["item_id"]}')
        categories = [part.strip() for part in row['node'].split(' | ') if part.strip()]
        reclassified, reason, _, _, _ = classify_categories(categories, spec)
        if reclassified != product_type:
            raise ValueError(f'category_leaf reclassification mismatch for {row["item_id"]}: {reclassified or reason}')
    if len(items) != counts['selected']:
        raise ValueError('selected count does not match items.csv')
    return {
        'status': 'STRUCTURAL_CHECKS_PASSED_INTERMEDIATE_SOURCE_ITEMS',
        'items': len(items),
        'unique_item_ids': len({row['item_id'] for row in items}),
        'unique_image_paths': len(seen_paths),
        'by_type': dict(sorted(by_type.items())),
        'max_per_type': max_per_type,
        'checks': [
            'validate_items', 'unique_image_paths', 'safe_image_paths',
            'main_image_id_present', 'split_placeholder', 'year_format',
            'category_reclassification', 'counts_match',
        ],
    }


def build_manifest(config, meta_path, source_sha256, source_bytes, scan, validation, max_per_type, seed, overlap=None):
    filter_config = {
        'root_category': config['root_category'],
        'second_level_categories': config['second_level_categories'],
        'type_rules': config['type_rules'],
        'fallbacks': config.get('fallbacks', {}),
        'exclude_segments_any': config.get('exclude_segments_any', []),
        'exclude_leaves_any': config.get('exclude_leaves_any', []),
        'abo_overlap': config.get('abo_overlap', {}),
    }
    generator = hashlib.sha256()
    for path in [Path(__file__), Path(__file__).resolve().parent / 'amr_io.py']:
        generator.update(path.read_bytes())
    return {
        'version': config['version'],
        'status': 'INTERMEDIATE_SOURCE_ITEMS_PILOT_NOT_FROZEN_NOT_HUMAN_REVIEWED',
        'source': {
            'path': Path(meta_path).as_posix(),
            'bytes': source_bytes,
            'sha256': source_sha256,
            'sha256_skipped': not bool(source_sha256),
            'lines': scan['counters']['lines'],
            'json_records': scan['counters']['json_records'],
            'malformed_json': scan['counters']['malformed_json'],
            'malformed_examples': scan['malformed_examples'],
        },
        'config_sha256': canonical_json_sha256(config),
        'filter_rule_sha256': canonical_json_sha256(filter_config),
        'generator_sha256': generator.hexdigest(),
        'filter': {
            'root': config['root_category'],
            'second_level_categories': config['second_level_categories'],
            'types': PRODUCT_TYPES,
            'seed': seed,
            'max_per_type': max_per_type,
            'sampling_method': 'stable_hash_topk',
        },
        'counts': {
            **scan['counters'],
            'by_type_mapped': dict(sorted(scan['by_type_mapped'].items())),
            'by_type_eligible': dict(sorted(scan['by_type_eligible'].items())),
            'by_type_selected': validation['by_type'],
            'excluded_by_reason': dict(sorted(scan['exclusions'].items())),
        },
        'sampling': scan['sampling'],
        'abo_overlap': (
            overlap_summary(overlap, scan['exclusions'].get('abo_overlap', 0), scan['abo_by_signal'])
            if overlap else {'enabled': False}
        ),
        'dfa': {
            'by_type': {
                product_type: {
                    'eligible': scan['by_type_eligible'][product_type],
                    'with_dfa': scan['by_type_dfa'][product_type],
                    'coverage': (
                        scan['by_type_dfa'][product_type] / scan['by_type_eligible'][product_type]
                        if scan['by_type_eligible'][product_type] else 0.0
                    ),
                }
                for product_type in PRODUCT_TYPES
            },
        },
        'images': {
            'requested': 0, 'ok': 0, 'resumed_valid': 0, 'failed': 0,
            'complete': False, 'variants_used': {}, 'failure_reasons': {},
        },
        'validation': validation,
        'limitations': [
            'Type-balanced pilot (200/type), not natural category prevalence.',
            'HOME and HOME_FURNITURE_AND_DECOR are broad catch-all types and have large eligible pools.',
            'Positives are listing title + MAIN image and are not human-verified.',
            'year comes only from Date First Available; review timestamps are not used yet.',
            'No near-duplicate grouping, ABO-overlap exclusion, splits or negatives in this phase.',
            'group_id and split=unassigned are placeholders for the next phase.',
        ],
    }


def write_build_outputs(out_dir, config, meta_path, source_sha256, source_bytes, scan, validation, max_per_type, seed, overlap=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / 'items.csv', scan['items'], ITEM_FIELDS)
    filter_rows = []
    dfa_rows = []
    for product_type in PRODUCT_TYPES:
        eligible = scan['by_type_eligible'][product_type]
        selected = validation['by_type'].get(product_type, 0)
        with_dfa = scan['by_type_dfa'][product_type]
        filter_rows.append({
            'product_type': product_type,
            'eligible': eligible,
            'selected': selected,
            'with_dfa': with_dfa,
            'with_main_image': scan['by_type_main'][product_type],
        })
        dfa_rows.append({
            'product_type': product_type,
            'eligible': eligible,
            'with_dfa': with_dfa,
            'coverage': f'{with_dfa / eligible:.4f}' if eligible else '0.0000',
        })
    write_csv(out_dir / 'filter_summary.csv', filter_rows,
              ['product_type', 'eligible', 'selected', 'with_dfa', 'with_main_image'])
    write_csv(out_dir / 'sampling_summary.csv', scan['sampling'],
              ['product_type', 'candidates', 'selected', 'max_per_type', 'truncated', 'cutoff_hash'])
    write_csv(out_dir / 'dfa_summary.csv', dfa_rows,
              ['product_type', 'eligible', 'with_dfa', 'coverage'])
    write_csv(
        out_dir / 'second_level_counts.csv',
        [{'second_level_category': key, 'count': value} for key, value in sorted(scan['by_second'].items())],
        ['second_level_category', 'count'],
    )
    write_csv(
        out_dir / 'exclusion_summary.csv',
        [{'reason': key, 'count': value} for key, value in sorted(scan['exclusions'].items())],
        ['reason', 'count'],
    )
    if scan['no_main']:
        write_csv(out_dir / 'no_main_images.csv', scan['no_main'], NO_MAIN_FIELDS)
    if scan['abo_overlap_rows']:
        write_csv(out_dir / 'abo_overlap.csv', scan['abo_overlap_rows'], ABO_OVERLAP_FIELDS)
    write_json_lf(out_dir / 'config.json', config)
    manifest = build_manifest(
        config, meta_path, source_sha256, source_bytes, scan, validation,
        max_per_type, seed, overlap=overlap,
    )
    write_json_lf(out_dir / 'validation.json', validation)
    write_json_lf(out_dir / 'manifest.json', manifest)
    write_checksums(out_dir, [
        'items.csv', 'filter_summary.csv', 'sampling_summary.csv', 'dfa_summary.csv',
        'second_level_counts.csv', 'exclusion_summary.csv', 'no_main_images.csv',
        'abo_overlap.csv', 'config.json', 'validation.json', 'manifest.json',
    ])
    return manifest


def _download_settings(config, args):
    from download_amr_images import DownloadSettings
    images = config['images']
    return DownloadSettings(
        variant_order=tuple(images.get('variant_order', ['large', 'hi_res', 'thumb'])),
        workers=args.workers if args.workers is not None else images.get('workers', 4),
        requests_per_second=(
            args.requests_per_second if args.requests_per_second is not None
            else images.get('requests_per_second', 2.0)
        ),
        timeout=args.timeout if args.timeout is not None else images.get('timeout_seconds', 30),
        retries=args.retries if args.retries is not None else images.get('retries', 3),
        max_bytes=images.get('max_bytes', 20_000_000),
        min_dimension=images.get('min_dimension', 64),
        max_dimension=images.get('max_dimension', 10000),
        max_pixels=images.get('max_pixels', 60_000_000),
        allowed_hosts=tuple(images.get('allowed_hosts', ['m.media-amazon.com'])),
        allowed_formats=tuple(images.get('allowed_formats', ['JPEG'])),
        low_resolution_threshold=images.get('low_resolution_threshold', 224),
    )


def download_after_build(out_dir, items, config, args, force=False):
    from download_amr_images import read_image_manifest, run_download, write_download_results
    settings = _download_settings(config, args)
    out_dir = Path(out_dir)
    items_sha256 = sha256_file(out_dir / 'items.csv')
    manifest_path = out_dir / 'manifest.json'
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        expected = previous.get('images', {}).get('items_sha256', '')
        if expected and expected != items_sha256 and not force:
            raise SystemExit('items.csv changed since the previous download; use --force or a new out-dir.')
    existing = read_image_manifest(out_dir / 'image_manifest.csv')
    rows, stats = run_download(
        items, out_dir / 'images', settings,
        existing_rows=existing, force=force, limit=args.limit,
    )
    write_download_results(out_dir, rows, stats, items_sha256, config_version=config['version'])
    return 0 if stats['failed'] == 0 else 1


def resume_images(out_dir, config, args):
    out_dir = Path(out_dir)
    items_path = out_dir / 'items.csv'
    if not items_path.is_file():
        raise SystemExit(f'No items.csv in {out_dir}; run the builder first.')
    items = read_csv(items_path)
    return download_after_build(out_dir, items, config, args, force=args.force)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/amr_home_v1.json')
    parser.add_argument('--meta-jsonl', default=None)
    parser.add_argument('--out-dir', default='data/processed/amr-home-v1')
    parser.add_argument('--max-per-type', type=int, default=None, help='0 keeps every eligible item (memory-heavy)')
    parser.add_argument('--limit', type=int, default=None, help='smoke-test cap on the final selected rows')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--download-images', action='store_true')
    parser.add_argument('--resume-images', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--progress-every', type=int, default=100000)
    parser.add_argument('--skip-source-hash', action='store_true')
    parser.add_argument('--abo-listings-dir', default=None)
    parser.add_argument('--skip-abo-overlap', action='store_true')
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--requests-per-second', type=float, default=None)
    parser.add_argument('--timeout', type=float, default=None)
    parser.add_argument('--retries', type=int, default=None)
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    if args.seed is not None:
        config['seed'] = args.seed
    seed = config['seed']
    max_per_type = args.max_per_type if args.max_per_type is not None else config.get('max_per_type', 200)
    meta_path = Path(args.meta_jsonl or config['source']['path'])
    out_dir = Path(args.out_dir)

    if args.resume_images:
        return resume_images(out_dir, config, args)
    if not args.dry_run and (out_dir / 'manifest.json').exists() and not args.force:
        raise SystemExit('Output exists; choose a new --out-dir, use --force, or --resume-images.')

    if not meta_path.is_file():
        raise SystemExit(f'Metadata file not found: {meta_path}')
    source_bytes = meta_path.stat().st_size
    source_sha256 = '' if args.skip_source_hash else sha256_file(meta_path)
    spec = FilterSpec(config)
    abo_config = config.get('abo_overlap', {})
    overlap = None
    if abo_config.get('enabled', True) and not args.skip_abo_overlap:
        abo_dir = Path(args.abo_listings_dir or abo_config.get('listings_dir', 'data/raw/listings/metadata'))
        if not abo_dir.is_dir():
            raise SystemExit(f'ABO listings directory not found: {abo_dir}; use --skip-abo-overlap to disable.')
        print(f'loading ABO overlap IDs from {abo_dir} ...', flush=True)
        overlap = load_abo_overlap_ids(abo_dir)
        print(
            f'ABO overlap: records={overlap["records"]:,}; '
            f'item_ids={len(overlap["item_ids"]):,}; '
            f'image_ids={len(overlap["image_ids"]):,}; '
            f'title_keys={len(overlap["title_keys"]):,}',
            flush=True,
        )
    started = time.time()
    scan = scan_and_select(
        meta_path, config, spec, max_per_type, seed, args.progress_every,
        overlap=overlap, abo_options=abo_config,
    )
    items = scan['items']
    if args.limit is not None and args.limit >= 0:
        items = items[:args.limit]
    scan['counters']['selected'] = len(items)
    scan['exclusions']['output_cap'] = max(0, scan['counters']['eligible'] - len(items))
    selected_counts = Counter(row['product_type'] for row in items)
    for sample in scan['sampling']:
        sample['selected'] = selected_counts.get(sample['product_type'], 0)
        sample['truncated'] = int(sample['candidates'] > sample['selected'])
    validation = validate_source_items(items, config, max_per_type, {
        'selected': len(items),
    })
    scan['items'] = items

    if args.dry_run:
        print(json.dumps({
            'counters': scan['counters'],
            'by_type_eligible': dict(sorted(scan['by_type_eligible'].items())),
            'by_type_selected': validation['by_type'],
            'exclusions': dict(sorted(scan['exclusions'].items())),
            'abo_overlap': (
                overlap_summary(overlap, scan['exclusions'].get('abo_overlap', 0), scan['abo_by_signal'])
                if overlap else {'enabled': False}
            ),
            'elapsed_seconds': round(time.time() - started, 1),
        }, ensure_ascii=False, indent=2))
        return 0

    manifest = write_build_outputs(
        out_dir, config, meta_path, source_sha256, source_bytes,
        scan, validation, max_per_type, seed, overlap=overlap,
    )
    print(json.dumps({
        'out_dir': str(out_dir),
        'selected': manifest['counts']['selected'],
        'by_type': manifest['counts']['by_type_selected'],
        'elapsed_seconds': round(time.time() - started, 1),
    }, ensure_ascii=False, indent=2), flush=True)

    if args.download_images:
        return download_after_build(out_dir, items, config, args, force=args.force)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
