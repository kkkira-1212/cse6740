"""Train CLIP LoRA or all parameters on fixed-image v2, selecting on validation only.

Image-to-text InfoNCE uses B original and B explicitly negative titles.
Text-to-image InfoNCE uses only the B original titles and B original images.
Identical tokenized positive titles are treated as multiple known positives,
including duplicate title donor occurrences in the explicit-negative columns.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import transformers
import peft
from PIL import Image
from peft import LoraConfig, PeftModel, get_peft_model
from sklearn.metrics import roc_auc_score
from transformers import CLIPModel, CLIPProcessor

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read_dataset(path, version):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len({r["pair_id"] for r in rows}) != len(rows):
        raise ValueError("empty dataset or duplicate pair IDs")
    groups, image_splits, group_splits = defaultdict(list), defaultdict(set), defaultdict(set)
    for row in rows:
        if row["dataset_version"] != version or row["split"] not in {"train", "val", "test"}:
            raise ValueError("unexpected dataset version or split")
        if row["label"] not in {"0", "1"} or (row["label"] == "1") != (row["neg_type"] == "pos"):
            raise ValueError("label/negative type contradiction")
        groups[row["anchor_item_id"]].append(row)
        image_splits[row["image_path"]].add(row["split"])
        group_splits[row["anchor_group_id"]].add(row["split"])
    if any(len(s) != 1 for s in list(image_splits.values()) + list(group_splits.values())):
        raise ValueError("image or anchor group crosses splits")
    anchors = defaultdict(list)
    for pair in groups.values():
        positives = [r for r in pair if r["label"] == "1"]
        negatives = [r for r in pair if r["label"] == "0"]
        if len(positives) != 1 or len(negatives) != 1:
            raise ValueError("each anchor requires one positive and one negative")
        pos, neg = positives[0], negatives[0]
        if any(pos[k] != neg[k] for k in ["image_path", "split", "anchor_group_id"]):
            raise ValueError("positive/negative anchor mismatch")
        if pos["text"] == neg["text"]:
            raise ValueError("positive and negative have identical text")
        anchors[pos["split"]].append((pos, neg))
    if set(anchors) != {"train", "val", "test"}:
        raise ValueError("train, val and test are required")
    return rows, anchors


def embedding(output):
    value = output if isinstance(output, torch.Tensor) else output.pooler_output
    return F.normalize(value.float(), dim=-1)


def load_images(paths, root):
    images = []
    for relative in paths:
        with Image.open(root / relative) as source:
            images.append(source.convert("RGB"))
    return images


def positive_masks(input_ids, attention_mask, batch_size):
    """Compare actual CLIP inputs, so truncation cannot create false negatives."""
    tokens = [tuple(ids[mask.bool()].tolist()) for ids, mask in zip(input_ids.cpu(), attention_mask.cpu())]
    image_to_text = torch.tensor([[a == b for b in tokens] for a in tokens[:batch_size]])
    text_to_image = image_to_text[:, :batch_size].T.contiguous()
    return image_to_text, text_to_image


def multi_positive_nce(logits, mask):
    if logits.shape != mask.shape or not mask.any(dim=1).all():
        raise ValueError("every query needs at least one known positive")
    return (torch.logsumexp(logits, dim=1) - torch.logsumexp(logits.masked_fill(~mask, -torch.inf), dim=1)).mean()


def contrastive_loss(images, texts, masks, temperature):
    batch = len(images)
    logits = images @ texts.T / temperature
    return 0.5 * (
        multi_positive_nce(logits, masks[0].to(logits.device))
        + multi_positive_nce(logits[:, :batch].T, masks[1].to(logits.device))
    )


def make_model(config):
    model = CLIPModel.from_pretrained(config["model_id"], revision=config["model_revision"])
    if config.get("training_mode", "lora") == "full":
        return model, []
    targets = [name for name, _ in model.named_modules()
               if name.endswith(("q_proj", "v_proj"))
               and (config["towers"] == "both" or name.startswith(config["towers"] + "_model."))]
    if not targets:
        raise ValueError("no matching Q/V layers")
    model = get_peft_model(model, LoraConfig(
        r=config["rank"], lora_alpha=config["alpha"], lora_dropout=config["dropout"],
        target_modules=targets, bias="none",
    ))
    trainable = [name for name, p in model.named_parameters() if p.requires_grad]
    if not trainable or any("lora_" not in name for name in trainable):
        raise ValueError("only LoRA parameters must be trainable")
    return model, targets


def score_rows(model, processor, rows, root, device, batch_size):
    model.eval()
    image_vectors, text_vectors = {}, {}
    with torch.inference_mode():
        paths = list(dict.fromkeys(r["image_path"] for r in rows))
        for start in range(0, len(paths), batch_size):
            batch = paths[start:start + batch_size]
            inputs = processor(images=load_images(batch, root), return_tensors="pt").to(device)
            vectors = embedding(model.get_image_features(**inputs)).cpu()
            image_vectors.update(zip(batch, vectors))
        texts = list(dict.fromkeys(r["text"] for r in rows))
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            inputs = processor(text=batch, padding=True, truncation=True, max_length=77, return_tensors="pt").to(device)
            vectors = embedding(model.get_text_features(**inputs)).cpu()
            text_vectors.update(zip(batch, vectors))
    scores = [float(image_vectors[r["image_path"]] @ text_vectors[r["text"]]) for r in rows]
    if not np.isfinite(scores).all():
        raise ValueError("non-finite scores")
    return scores


def write_scores(path, rows, scores):
    with Path(path).open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["pair_id", "score"])
        writer.writerows((r["pair_id"], f"{s:.8f}") for r, s in zip(rows, scores))


def train(config, run_dir, device, smoke=False):
    random.seed(config["seed"])
    np.random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    rows, anchors = read_dataset(ROOT / config["pairs_csv"], config["dataset_version"])
    train_anchors = anchors["train"][:32] if smoke else anchors["train"]
    val_rows = [r for pair in (anchors["val"][:16] if smoke else anchors["val"]) for r in pair]
    # Test rows are structurally validated above; neither test images nor scores
    # participate in training/checkpoint selection.
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "config.json", config)
    processor = CLIPProcessor.from_pretrained(config["model_id"], revision=config["model_revision"])
    model, targets = make_model(config)
    model.to(device)
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=config["learning_rate"], weight_decay=config["weight_decay"])
    epochs = 1 if smoke else config["epochs"]
    n_steps = math.ceil(len(train_anchors) / config["batch_size"]) * epochs
    warmup = max(1, int(n_steps * config["warmup_fraction"]))

    def lr_multiplier(step):
        if step < warmup:
            return (step + 1) / warmup
        return 0.5 * (1 + math.cos(math.pi * (step - warmup) / max(1, n_steps - warmup)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_multiplier)
    metadata = {
        "config": config, "smoke": smoke, "device": device,
        "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "transformers": transformers.__version__, "peft": peft.__version__, "numpy": np.__version__},
        "pairs_sha256": sha256(ROOT / config["pairs_csv"]),
        "script_sha256": sha256(__file__), "target_modules": targets,
        "trainable_parameters": sum(p.numel() for p in parameters),
        "total_parameters": sum(p.numel() for p in model.parameters()),
        "train_anchors": len(train_anchors), "validation_pairs": len(val_rows),
        "negative_counts": dict(Counter(n["neg_type"] for _, n in train_anchors)),
        "objective": "mean(image-to-[positive+negative]-text multi-positive InfoNCE, positive-text-to-image InfoNCE)",
        "checkpoint_selection": "highest val AUC, earlier epoch wins ties; includes initial checkpoint",
        "training_mode": config.get("training_mode", "lora"),
        "test_evaluated": False, "status": "running", "history": [],
    }
    write_json(run_dir / "training.json", metadata)
    root = ROOT / config["image_root"]
    best_auc, best_epoch, best_scores = -float("inf"), None, None
    started = time.monotonic()
    for epoch in range(epochs + 1):
        epoch_start = time.monotonic()
        losses = []
        if epoch:
            model.train()
            ordering = list(range(len(train_anchors)))
            random.Random(config["seed"] + epoch).shuffle(ordering)
            for start in range(0, len(ordering), config["batch_size"]):
                batch = [train_anchors[i] for i in ordering[start:start + config["batch_size"]]]
                positive = [p["text"] for p, _ in batch]
                negative = [n["text"] for _, n in batch]
                pixels = processor(images=load_images([p["image_path"] for p, _ in batch], root), return_tensors="pt").to(device)
                tokens = processor(text=positive + negative, padding=True, truncation=True, max_length=77, return_tensors="pt")
                masks = positive_masks(tokens["input_ids"], tokens["attention_mask"], len(batch))
                tokens = tokens.to(device)
                optimizer.zero_grad(set_to_none=True)
                images = embedding(model.get_image_features(**pixels))
                texts = embedding(model.get_text_features(**tokens))
                loss = contrastive_loss(images, texts, masks, config["temperature"])
                if not torch.isfinite(loss):
                    raise ValueError("non-finite training loss")
                loss.backward()
                grad_norm = torch.nn.utils.clip_grad_norm_(parameters, config["max_grad_norm"], error_if_nonfinite=True)
                optimizer.step()
                scheduler.step()
                losses.append((float(loss.detach()), len(batch)))
                if start == 0 or (start // config["batch_size"] + 1) % 25 == 0:
                    print(f"epoch={epoch} anchors={start + len(batch)}/{len(train_anchors)} loss={float(loss.detach()):.5f} grad_norm={float(grad_norm):.4f}", flush=True)
        scores = score_rows(model, processor, val_rows, root, device, config["batch_size"] * 2)
        auc = float(roc_auc_score([int(r["label"]) for r in val_rows], scores))
        if auc > best_auc:
            best_auc, best_epoch, best_scores = auc, epoch, scores
            model.save_pretrained(run_dir / ("best_model" if config.get("training_mode", "lora") == "full" else "best_adapter"))
            write_scores(run_dir / "val_scores.csv", val_rows, scores)
        result = {"epoch": epoch, "val_auc": auc,
                  "train_loss": sum(loss * n for loss, n in losses) / sum(n for _, n in losses) if losses else None,
                  "seconds": time.monotonic() - epoch_start}
        metadata["history"].append(result)
        metadata.update(best_epoch=best_epoch, best_val_auc=best_auc, elapsed_seconds=time.monotonic() - started)
        write_json(run_dir / "training.json", metadata)
        print(f"epoch={epoch} val_auc={auc:.6f} best_epoch={best_epoch} seconds={result['seconds']:.1f}", flush=True)
    # Verify the saved artifact actually restores the selected predictions.
    del optimizer, scheduler, parameters, model
    if device == "mps":
        torch.mps.empty_cache()
    artifact = run_dir / ("best_model" if config.get("training_mode", "lora") == "full" else "best_adapter")
    if config.get("training_mode", "lora") == "full":
        restored = CLIPModel.from_pretrained(artifact).to(device)
    else:
        base = CLIPModel.from_pretrained(config["model_id"], revision=config["model_revision"])
        restored = PeftModel.from_pretrained(base, artifact).to(device)
    reloaded = score_rows(restored, processor, val_rows, root, device, config["batch_size"] * 2)
    error = float(np.max(np.abs(np.array(reloaded) - np.array(best_scores))))
    if error > 1e-5:
        raise ValueError(f"checkpoint reload changes predictions by {error}")
    metadata.update(status="complete", reload_max_error=error,
                    checkpoint_sha256=sha256(artifact / "model.safetensors" if config.get("training_mode", "lora") == "full"
                                             else artifact / "adapter_model.safetensors"))
    if config.get("training_mode", "lora") == "lora":
        metadata["adapter_reload_max_error"] = error
    write_json(run_dir / "training.json", metadata)
    print(f"complete: best epoch {best_epoch}, validation AUC {best_auc:.6f}, reload error {error}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    parser.add_argument("--smoke", action="store_true", help="one epoch on 32 train anchors and 16 val anchors")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    if config.get("training_mode", "lora") not in {"lora", "full"}:
        parser.error("training_mode must be lora or full")
    if config["towers"] not in {"both", "text", "vision"}:
        parser.error("towers must be both, text or vision")
    if config["selection_metric"] != "val_auc" or not config["include_initial_checkpoint"]:
        parser.error("this protocol requires val_auc and inclusion of the initial checkpoint")
    for key in ["epochs", "batch_size", "learning_rate", "temperature", "max_grad_norm"]:
        if config[key] <= 0:
            parser.error(f"{key} must be positive")
    if config.get("training_mode", "lora") == "lora":
        for key in ["rank", "alpha"]:
            if config[key] <= 0:
                parser.error(f"{key} must be positive")
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    train(config, Path(args.run_dir), device, args.smoke)


if __name__ == "__main__":
    main()
