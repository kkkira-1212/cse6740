"""WP8: more zero-shot baselines, scored in the shared pair_id,score format.

Two scoring families:
  dual   image and title are encoded separately; score = cosine similarity
         (the same recipe as Jack's WP5 CLIP ViT-B/32, with bigger or
         different encoders)
  itm    a fusion model reads image and title together through its
         image-text matching head; score = P(match) from the 2-way softmax

No training and no label use here; the threshold is chosen on val by the
shared evaluator (src/eval/eval.py), exactly as for WP5.

Example:
  python src/baselines/zero_shot_baselines.py --model siglip-b16
  python src/eval/eval.py --pairs-csv docs/mini_version/pairs.csv \
    --scores-csv scores/siglip_b16_zero_shot.csv --drop-cross-split-images --r-at-1
"""
import argparse
import json
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

from common import pick_device, read_pairs, write_scores

# Model ids are public Hugging Face checkpoints. Pin a revision with
# --revision once a run is final, and record it in the README.
MODELS = {
    "clip-l14": dict(hf_id="openai/clip-vit-large-patch14", family="dual", text_kwargs={"max_length": 77}),
    "siglip-b16": dict(hf_id="google/siglip-base-patch16-224", family="dual",
                       text_kwargs={"padding": "max_length", "max_length": 64}),
    "siglip2-b16": dict(hf_id="google/siglip2-base-patch16-224", family="dual",
                        text_kwargs={"padding": "max_length", "max_length": 64}),
    "align-b": dict(hf_id="kakaobrain/align-base", family="dual",
                    text_kwargs={"padding": "max_length", "max_length": 64}),
    "blip-itm-b": dict(hf_id="Salesforce/blip-itm-base-coco", family="itm", loader="blip"),
    "blip2-itm-g": dict(hf_id="Salesforce/blip2-itm-vit-g", family="itm", loader="blip2"),
}


def load_images(paths, root):
    images = []
    for rel in paths:
        path = Path(root) / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        with Image.open(path) as image:
            images.append(image.convert("RGB"))
    return images


def as_embedding(output):
    """get_*_features returns a tensor in some transformers versions and a ModelOutput in others."""
    if isinstance(output, torch.Tensor):
        return output
    for name in ("image_embeds", "text_embeds", "pooler_output"):
        value = getattr(output, name, None)
        if value is not None:
            return value
    raise TypeError(f"cannot find an embedding in {type(output).__name__}")


def load_model(spec, revision, device):
    if spec["family"] == "dual":
        model = AutoModel.from_pretrained(spec["hf_id"], revision=revision)
    elif spec["loader"] == "blip":
        from transformers import BlipForImageTextRetrieval
        model = BlipForImageTextRetrieval.from_pretrained(spec["hf_id"], revision=revision)
    else:
        from transformers import Blip2ForImageTextRetrieval
        model = Blip2ForImageTextRetrieval.from_pretrained(spec["hf_id"], revision=revision)
    processor = AutoProcessor.from_pretrained(spec["hf_id"], revision=revision)
    return model.to(device).eval(), processor


def score_dual(rows, model, processor, spec, args, device):
    paths = list(dict.fromkeys(r["image_path"] for r in rows))
    texts = list(dict.fromkeys(r["text"] for r in rows))
    image_vec, text_vec = {}, {}
    for start in range(0, len(paths), args.batch_size):
        batch = paths[start:start + args.batch_size]
        inputs = processor(images=load_images(batch, args.image_root), return_tensors="pt").to(device)
        with torch.inference_mode():
            feats = as_embedding(model.get_image_features(**inputs))
        feats = torch.nn.functional.normalize(feats.float(), dim=-1).cpu()
        image_vec.update(zip(batch, feats))
        print(f"images {min(start + args.batch_size, len(paths))}/{len(paths)}", flush=True)
    text_kwargs = {"padding": True, "truncation": True, **spec.get("text_kwargs", {})}
    for start in range(0, len(texts), args.batch_size):
        batch = texts[start:start + args.batch_size]
        inputs = processor(text=batch, return_tensors="pt", **text_kwargs).to(device)
        with torch.inference_mode():
            feats = as_embedding(model.get_text_features(**inputs))
        feats = torch.nn.functional.normalize(feats.float(), dim=-1).cpu()
        text_vec.update(zip(batch, feats))
        print(f"texts {min(start + args.batch_size, len(texts))}/{len(texts)}", flush=True)
    return {r["pair_id"]: float(image_vec[r["image_path"]] @ text_vec[r["text"]]) for r in rows}


def score_itm(rows, model, processor, spec, args, device):
    scores = {}
    for start in range(0, len(rows), args.batch_size):
        batch = rows[start:start + args.batch_size]
        inputs = processor(images=load_images([r["image_path"] for r in batch], args.image_root),
                           text=[r["text"] for r in batch], padding=True, truncation=True,
                           return_tensors="pt").to(device)
        with torch.inference_mode():
            if spec["loader"] == "blip":
                out = model(**inputs, use_itm_head=True)
            else:
                out = model(**inputs, use_image_text_matching_head=True)
        logits = getattr(out, "itm_score", None)
        if logits is None:
            logits = out.logits_per_image
        probs = torch.softmax(logits.float(), dim=-1)[:, 1].cpu().tolist()
        scores.update((r["pair_id"], p) for r, p in zip(batch, probs))
        print(f"pairs {min(start + args.batch_size, len(rows))}/{len(rows)}", flush=True)
    return scores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=sorted(MODELS), required=True)
    ap.add_argument("--pairs-csv", default="docs/mini_version/pairs.csv")
    ap.add_argument("--image-root", default="data/images")
    ap.add_argument("--splits", nargs="+", default=["val", "test"],
                    help="splits to score; the evaluator needs val (threshold) and test")
    ap.add_argument("--limit", type=int, help="smoke test on the first N pairs")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--device", choices=("auto", "cuda", "mps", "cpu"), default="auto")
    ap.add_argument("--revision", default="main", help="Hugging Face revision (commit hash) to pin")
    ap.add_argument("--out-csv", help="default: scores/<model>_zero_shot.csv")
    args = ap.parse_args()

    spec = MODELS[args.model]
    rows = read_pairs(args.pairs_csv, splits=args.splits, limit=args.limit)
    device = pick_device(args.device)
    out_csv = args.out_csv or f"scores/{args.model.replace('-', '_')}_zero_shot.csv"
    print(f"model={spec['hf_id']}@{args.revision} family={spec['family']} device={device} pairs={len(rows)}",
          flush=True)

    start = time.monotonic()
    model, processor = load_model(spec, args.revision, device)
    scorer = score_dual if spec["family"] == "dual" else score_itm
    scores = scorer(rows, model, processor, spec, args, device)
    elapsed = time.monotonic() - start

    out = write_scores(out_csv, rows, scores)
    meta = {
        "model_key": args.model, "hf_id": spec["hf_id"], "revision": args.revision, "family": spec["family"],
        "score": "cosine similarity" if spec["family"] == "dual" else "softmax P(match) from ITM head",
        "n_params": sum(p.numel() for p in model.parameters()), "device": device,
        "seconds": round(elapsed, 1), "pairs_csv": args.pairs_csv, "splits": args.splits, "n_pairs": len(rows),
        "torch": torch.__version__, "transformers": __import__("transformers").__version__,
    }
    Path(out).with_name(Path(out).stem + "_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {len(scores)} scores to {out} ({meta['n_params'] / 1e6:.0f}M params, {elapsed:.0f}s)")


if __name__ == "__main__":
    main()
