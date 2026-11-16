"""Verify the frozen V3 snapshot from a repository or extracted data package."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = Path(__file__).resolve().parent


def verify():
    manifest = json.loads((RELEASE / 'manifest.json').read_text())
    for relative, expected in manifest['files_sha256'].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Checksum mismatch: {relative}')
    with (ROOT / manifest['pairs_csv']).open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 6670 or len({r['pair_id'] for r in rows}) != 6670:
        raise ValueError('Incorrect pair count or duplicate IDs')
    anchors = defaultdict(list)
    for row in rows:
        anchors[row['anchor_item_id']].append(row)
    if len(anchors) != 3335:
        raise ValueError('Incorrect anchor count')
    for anchor, pair in anchors.items():
        if len(pair) != 2 or {r['label'] for r in pair} != {'0', '1'}:
            raise ValueError(f'Invalid positive/negative pair: {anchor}')
        for field in ('image_path', 'split', 'anchor_group_id'):
            if len({r[field] for r in pair}) != 1:
                raise ValueError(f'Inconsistent {field}: {anchor}')
    counts = dict(Counter(r['split'] + ':' + r['neg_type'] for r in rows))
    if counts != manifest['counts']:
        raise ValueError('Split/type counts differ from frozen manifest')
    print(f"Verified {manifest['release_id']}: 3335 anchors, 6670 pairs")
    print('Pairs SHA-256:', manifest['files_sha256'][manifest['pairs_csv']])


if __name__ == '__main__':
    verify()
