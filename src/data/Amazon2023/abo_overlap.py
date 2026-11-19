"""Load ABO identifiers used to exclude cross-source overlap from the AMR pilot.

ABO overlap is checked on three signals:
- ABO item_id == AMR parent_asin
- ABO image id (main or other) == any AMR MAIN-image variant image id
- exact normalized en_US title (length >= 12), as a conservative relisting check

This module only loads identifiers. It does not filter records.
"""
import html
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/data
from abo_io import en_us_value, iter_listings

ABO_SHARDS = {f'listings_{suffix}.json.gz' for suffix in '0123456789abcdef'}


def title_key(value):
    return re.sub(r'\s+', ' ', html.unescape('' if value is None else str(value)).casefold()).strip()


def load_abo_overlap_ids(listings_dir):
    """Return ABO item/image/title sets plus source summary."""
    listings_dir = Path(listings_dir)
    files = sorted(listings_dir.glob('listings_*.json.gz'))
    names = {path.name for path in files}
    if names != ABO_SHARDS:
        missing = sorted(ABO_SHARDS - names)
        extra = sorted(names - ABO_SHARDS)
        raise ValueError(
            'ABO listings shards are incomplete or unexpected; '
            f'missing={missing}; extra={extra}'
        )
    item_ids = set()
    image_ids = set()
    title_keys = set()
    records = 0
    for raw in iter_listings(listings_dir):
        records += 1
        item_id = raw.get('item_id')
        if item_id:
            item_ids.add(item_id)
        main_image_id = raw.get('main_image_id')
        if main_image_id:
            image_ids.add(main_image_id)
        for image_id in raw.get('other_image_id') or []:
            if image_id:
                image_ids.add(image_id)
        title = title_key(en_us_value(raw.get('item_name')))
        if len(title) >= 12:
            title_keys.add(title)
    return {
        'listings_dir': listings_dir.as_posix(),
        'shards': [path.name for path in files],
        'records': records,
        'item_ids': item_ids,
        'image_ids': image_ids,
        'title_keys': title_keys,
    }


def overlap_signals(item_id, title, image_ids, overlap, options=None):
    """Return [(signal, detail)] for every ABO overlap signal that matches."""
    options = options or {}
    signals = []
    if options.get('exclude_item_ids', True) and item_id in overlap['item_ids']:
        signals.append(('item_id', item_id))
    if options.get('exclude_exact_titles', True):
        key = title_key(title)
        if len(key) >= 12 and key in overlap['title_keys']:
            signals.append(('title', key))
    if options.get('exclude_image_ids', True):
        hits = sorted(image_id for image_id in image_ids if image_id in overlap['image_ids'])
        if hits:
            signals.append(('image_id', ';'.join(hits)))
    return signals


def overlap_summary(overlap, excluded=0, by_signal=None):
    return {
        'listings_dir': overlap['listings_dir'],
        'shards': overlap['shards'],
        'records': overlap['records'],
        'item_ids': len(overlap['item_ids']),
        'image_ids': len(overlap['image_ids']),
        'title_keys': len(overlap['title_keys']),
        'excluded': excluded,
        'by_signal': dict(sorted((by_signal or {}).items())),
    }
