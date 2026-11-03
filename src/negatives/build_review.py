"""Sample N2/N3 pairs and create an offline, self-contained human review page.

The exported review CSV is input to finalize_review.py. Images are downloaded
only for sampled pairs and embedded; do NOT commit the generated HTML or images.
"""
import argparse
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

from sean_common import REVIEW_FIELDS, read_csv, stable_key, write_csv, write_json

BASE = 'https://amazon-berkeley-objects.s3.amazonaws.com/images/'


def sample_review(items, pairs, audit, n_per_type=100, seed=7, types=('N2', 'N3')):
    lookup = {r['item_id']: r for r in items}
    details = {r['pair_id']: r for r in audit}
    result = []
    for kind in types:
        candidates = [r for r in pairs if r['neg_type'] == kind]
        for row in sorted(candidates, key=lambda r: stable_key(seed, r['pair_id']))[:n_per_type]:
            source_id = row['pair_id'].removesuffix('_' + kind)
            if source_id not in lookup:
                raise ValueError('missing text source: ' + row['pair_id'])
            source = lookup[source_id]
            if row['item_id'] not in lookup:
                raise ValueError('missing image source: ' + row['pair_id'])
            d = details.get(row['pair_id'], {})
            result.append(dict(row, text_item_id=source_id, image_item_id=row['item_id'],
                               original_text=source['title'], attribute=d.get('attribute', ''),
                               old_value=d.get('old_value', ''), new_value=d.get('new_value', ''),
                               review_decision='', reason='', notes=''))
    if len({r['pair_id'] for r in result}) != len(result):
        raise ValueError('duplicate review pair IDs')
    return result


def load_image(relative, root):
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or not parts.parts or parts.parts[0] != 'small':
        return relative, None, 'unsafe or non-small image path'
    path = Path(root) / relative
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(BASE + relative, timeout=35) as r:
                content = r.read()
            temporary = path.with_suffix('.part')
            temporary.write_bytes(content)
            temporary.replace(path)
        content = path.read_bytes()
        # This validates the actual downloaded bytes, not metadata alone.
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        return relative, 'data:image/jpeg;base64,' + base64.b64encode(content).decode(), None
    except Exception as exc:
        return relative, None, f'{type(exc).__name__}: {exc}'


def create_page(rows, image_root, output, title='Sean · N2 / N3 人工审查'):
    images, failures = {}, {}
    paths = sorted({r['image_path'] for r in rows})
    with ThreadPoolExecutor(max_workers=12) as pool:
        for path, image, error in pool.map(lambda p: load_image(p, image_root), paths):
            images[path] = image
            if error:
                failures[path] = error
    data = [{**r, 'image_data': images[r['image_path']]} for r in rows]
    serialized = json.dumps(data, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:20]
    template = Path(__file__).with_name('review_template.html').read_text(encoding='utf-8')
    import html
    rendered = template.replace('__TITLE__', html.escape(title)).replace('__DATA__', serialized).replace('__KEY__', fingerprint)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(rendered, encoding='utf-8')
    return {'rows': len(rows), 'images': len(paths), 'image_failures': failures,
            'sample_by_type': dict(Counter(r['neg_type'] for r in rows)), 'dataset_id': fingerprint}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--items-csv', required=True)
    ap.add_argument('--pairs-csv', nargs='+', required=True)
    ap.add_argument('--n3-audit', required=True)
    ap.add_argument('--n-per-type', type=int, default=100)
    ap.add_argument('--types', nargs='+', default=['N2', 'N3'], choices=['N1', 'N2', 'N3'])
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--image-root', default='data/images')
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    if args.n_per_type < 1:
        ap.error('--n-per-type must be positive')
    pairs = [row for path in args.pairs_csv for row in read_csv(path)]
    if len({r['pair_id'] for r in pairs}) != len(pairs):
        raise ValueError('pair IDs must be unique across --pairs-csv inputs')
    rows = sample_review(read_csv(args.items_csv), pairs, read_csv(args.n3_audit), args.n_per_type, args.seed, args.types)
    out = Path(args.out_dir)
    write_csv(out / 'review_sample.csv', rows, REVIEW_FIELDS)
    summary = create_page(rows, args.image_root, out / 'review.html')
    summary.update(seed=args.seed, status='AWAITING_HUMAN_REVIEW', sampling='deterministic uniform hash sample per neg_type')
    write_json(out / 'review_manifest.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
