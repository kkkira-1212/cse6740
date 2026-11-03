"""WP5 provisional threshold check; Aaron's WP4 remains the shared evaluator."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score


def metrics(rows, threshold):
    y = np.array([int(r['label']) for r in rows])
    s = np.array([r['score'] for r in rows])
    pred = s >= threshold
    tpr = float(pred[y == 1].mean())
    tnr = float((~pred[y == 0]).mean())
    return dict(n=len(rows), accuracy=float((pred == y).mean()),
                auc=float(roc_auc_score(y, s)), positive_recall=tpr,
                negative_recall=tnr, balanced_accuracy=(tpr + tnr) / 2,
                negatives_by_type={t: dict(n=sum(r['neg_type'] == t for r in rows),
                    recall=float(np.mean([r['score'] < threshold for r in rows if r['neg_type'] == t])))
                    for t in sorted({r['neg_type'] for r in rows} - {'pos'})})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pairs-csv', default='docs/mini_version/pairs.csv')
    ap.add_argument('--scores-csv', default='scores/clip_vit_b32_zero_shot.csv')
    ap.add_argument('--out-json', default='scores/clip_vit_b32_zero_shot_calibration.json')
    args = ap.parse_args()
    with open(args.pairs_csv, newline='') as f:
        rows = list(csv.DictReader(f))
    with open(args.scores_csv, newline='') as f:
        scores = list(csv.DictReader(f))
    for data in (rows, scores):
        if len({r['pair_id'] for r in data}) != len(data):
            raise ValueError('duplicate pair_id')
    lookup = {r['pair_id']: float(r['score']) for r in scores}
    if set(lookup) != {r['pair_id'] for r in rows}:
        raise ValueError('pair and score IDs differ')
    for row in rows:
        row['score'] = lookup[row['pair_id']]
        if not np.isfinite(row['score']) or row['label'] not in ('0', '1'):
            raise ValueError('invalid score or label')
    val = [r for r in rows if r['split'] == 'val']
    test = [r for r in rows if r['split'] == 'test']
    if any({r['label'] for r in subset} != {'0', '1'} for subset in (val, test)):
        raise ValueError('val and test must both contain positive and negative examples')
    values = np.unique([r['score'] for r in val])
    candidates = np.append(values, np.nextafter(values[-1], np.inf))
    # Each unique validation score represents a possible decision partition.
    # Ties select the smallest threshold (higher positive recall).
    correct = [sum((r['score'] >= t) == (r['label'] == '1') for r in val) for t in candidates]
    threshold = float(candidates[int(np.argmax(correct))])
    result = dict(selection_split='val', objective='accuracy', rule='score >= threshold',
                  tie_break='smallest threshold among maximum-accuracy candidates',
                  threshold=threshold, val=metrics(val, threshold), test=metrics(test, threshold),
                  input_sha256={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in (args.pairs_csv, args.scores_csv)},
                  limitation='Provisional WP5 check: two image paths cross splits; N2 labels remain noisy.')
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
