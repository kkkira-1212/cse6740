"""Thin IO helpers for raw ABO listings/images metadata. No filtering logic here."""
import gzip
import json
from pathlib import Path


def iter_listings(listings_dir):
    """Yield raw listing dicts from all listings_*.json.gz shards, in a stable shard order."""
    for path in sorted(Path(listings_dir).glob("listings_*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)


def load_image_path_map(images_csv_gz):
    """Return dict: image_id -> relative path under images/small/, e.g. '14/14fe8812.jpg'."""
    mapping = {}
    with gzip.open(images_csv_gz, "rt", encoding="utf-8") as f:
        next(f)  # header: image_id,height,width,path
        for line in f:
            image_id, _height, _width, path = line.rstrip("\n").split(",", 3)
            mapping[image_id] = path
    return mapping


def en_us_value(entries):
    """First en_US 'value' from a language-tagged list field, or None."""
    if not entries:
        return None
    for e in entries:
        if e.get("language_tag") == "en_US":
            return e.get("value")
    return None


def en_us_standardized(entries):
    """(display_value, standardized_value) for the en_US entry of a color/material field."""
    if not entries:
        return None, None
    for e in entries:
        if e.get("language_tag") == "en_US":
            std = e.get("standardized_values")
            return e.get("value"), (std[0] if std else None)
    return None, None


def first_node_name(nodes, prefer_prefix=None):
    """Pick a node_name from the 'node' list, preferring one starting with prefer_prefix."""
    if not nodes:
        return None
    if prefer_prefix:
        for n in nodes:
            name = n.get("node_name")
            if name and name.startswith(prefer_prefix):
                return name
    return nodes[0].get("node_name")
