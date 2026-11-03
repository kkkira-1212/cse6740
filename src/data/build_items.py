"""
WP1: build the furniture items table (mini version) from raw ABO listings.

Steps: filter to furniture product_types with an en_US title + main image ->
resolve image paths -> download small images -> group near-duplicates
(same main image, or same product_type + near-identical title) -> split by
group_id into train/val/test, keeping each group inside a single split.

Usage:
    python src/data/build_items.py \
        --listings-dir data/raw/listings/metadata \
        --images-csv data/raw/images/metadata/images.csv.gz \
        --images-out data/images/small \
        --out-csv data/processed/items.csv \
        --out-counts-csv docs/furniture_category_counts.csv
"""
import argparse
import csv
import random
import re
from pathlib import Path

import requests

from abo_io import en_us_standardized, en_us_value, first_node_name, iter_listings, load_image_path_map

# Core furniture product_types, picked from docs/category_counts.csv: real seating/sleeping/
# storage/surface furniture. Excludes HOME_FURNITURE_AND_DECOR and HOME_BED_AND_BATH (catch-all /
# linens, not furniture itself) and FURNITURE_COVER (a slipcover accessory, not the furniture).
FURNITURE_TYPES = {
    "CHAIR", "SOFA", "TABLE", "STOOL_SEATING", "OTTOMAN", "HEADBOARD", "BED", "BED_FRAME",
    "SHELF", "DESK", "CABINET", "DRESSER", "BENCH", "FURNITURE", "AV_FURNITURE", "BEAN_BAG_CHAIR",
}

_SIZE_WORDS = re.compile(
    r"\b(x-?small|small|medium|large|x-?large|xl|xxl|twin|full|queen|king|california king|"
    r"\d+(\.\d+)?\s*(in|inch|inches|cm|ft|feet|\")|set of \d+|\d+\s*-?\s*(pack|piece|pc))\b",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[,\-–—/()\.]")
_WS = re.compile(r"\s+")

S3_BASE = "https://amazon-berkeley-objects.s3.amazonaws.com/images/small/"


def normalize_title(title, color, material):
    t = title.lower()
    if color:
        t = t.replace(color.lower(), " ")
    if material:
        t = t.replace(material.lower(), " ")
    t = _SIZE_WORDS.sub(" ", t)
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    return t


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def extract_items(listings_dir):
    seen_item_ids = set()
    items = []
    for rec in iter_listings(listings_dir):
        item_id = rec.get("item_id")
        if item_id in seen_item_ids:
            continue  # same item_id shouldn't repeat across shards; guard anyway
        pt = rec.get("product_type", [{}])[0].get("value")
        if pt not in FURNITURE_TYPES:
            continue
        title = en_us_value(rec.get("item_name"))
        main_image_id = rec.get("main_image_id")
        if not title or not main_image_id:
            continue
        if "swatch" in title.lower():
            continue  # fabric swatch listings, mislabeled under furniture product_types
        seen_item_ids.add(item_id)

        color_val, color_std = en_us_standardized(rec.get("color"))
        color = color_std or color_val
        mat_val, _mat_std = en_us_standardized(rec.get("material"))
        material = mat_val

        node_name = first_node_name(rec.get("node"), prefer_prefix="/Categories/Furniture")

        items.append(
            {
                "item_id": item_id,
                "title": title,
                "product_type": pt,
                "node": node_name or "",
                "color": color or "",
                "material": material or "",
                "main_image_id": main_image_id,
            }
        )
    return items


# A handful of main_image_ids are generic "no photo" placeholders ABO reuses across dozens of
# unrelated products (a chair, a desk, a bed all sharing one stock image). Genuine duplicate-shot
# clusters (same item in a few sizes/colors reusing one photo) top out around 4 items, so treat
# anything shared by more than this as a placeholder and skip it as a grouping signal.
_MAX_SHARED_IMAGE_FOR_GROUPING = 4


def group_items(items):
    uf = UnionFind()
    by_main_image = {}
    by_title_key = {}
    by_exact_title = {}

    image_freq = {}
    for it in items:
        image_freq[it["main_image_id"]] = image_freq.get(it["main_image_id"], 0) + 1

    for it in items:
        uf.find(it["item_id"])  # register

        mi = it["main_image_id"]
        if image_freq[mi] > _MAX_SHARED_IMAGE_FOR_GROUPING:
            continue  # likely a placeholder image, not a real duplicate signal
        if mi in by_main_image:
            uf.union(it["item_id"], by_main_image[mi])
        else:
            by_main_image[mi] = it["item_id"]

        norm = normalize_title(it["title"], it["color"], it["material"])
        key = (it["product_type"], norm)
        if len(norm) > 3:
            if key in by_title_key:
                uf.union(it["item_id"], by_title_key[key])
            else:
                by_title_key[key] = it["item_id"]

        # Re-listed duplicates sometimes carry a wrong/inconsistent color or material field
        # (title still says "Denim Blue", color field says "Beige"), which breaks the
        # normalized-title match above. An exact, byte-for-byte identical title is on its own
        # strong enough evidence of the same real product to merge on, independent of color/material.
        exact_key = (it["product_type"], it["title"].strip().lower())
        if exact_key in by_exact_title:
            uf.union(it["item_id"], by_exact_title[exact_key])
        else:
            by_exact_title[exact_key] = it["item_id"]

    root_to_group_id = {}
    for it in items:
        root = uf.find(it["item_id"])
        if root not in root_to_group_id:
            root_to_group_id[root] = f"g{len(root_to_group_id):06d}"
        it["group_id"] = root_to_group_id[root]
    return items


def assign_splits(items, seed=42, ratios=(0.8, 0.1, 0.1)):
    group_ids = sorted({it["group_id"] for it in items})
    rng = random.Random(seed)
    rng.shuffle(group_ids)
    n = len(group_ids)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    split_of_group = {}
    for i, gid in enumerate(group_ids):
        if i < n_train:
            split_of_group[gid] = "train"
        elif i < n_train + n_val:
            split_of_group[gid] = "val"
        else:
            split_of_group[gid] = "test"
    for it in items:
        it["split"] = split_of_group[it["group_id"]]
    return items


def _download_one(rel_path, out_dir):
    local_path = out_dir / rel_path
    if local_path.exists():
        return rel_path, None
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(S3_BASE + rel_path, timeout=20)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)
        return rel_path, None
    except Exception as e:
        return rel_path, str(e)


def resolve_and_download_images(items, images_csv, images_out_dir, workers=16):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    path_map = load_image_path_map(images_csv)
    out_dir = Path(images_out_dir)

    kept = []
    missing_mapping = 0
    rel_path_by_item = {}
    for it in items:
        rel_path = path_map.get(it["main_image_id"])
        if rel_path is None:
            missing_mapping += 1
            continue
        rel_path_by_item[it["item_id"]] = rel_path

    failures = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_download_one, rel_path, out_dir): item_id
            for item_id, rel_path in rel_path_by_item.items()
        }
        for fut in as_completed(futures):
            item_id = futures[fut]
            rel_path, err = fut.result()
            if err:
                failures[item_id] = err

    for it in items:
        rel_path = rel_path_by_item.get(it["item_id"])
        if rel_path is None or it["item_id"] in failures:
            continue
        it["image_path"] = f"small/{rel_path}"
        kept.append(it)

    print(
        f"resolved images: kept={len(kept)} missing_mapping={missing_mapping} "
        f"download_failures={len(failures)}"
    )
    for item_id, err in list(failures.items())[:5]:
        print(f"  download failed for {item_id}: {err}")
    return kept


def write_items_csv(items, out_csv):
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    fields = ["item_id", "title", "image_path", "product_type", "node", "color", "material", "group_id", "split"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for it in items:
            writer.writerow({k: it.get(k, "") for k in fields})


def write_counts_csv(items, out_counts_csv):
    from collections import Counter

    pt_counts = Counter(it["product_type"] for it in items)
    split_counts = Counter(it["split"] for it in items)
    Path(out_counts_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_counts_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["product_type", "count"])
        for pt, c in pt_counts.most_common():
            writer.writerow([pt, c])
        writer.writerow([])
        writer.writerow(["split", "count"])
        for s, c in split_counts.items():
            writer.writerow([s, c])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings-dir", required=True)
    ap.add_argument("--images-csv", required=True)
    ap.add_argument("--images-out", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-counts-csv", required=True)
    ap.add_argument("--max-items", type=int, default=None, help="cap for a quick smoke run")
    args = ap.parse_args()

    items = extract_items(args.listings_dir)
    print(f"furniture items with en_US title + main_image_id: {len(items)}")
    if args.max_items:
        items = items[: args.max_items]

    items = group_items(items)
    n_groups = len({it["group_id"] for it in items})
    print(f"near-duplicate groups: {n_groups}")

    items = assign_splits(items)
    items = resolve_and_download_images(items, args.images_csv, args.images_out)

    write_items_csv(items, args.out_csv)
    write_counts_csv(items, args.out_counts_csv)
    print(f"wrote {args.out_csv} ({len(items)} rows)")


if __name__ == "__main__":
    main()
