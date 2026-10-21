"""
Step 0: download raw ABO metadata from the public S3 bucket into data/raw/.
This is the input build_items.py and count_categories.py read from.

Pulls the 16 listings_*.json.gz shards (listings metadata, ~84MB total) and
images.csv.gz (image_id -> small-image path mapping, ~6MB). It does NOT
download the 3GB+ image archive - actual images are fetched on demand, per
selected item, by build_items.py.

Usage:
    python src/data/fetch_raw.py --out-dir data/raw
"""
import argparse
from pathlib import Path

import requests

BASE = "https://amazon-berkeley-objects.s3.amazonaws.com/"
LISTING_SHARDS = "0123456789abcdef"


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"skip (exists): {dest}")
        return
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"downloaded: {dest} ({len(resp.content) / 1e6:.1f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data/raw")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)

    download(BASE + "images/metadata/images.csv.gz", out_dir / "images/metadata/images.csv.gz")
    for h in LISTING_SHARDS:
        download(
            BASE + f"listings/metadata/listings_{h}.json.gz",
            out_dir / f"listings/metadata/listings_{h}.json.gz",
        )


if __name__ == "__main__":
    main()
