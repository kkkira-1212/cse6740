"""
WP2: build the pairs table (pos + N1 random negatives + N2 same-category hard
negatives) from Kira's items table (src/data/build_items.py output).

Per title: one positive pair, one N1 pair, one N2 pair (pos:N1:N2 = 1:1:1).
`item_id`/`image_path` on a pair always refer to the product the IMAGE belongs
to; `text` is the title attached to it (for pos it's the same item's own
title; for negatives it's a different item's title paired onto this image).

N2 similarity uses a non-CLIP sentence encoder (all-MiniLM-L6-v2) over
en_US titles, scoped to the same product_type and the same split as the
text owner, excluding the text owner's own near-duplicate group.

Both N1 and N2 candidates are restricted to the text owner's own split (a
train item never gets a val/test image as its negative, and vice versa),
and are never allowed to reproduce an existing positive (image_path, text)
pair - this matters because a few main images are shared by many unrelated
items (ABO placeholder "no photo" stock images; see
_MAX_SHARED_IMAGE_FOR_GROUPING in build_items.py), so "different group_id"
alone doesn't guarantee a different, non-contradictory image.

Usage:
    python src/negatives/build_pairs.py \
        --items-csv data/processed/items.csv \
        --out-csv data/processed/pairs.csv \
        --spotcheck-csv docs/n1_n2_spotcheck_sample.csv
"""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import numpy as np


def load_items(items_csv):
    with open(items_csv, newline="") as f:
        return list(csv.DictReader(f))


def _build_pos_index(items):
    """Set of (image_path, text) combos already used as a positive pair -
    a negative must never reproduce one of these."""
    return {(it["image_path"], it["title"]) for it in items}


def _is_valid_negative(owner, candidate, pos_index):
    if candidate["group_id"] == owner["group_id"]:
        return False
    if candidate["split"] != owner["split"]:
        return False
    if candidate["image_path"] == owner["image_path"]:
        return False
    if (candidate["image_path"], owner["title"]) in pos_index:
        return False
    return True


def build_n1(items, seed=42):
    """For each item, a random image from a different group_id, same split."""
    rng = random.Random(seed)
    pos_index = _build_pos_index(items)
    by_split = defaultdict(list)
    for it in items:
        by_split[it["split"]].append(it)

    n1_image_for = {}
    skipped_no_candidate = 0
    for it in items:
        candidates = [c for c in by_split[it["split"]] if _is_valid_negative(it, c, pos_index)]
        if not candidates:
            skipped_no_candidate += 1
            continue
        n1_image_for[it["item_id"]] = rng.choice(candidates)
    if skipped_no_candidate:
        print(f"N1: {skipped_no_candidate} items had no valid same-split different-group candidate (skipped)")
    return n1_image_for


def build_n2(items, model_name="all-MiniLM-L6-v2", batch_size=256):
    """For each item, the most title-similar item in the same product_type
    and split, excluding its own near-duplicate group (non-CLIP sentence
    embeddings)."""
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    pos_index = _build_pos_index(items)
    model = SentenceTransformer(model_name)
    titles = [it["title"] for it in items]
    embeddings = model.encode(titles, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)

    by_pt = defaultdict(list)
    for idx, it in enumerate(items):
        by_pt[it["product_type"]].append(idx)

    n2_image_for = {}
    skipped_no_candidate = 0
    for pt, idxs in by_pt.items():
        sub_emb = embeddings[idxs]
        sims = cosine_similarity(sub_emb, sub_emb)
        for row, i in enumerate(idxs):
            owner = items[i]
            row_sims = sims[row].copy()
            for col, j in enumerate(idxs):
                if not _is_valid_negative(owner, items[j], pos_index):
                    row_sims[col] = -np.inf
            best_col = int(np.argmax(row_sims))
            if row_sims[best_col] == -np.inf:
                skipped_no_candidate += 1
                continue
            n2_image_for[owner["item_id"]] = items[idxs[best_col]]
    print(f"N2: {skipped_no_candidate} items had no valid same-split same-category candidate (skipped)")
    return n2_image_for


def write_pairs(items, n1_image_for, n2_image_for, out_csv):
    fields = ["pair_id", "item_id", "image_path", "text", "label", "neg_type", "category", "year", "split"]
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    n_pos = n_n1 = n_n2 = 0
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for it in items:
            writer.writerow(
                {
                    "pair_id": f"{it['item_id']}_pos",
                    "item_id": it["item_id"],
                    "image_path": it["image_path"],
                    "text": it["title"],
                    "label": 1,
                    "neg_type": "pos",
                    "category": it["product_type"],
                    "year": "",
                    "split": it["split"],
                }
            )
            n_pos += 1

            neg_img = n1_image_for.get(it["item_id"])
            if neg_img is not None:
                writer.writerow(
                    {
                        "pair_id": f"{it['item_id']}_N1",
                        "item_id": neg_img["item_id"],
                        "image_path": neg_img["image_path"],
                        "text": it["title"],
                        "label": 0,
                        "neg_type": "N1",
                        "category": it["product_type"],
                        "year": "",
                        "split": it["split"],
                    }
                )
                n_n1 += 1

            neg_img = n2_image_for.get(it["item_id"])
            if neg_img is not None:
                writer.writerow(
                    {
                        "pair_id": f"{it['item_id']}_N2",
                        "item_id": neg_img["item_id"],
                        "image_path": neg_img["image_path"],
                        "text": it["title"],
                        "label": 0,
                        "neg_type": "N2",
                        "category": it["product_type"],
                        "year": "",
                        "split": it["split"],
                    }
                )
                n_n2 += 1
    print(f"wrote {out_csv}: pos={n_pos} N1={n_n1} N2={n_n2}")


def write_spotcheck_sample(items, n1_image_for, n2_image_for, out_csv, n_per_type=20, seed=7):
    rng = random.Random(seed)
    rows = []
    for neg_type, mapping in (("N1", n1_image_for), ("N2", n2_image_for)):
        candidates = [it for it in items if it["item_id"] in mapping]
        sample = rng.sample(candidates, min(n_per_type, len(candidates)))
        for it in sample:
            neg = mapping[it["item_id"]]
            rows.append(
                {
                    "neg_type": neg_type,
                    "text_item_id": it["item_id"],
                    "title": it["title"],
                    "image_item_id": neg["item_id"],
                    "image_path": neg["image_path"],
                    "actually_a_match": "",  # for human reviewer to fill in (y/n)
                }
            )
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["neg_type", "text_item_id", "title", "image_item_id", "image_path", "actually_a_match"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out_csv}: {len(rows)} rows for manual spot-check")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--spotcheck-csv", required=True)
    args = ap.parse_args()

    items = load_items(args.items_csv)
    print(f"loaded {len(items)} items")

    n1_image_for = build_n1(items)
    n2_image_for = build_n2(items)

    write_pairs(items, n1_image_for, n2_image_for, args.out_csv)
    write_spotcheck_sample(items, n1_image_for, n2_image_for, args.spotcheck_csv)


if __name__ == "__main__":
    main()
