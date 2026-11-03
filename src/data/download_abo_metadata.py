"""Download the official ABO metadata needed by Sean's scripts; no image tar.

python src/data/download_abo_metadata.py --out-dir data/raw
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

BASE = 'https://amazon-berkeley-objects.s3.amazonaws.com/'


def download(key, root):
    path = Path(root) / key
    if path.exists() and path.stat().st_size:
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    with urllib.request.urlopen(BASE + key, timeout=90) as source, temporary.open('wb') as dest:
        while chunk := source.read(1024 * 1024):
            dest.write(chunk)
    temporary.replace(path)
    print('downloaded', key, flush=True)
    return str(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out-dir', default='data/raw')
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()
    keys = [f'listings/metadata/listings_{c}.json.gz' for c in '0123456789abcdef']
    keys.append('images/metadata/images.csv.gz')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda key: download(key, args.out_dir), keys))


if __name__ == '__main__':
    main()
