"""Small, dependency-free helpers shared by Sean's MVP scripts."""
import csv
import hashlib
import json
from pathlib import Path

PAIR_FIELDS = ['pair_id', 'item_id', 'image_path', 'text', 'label', 'neg_type', 'category', 'year', 'split']
REVIEW_FIELDS = ['pair_id', 'neg_type', 'split', 'category', 'text_item_id', 'image_item_id',
                 'image_path', 'original_text', 'text', 'attribute', 'old_value', 'new_value',
                 'review_decision', 'reason', 'notes']


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def stable_key(seed, value):
    return hashlib.sha256(f'{seed}:{value}'.encode()).hexdigest()


def validate_items(items):
    seen = set()
    required = {'item_id', 'title', 'image_path', 'product_type', 'group_id', 'split'}
    for row in items:
        if not required.issubset(row) or any(not row[k] for k in required):
            raise ValueError('items must contain nonempty ' + ', '.join(sorted(required)))
        if row['item_id'] in seen:
            raise ValueError('duplicate item_id: ' + row['item_id'])
        seen.add(row['item_id'])


def pair(item, kind, text=None, image=None):
    image = image or item
    return dict(pair_id=f"{item['item_id']}_{kind}", item_id=image['item_id'],
                image_path=image['image_path'], text=text if text is not None else item['title'],
                label=1 if kind == 'pos' else 0, neg_type=kind, category=item['product_type'],
                year=item.get('year', ''), split=item['split'])
