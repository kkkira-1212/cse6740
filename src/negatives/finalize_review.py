"""Summarize real human judgments; export only individually accepted N3 pairs.

No extrapolation of sample approval to the remaining unreviewed candidates.
Use --sample-csv to detect changed texts/images and incomplete review exports.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from sean_common import PAIR_FIELDS, read_csv, write_csv, write_json


def summarize(rows):
    result = {}
    for kind in sorted({r['neg_type'] for r in rows}):
        subset = [r for r in rows if r['neg_type'] == kind]
        count = Counter(r['review_decision'] or 'pending' for r in subset)
        judged = count['match'] + count['mismatch']
        result[kind] = dict(total=len(subset), counts=dict(count), determinate=judged,
                            false_negative_rate=count['match'] / judged if judged else None,
                            uncertain_rate=count['uncertain'] / len(subset),
                            denominator='match + mismatch; pending and uncertain excluded')
    return result


def finalize(reviews, sample, n3):
    def index(rows):
        ids = [r['pair_id'] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate pair_id')
        return {r['pair_id']: r for r in rows}
    review_map, sample_map, n3_map = index(reviews), index(sample), index(n3)
    if review_map.keys() != sample_map.keys():
        raise ValueError('review must contain exactly the sampled IDs; do not drop pending rows')
    approved = []
    for pair_id, row in review_map.items():
        original = sample_map[pair_id]
        for field in ['neg_type', 'split', 'category', 'text_item_id', 'image_item_id', 'image_path', 'text']:
            if row[field] != original[field]:
                raise ValueError('changed sampled data: ' + pair_id + '/' + field)
        if row['review_decision'] not in {'', 'mismatch', 'match', 'uncertain'}:
            raise ValueError('invalid decision: ' + pair_id)
        if row['neg_type'] == 'N3':
            p = n3_map[pair_id]
            if p['text'] != row['text'] or p['image_path'] != row['image_path']:
                raise ValueError('N3 candidates differ from review: ' + pair_id)
            if row['review_decision'] == 'mismatch':
                approved.append(p)
    return approved, summarize(reviews)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--review-csv', required=True)
    ap.add_argument('--sample-csv', required=True)
    ap.add_argument('--n3-candidates', required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    approved, summary = finalize(read_csv(args.review_csv), read_csv(args.sample_csv), read_csv(args.n3_candidates))
    out = Path(args.out_dir)
    write_csv(out / 'n3_approved.csv', approved, PAIR_FIELDS)
    write_json(out / 'review_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('individually approved N3 rows:', len(approved))


if __name__ == '__main__':
    main()
