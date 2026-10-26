"""Score image-title pairs with the original zero-shot CLIP ViT-B/32."""
import argparse
import csv
import json
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_ID = "openai/clip-vit-base-patch32"
MODEL_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"


def read_pairs(path, limit=None):
    with open(path, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"pair_id", "image_path", "text"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"pairs CSV needs {sorted(required)} and at least one row")
    rows = rows[:limit] if limit else rows
    ids = [row["pair_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate pair_id in input")
    if any(not all(row[key] for key in required) for row in rows):
        raise ValueError("empty pair_id, image_path, or text")
    return rows


def encode_images(paths, root, processor, model, device, batch_size):
    vectors = {}
    for start in range(0, len(paths), batch_size):
        batch = paths[start:start + batch_size]
        images = []
        for rel in batch:
            path = root / rel
            if not path.is_file():
                raise FileNotFoundError(path)
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        inputs = processor(images=images, return_tensors="pt").to(device)
        with torch.inference_mode():
            features = model.get_image_features(**inputs)
            features = torch.nn.functional.normalize(features.pooler_output, dim=-1)
        vectors.update(zip(batch, features.cpu().float().numpy()))
        print(f"images {min(start + batch_size, len(paths))}/{len(paths)}", flush=True)
    return vectors


def encode_texts(texts, processor, model, device, batch_size):
    vectors = {}
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        inputs = processor(text=batch, padding=True, truncation=True, max_length=77, return_tensors="pt").to(device)
        with torch.inference_mode():
            features = model.get_text_features(**inputs)
            features = torch.nn.functional.normalize(features.pooler_output, dim=-1)
        vectors.update(zip(batch, features.cpu().float().numpy()))
        print(f"texts {min(start + batch_size, len(texts))}/{len(texts)}", flush=True)
    return vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs-csv", default="docs/mini_version/pairs.csv")
    parser.add_argument("--image-root", default="data/images")
    parser.add_argument("--out-csv", default="scores/clip_vit_b32_zero_shot.csv")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), default="auto")
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    args = parser.parse_args()
    if args.batch_size < 1 or (args.limit is not None and args.limit < 1):
        parser.error("batch-size and limit must be positive")

    rows = read_pairs(args.pairs_csv, args.limit)
    device = "mps" if args.device == "auto" and torch.backends.mps.is_available() else args.device
    if device == "auto":
        device = "cpu"
    if device == "mps" and not torch.backends.mps.is_available():
        parser.error("MPS unavailable in this process; use --device cpu or run outside the sandbox")
    print(f"model={MODEL_ID}@{args.model_revision} device={device} pairs={len(rows)}", flush=True)
    processor = CLIPProcessor.from_pretrained(MODEL_ID, revision=args.model_revision)
    model = CLIPModel.from_pretrained(MODEL_ID, revision=args.model_revision).to(device).eval()
    paths = list(dict.fromkeys(row["image_path"] for row in rows))
    texts = list(dict.fromkeys(row["text"] for row in rows))
    image_features = encode_images(paths, Path(args.image_root), processor, model, device, args.batch_size)
    text_features = encode_texts(texts, processor, model, device, args.batch_size)

    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("pair_id", "score"))
        for row in rows:
            score = float(image_features[row["image_path"]] @ text_features[row["text"]])
            writer.writerow((row["pair_id"], f"{score:.8f}"))
    print(f"wrote {len(rows)} scores to {out}")


if __name__ == "__main__":
    main()
