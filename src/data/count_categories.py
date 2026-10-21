"""
WP1 step 1 deliverable: count ABO listings by product_type / top-level category,
restricted to items with an en_US title and a main image, and measure how often
the standardized color/material value actually appears in the title (this caps
how many N3 attribute-swap negatives Sean can build later).

Usage:
    python src/data/count_categories.py \
        --listings-dir data/raw/listings/metadata \
        --out-csv data/processed/category_counts.csv \
        --out-md docs/category_counts.md
"""
import argparse
import csv
from collections import Counter

from abo_io import en_us_standardized, en_us_value, first_node_name, iter_listings


_GENERIC_WRAPPERS = {"Categories", "Departments", "Products"}


def top_level(node_name):
    """First meaningful path segment, skipping generic wrappers like '/Categories/...'."""
    if not node_name:
        return None
    parts = [p for p in node_name.split("/") if p]
    if not parts:
        return None
    if parts[0] in _GENERIC_WRAPPERS and len(parts) > 1:
        return parts[1]
    return parts[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings-dir", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    pt_counts = Counter()
    pt_color_title_hits = Counter()
    pt_material_title_hits = Counter()
    top_level_counts = Counter()
    total_records = 0
    total_en_us_with_image = 0

    for rec in iter_listings(args.listings_dir):
        total_records += 1
        title = en_us_value(rec.get("item_name"))
        if not title or "main_image_id" not in rec:
            continue
        total_en_us_with_image += 1

        pt = rec.get("product_type", [{}])[0].get("value", "UNKNOWN")
        pt_counts[pt] += 1

        node_name = first_node_name(rec.get("node"))
        top_level_counts[top_level(node_name)] += 1

        title_lower = title.lower()
        color_val, color_std = en_us_standardized(rec.get("color"))
        color_check = color_std or color_val  # ABO always has standardized color; val is the fallback
        if color_check and color_check.lower() in title_lower:
            pt_color_title_hits[pt] += 1
        mat_val, mat_std = en_us_standardized(rec.get("material"))
        mat_check = mat_std or mat_val  # ABO never standardizes material, so this is always the raw value
        if mat_check and mat_check.lower() in title_lower:
            pt_material_title_hits[pt] += 1

    rows = []
    for pt, count in pt_counts.most_common():
        rows.append(
            {
                "product_type": pt,
                "count_en_us_with_image": count,
                "color_std_in_title": pt_color_title_hits.get(pt, 0),
                "material_std_in_title": pt_material_title_hits.get(pt, 0),
            }
        )

    with open(args.out_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["product_type", "count_en_us_with_image", "color_std_in_title", "material_std_in_title"]
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(args.out_md, "w") as f:
        f.write("# ABO category counts (en_US title + main image present)\n\n")
        f.write(f"Total raw listing records: {total_records}\n\n")
        f.write(f"Total with en_US title + main_image_id: {total_en_us_with_image}\n\n")
        f.write("## Top-level category (from `node` path), top 20\n\n")
        f.write("| top_level_category | count |\n|---|---|\n")
        for name, count in top_level_counts.most_common(20):
            f.write(f"| {name} | {count} |\n")
        f.write("\n## product_type, top 40\n\n")
        f.write("| product_type | count | color_std_in_title | material_std_in_title |\n|---|---|---|---|\n")
        for row in rows[:40]:
            f.write(
                f"| {row['product_type']} | {row['count_en_us_with_image']} | "
                f"{row['color_std_in_title']} | {row['material_std_in_title']} |\n"
            )
        f.write("\nFull table: `data/processed/category_counts.csv` (not committed, regenerate locally).\n")

    print(f"wrote {args.out_csv} and {args.out_md}")
    print(f"total_records={total_records} total_en_us_with_image={total_en_us_with_image}")


if __name__ == "__main__":
    main()
