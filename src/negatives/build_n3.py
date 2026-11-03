"""WP3: conservative COLOR-only candidates, not human-verified negatives.

One candidate per eligible item, keeping its image/group/split. No material or
shape substitutions: ABO material may contain brand artifacts (Stone & Beam).
Use --listings-dir to check the full raw color field rather than only the lossy
items.csv color column. See docs/sean_mvp.md for the review workflow.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re

from sean_common import PAIR_FIELDS, REVIEW_FIELDS, pair, read_csv, stable_key, validate_items, write_csv, write_json

# Family aliases prevent synonym swaps. Longest phrases win at each position.
ALIASES = {
    'black': ['black'], 'white': ['white', 'ivory', 'cream', 'off white', 'off-white'],
    'gray': ['gray', 'grey', 'light gray', 'light grey', 'dark gray', 'dark grey'],
    'blue': ['blue', 'navy', 'navy blue', 'light blue', 'dark blue'],
    'red': ['red', 'burgundy', 'wine red'], 'green': ['green', 'dark green', 'light green'],
    'yellow': ['yellow'], 'pink': ['pink', 'light pink'], 'purple': ['purple'],
    'orange': ['orange'], 'brown': ['brown', 'dark brown', 'light brown', 'chocolate brown'],
    'beige': ['beige', 'tan'], 'silver': ['silver'], 'gold': ['gold', 'golden'],
}
FAMILY = {alias: family for family, aliases in ALIASES.items() for alias in aliases}
COLOR = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(x) for x in sorted(FAMILY, key=lambda x: (-len(x), x))) + r')(?!\w)', re.I)
AMBIGUOUS = re.compile(r'\b(multi[ -]?colo[u]?r(?:ed)?|two[ -]?tone|dual[ -]?tone|bi[ -]?colo[u]?r|assorted|rainbow|floral|striped|swatch)\b', re.I)
TARGETS = ['red', 'blue', 'green', 'yellow']
# Deliberately conservative near-color exclusions, including broad perceptual neighbors.
EXCLUDE = {'red': {'red', 'pink', 'purple', 'orange', 'brown'},
           'blue': {'blue', 'purple', 'green', 'gray', 'black'},
           'green': {'green', 'blue', 'yellow'},
           'yellow': {'yellow', 'orange', 'beige', 'gold', 'brown', 'white'}}


def raw_colors(listings_dir, wanted):
    result = {}
    for path in sorted(Path(listings_dir).glob('listings_*.json.gz')):
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            for line in f:
                row = json.loads(line)
                if row.get('item_id') in wanted:
                    result[row['item_id']] = row.get('color', [])
    if not result:
        raise ValueError('No matching raw listings found; check --listings-dir')
    return result


def raw_color_safe(entries):
    english = [e for e in entries if e.get('language_tag') == 'en_US']
    # More than one entry/value is not evidence of a single-color item.
    if len(english) != 1:
        return False
    entry = english[0]
    value = entry.get('value', '').strip().lower()
    std = entry.get('standardized_values', [])
    return (value in FAMILY and len(std) <= 1 and
            all(str(s).strip().lower() in FAMILY and FAMILY[str(s).strip().lower()] == FAMILY[value] for s in std))


def make_candidates(items, seed=42, raw=None):
    validate_items(items)
    image_freq = Counter(it['image_path'] for it in items)
    candidates, audit, skipped = [], [], []
    for it in sorted(items, key=lambda r: r['item_id']):
        reason = ''
        color = it.get('color', '').strip().lower()
        matches = list(COLOR.finditer(it['title']))
        if image_freq[it['image_path']] > 4:
            reason = 'high_frequency_shared_image'
        elif raw is not None and not raw_color_safe(raw.get(it['item_id'], [])):
            reason = 'raw_color_missing_multivalue_or_ambiguous'
        elif color not in FAMILY:
            reason = 'metadata_color_not_in_conservative_vocabulary'
        elif AMBIGUOUS.search(it['title']):
            reason = 'title_multicolor_pattern_or_swatch'
        elif len(matches) != 1:
            reason = 'title_must_contain_exactly_one_known_color_span'
        elif FAMILY[matches[0].group().lower()] != FAMILY[color]:
            reason = 'title_metadata_color_disagree'
        if reason:
            skipped.append(dict(item_id=it['item_id'], split=it['split'], reason=reason))
            continue
        source_family = FAMILY[color]
        choices = [t for t in TARGETS if source_family not in EXCLUDE[t]]
        target = min(choices, key=lambda t: stable_key(seed, it['item_id'] + ':' + t))
        m = matches[0]
        old = m.group()
        replacement = target.upper() if old.isupper() else target.title() if old[0].isupper() else target
        text = it['title'][:m.start()] + replacement + it['title'][m.end():]
        p = pair(it, 'N3', text=text)
        candidates.append(p)
        audit.append(dict(p, text_item_id=it['item_id'], image_item_id=it['item_id'],
                          original_text=it['title'], attribute='color', old_value=old,
                          new_value=replacement, review_decision='', reason='', notes='',
                          group_id=it['group_id'], raw_color_checked=raw is not None))
    return candidates, audit, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--items-csv', required=True)
    ap.add_argument('--listings-dir', help='recommended: raw ABO metadata directory')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()
    items = read_csv(args.items_csv)
    raw = raw_colors(args.listings_dir, {r['item_id'] for r in items}) if args.listings_dir else None
    pairs, audit, skipped = make_candidates(items, args.seed, raw)
    out = Path(args.out_dir)
    write_csv(out / 'n3_candidates.csv', pairs, PAIR_FIELDS)
    write_csv(out / 'n3_audit.csv', audit, REVIEW_FIELDS + ['group_id', 'raw_color_checked'])
    write_csv(out / 'n3_skipped.csv', skipped, ['item_id', 'split', 'reason'])
    summary = dict(status='UNREVIEWED_CANDIDATES', seed=args.seed, items=len(items), candidates=len(pairs),
                   raw_color_checked=raw is not None, by_split=dict(Counter(p['split'] for p in pairs)),
                   skipped_by_reason=dict(Counter(r['reason'] for r in skipped)))
    write_json(out / 'n3_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
