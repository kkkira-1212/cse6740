"""Verify the intermediate Amazon Reviews 2023 source-items output.

Checks items.csv, summaries, manifest, checksums and (optionally) every image
against image_manifest.csv. This is structural verification, not semantic
certification of listing title-image agreement.

Run:
python src/data/Amazon2023/verify_amr.py --out-dir data/processed/amr-home-v1 --images
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'negatives'))
from sean_common import read_csv

from amr_io import (
    IMAGE_MANIFEST_FIELDS, PRODUCT_TYPES, FilterSpec, classify_categories,
    sha256_file, write_json_lf,
)

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


def _fail(message):
    raise ValueError(message)


def verify(out_dir, config, check_images=False, allow_image_failures=False):
    out_dir = Path(out_dir)
    items_path = out_dir / 'items.csv'
    manifest_path = out_dir / 'manifest.json'
    checksums_path = out_dir / 'checksums.json'
    if not items_path.is_file():
        _fail(f'missing {items_path}')
    if not manifest_path.is_file():
        _fail(f'missing {manifest_path}')
    items = read_csv(items_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not items:
        _fail('items.csv is empty')
    if len(items) != manifest['counts']['selected']:
        _fail('items.csv row count differs from manifest counts.selected')
    if len(items) != sum(manifest['counts']['by_type_selected'].values()):
        _fail('items.csv row count differs from by_type_selected sum')
    spec = FilterSpec(config)
    seen_ids = set()
    seen_paths = set()
    by_type = {}
    year_count = 0
    for row in items:
        item_id = row['item_id']
        if item_id in seen_ids:
            _fail(f'duplicate item_id {item_id}')
        seen_ids.add(item_id)
        if row['product_type'] not in PRODUCT_TYPES:
            _fail(f'unknown product_type {row["product_type"]}')
        by_type[row['product_type']] = by_type.get(row['product_type'], 0) + 1
        relative = PurePosixPath(row['image_path'])
        if relative.is_absolute() or '..' in relative.parts or len(relative.parts) != 3:
            _fail(f'unsafe image_path {row["image_path"]}')
        if relative.parts[0] != row['product_type'].casefold() or relative.suffix != '.jpg':
            _fail(f'image_path/type mismatch {row["image_path"]}')
        if row['image_path'] in seen_paths:
            _fail(f'duplicate image_path {row["image_path"]}')
        seen_paths.add(row['image_path'])
        if not row['main_image_id']:
            _fail(f'missing main_image_id for {item_id}')
        if row['split'] != 'unassigned':
            _fail(f'expected split=unassigned for {item_id}')
        if not row['group_id'].startswith('amr_'):
            _fail(f'unexpected group_id for {item_id}')
        if row['year']:
            if not (len(row['year']) == 4 and row['year'].isdigit()):
                _fail(f'invalid year for {item_id}')
            year_count += 1
        categories = [part.strip() for part in row['node'].split(' | ') if part.strip()]
        reclassified, reason, _, _, _ = classify_categories(categories, spec)
        if reclassified != row['product_type']:
            _fail(f'reclassification mismatch for {item_id}: {reclassified or reason}')
    if by_type != manifest['counts']['by_type_selected']:
        _fail('per-type counts differ from manifest')
    if manifest.get('validation', {}).get('status') != 'STRUCTURAL_CHECKS_PASSED_INTERMEDIATE_SOURCE_ITEMS':
        _fail('validation.json status is not the expected intermediate status')

    if checksums_path.is_file():
        checksums = json.loads(checksums_path.read_text(encoding='utf-8'))
        for name, expected in checksums.items():
            path = out_dir / name
            if not path.is_file():
                _fail(f'checksummed file missing: {name}')
            actual = sha256_file(path)
            if actual != expected:
                _fail(f'checksum mismatch for {name}')
    else:
        _fail('missing checksums.json')

    image_rows = []
    image_failures = []
    checked_images = 0
    if check_images:
        image_manifest_path = out_dir / 'image_manifest.csv'
        if not image_manifest_path.is_file():
            _fail('missing image_manifest.csv')
        image_rows = read_csv(image_manifest_path)
        if len(image_rows) != len(items):
            _fail('image_manifest.csv does not have one row per item')
        image_by_id = {row['item_id']: row for row in image_rows}
        if len(image_by_id) != len(image_rows):
            _fail('duplicate item_id in image_manifest.csv')
        for item in items:
            image_row = image_by_id.get(item['item_id'])
            if image_row is None:
                _fail(f'missing image manifest row for {item["item_id"]}')
            if image_row['image_path'] != item['image_path']:
                _fail(f'image_path mismatch for {item["item_id"]}')
            if image_row['error']:
                if not allow_image_failures:
                    _fail(f'image failure for {item["item_id"]}: {image_row["error"]}')
                image_failures.append({
                    'item_id': item['item_id'],
                    'error_class': image_row.get('error_class', ''),
                    'error': image_row['error'],
                })
                continue
            target = out_dir / 'images' / PurePosixPath(item['image_path'])
            if not target.is_file():
                _fail(f'missing image file {target}')
            digest = sha256_file(target)
            if digest != image_row['sha256']:
                _fail(f'image hash mismatch for {item["item_id"]}')
            if Image is not None:
                with Image.open(target) as image:
                    image.verify()
            checked_images += 1
        leftovers = list((out_dir / 'images').rglob('*.part')) if (out_dir / 'images').is_dir() else []
        if leftovers:
            _fail(f'{len(leftovers)} .part files remain under images/')
        if not manifest.get('images', {}).get('complete') and not allow_image_failures:
            _fail('manifest images.complete is not true')

    result = {
        'status': 'STRUCTURAL_CHECKS_PASSED_WITH_IMAGE_FAILURES' if image_failures else 'STRUCTURAL_CHECKS_PASSED',
        'items': len(items),
        'by_type': by_type,
        'year_items': year_count,
        'images_checked': checked_images if check_images else 0,
        'image_failures': image_failures,
        'checks': [
            'unique_item_ids', 'unique_image_paths', 'safe_image_paths',
            'main_image_id_present', 'split_placeholder', 'year_format',
            'category_reclassification', 'manifest_counts', 'checksums',
        ] + (['image_manifest', 'image_hashes', 'pillow_decode', 'no_part_files'] if check_images else []),
    }
    write_json_lf(out_dir / 'verify.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', default='data/processed/amr-home-v1')
    parser.add_argument('--config', default='configs/amr_home_v1.json')
    parser.add_argument('--images', action='store_true')
    parser.add_argument('--allow-image-failures', action='store_true')
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    try:
        result = verify(
            Path(args.out_dir), config,
            check_images=args.images,
            allow_image_failures=args.allow_image_failures,
        )
    except Exception as exc:
        print(f'VERIFY FAILED: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
