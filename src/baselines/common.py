"""Shared IO helpers for the WP7/WP8 baselines (pairs in, pair_id,score out)."""
import csv
from pathlib import Path

REQUIRED = ("pair_id", "image_path", "text")


def read_pairs(path, splits=None, limit=None):
    """Read a pairs CSV (docs/schema.md), optionally keeping only some splits.

    Order is preserved so score files line up with the input table.
    """
    with open(path, newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not set(REQUIRED).issubset(rows[0]):
        raise ValueError(f"{path}: needs columns {list(REQUIRED)} and at least one row")
    if splits:
        wanted = set(splits)
        rows = [row for row in rows if row.get("split") in wanted]
    if limit:
        rows = rows[:limit]
    ids = [row["pair_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate pair_id")
    for row in rows:
        if not all(row.get(key) for key in REQUIRED):
            raise ValueError(f"{path}: empty pair_id, image_path or text in {row.get('pair_id')}")
    return rows


def write_scores(path, rows, scores):
    """Write pair_id,score (higher = more likely a match) in input order."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("pair_id", "score"))
        for row in rows:
            if row["pair_id"] in scores:
                writer.writerow((row["pair_id"], f"{scores[row['pair_id']]:.8f}"))
    return out


def text_item_id(row):
    """Text-source item id: pair_id is <text_item_id>_<neg_type> per schema."""
    suffix = f"_{row['neg_type']}"
    pair_id = row["pair_id"]
    return pair_id[: -len(suffix)] if pair_id.endswith(suffix) else pair_id


def pick_device(requested):
    """Resolve auto -> cuda / mps / cpu, failing loudly if the request is impossible."""
    import torch

    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    if requested == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but not available")
    return requested
