"""Download and validate only images referenced by items/pairs CSV files.

python src/data/download_pair_images.py --csv docs/sean_mvp/ood_items.csv
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'negatives'))
from build_review import load_image
from sean_common import read_csv, write_json


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv', nargs='+', required=True)
    ap.add_argument('--image-root', default='data/images')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--manifest', default='data/processed/sean/image_downloads.json')
    args = ap.parse_args()
    paths = sorted({r['image_path'] for filename in args.csv for r in read_csv(filename)})
    failures = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for path, image, error in pool.map(lambda p: load_image(p, args.image_root), paths):
            if error:
                failures[path] = error
    summary = dict(checked=len(paths), failures=failures)
    write_json(args.manifest, summary)
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
