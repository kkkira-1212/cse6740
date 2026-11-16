"""Metrics required by the proposed final V3 reporting protocol."""
from collections import defaultdict

import numpy as np
from sklearn.metrics import roc_auc_score


def matched_rows(rows, neg_type):
    negatives = [row for row in rows if row["label"] == 0 and row["neg_type"] == neg_type]
    positives = {row["anchor_item_id"]: row for row in rows if row["label"] == 1}
    if len(positives) != sum(row["label"] == 1 for row in rows):
        raise ValueError("expected one positive per anchor")
    if any(row["anchor_item_id"] not in positives for row in negatives):
        raise ValueError("negative is missing its corresponding positive")
    return [(positives[row["anchor_item_id"]], row) for row in negatives]


def matched_metrics(rows, neg_type, threshold):
    pairs = matched_rows(rows, neg_type)
    if not pairs:
        raise ValueError(f"no {neg_type} pairs")
    positives = np.array([pair[0]["score"] for pair in pairs], dtype=float)
    negatives = np.array([pair[1]["score"] for pair in pairs], dtype=float)
    labels = np.r_[np.ones(len(pairs)), np.zeros(len(pairs))]
    scores = np.r_[positives, negatives]
    positive_recall = float(np.mean(positives >= threshold))
    negative_recall = float(np.mean(negatives < threshold))
    strict_wins = positives > negatives
    ties = positives == negatives
    return {
        "neg_type": neg_type, "n_pos": len(pairs), "n_neg": len(pairs),
        "auc": float(roc_auc_score(labels, scores)),
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": (positive_recall + negative_recall) / 2,
        "paired_ranking_accuracy": float(np.mean(strict_wins)),
        "paired_ranking_wins": int(strict_wins.sum()),
        "paired_ranking_ties": int(ties.sum()),
    }


def prediction_transitions(reference_rows, candidate_rows, reference_threshold, candidate_threshold, neg_types):
    reference = {row["pair_id"]: row for row in reference_rows}
    candidate = {row["pair_id"]: row for row in candidate_rows}
    if set(reference) != set(candidate):
        raise ValueError("paired error analysis requires identical pair IDs")
    allowed_anchors = {row["anchor_item_id"] for row in reference_rows
                       if row["label"] == 0 and row["neg_type"] in neg_types}
    selected = [pair_id for pair_id, row in reference.items()
                if row["anchor_item_id"] in allowed_anchors
                and (row["label"] == 1 or row["neg_type"] in neg_types)]
    counts = defaultdict(int)
    changed = []
    for pair_id in selected:
        old, new = reference[pair_id], candidate[pair_id]
        old_correct = (old["score"] >= reference_threshold) == bool(old["label"])
        new_correct = (new["score"] >= candidate_threshold) == bool(new["label"])
        key = ("correct" if old_correct else "wrong") + "_to_" + ("correct" if new_correct else "wrong")
        counts[key] += 1
        if old_correct != new_correct:
            changed.append({"pair_id": pair_id, "anchor_item_id": old["anchor_item_id"],
                            "neg_type": old["neg_type"], "reference_score": old["score"],
                            "candidate_score": new["score"], "transition": key})
    for key in ("wrong_to_correct", "correct_to_wrong", "correct_to_correct", "wrong_to_wrong"):
        counts[key] += 0
    return {"n_rows": len(selected), **dict(counts), "changed": changed}


def ranking_transitions(reference_rows, candidate_rows, neg_types):
    output = {}
    for neg_type in neg_types:
        ref = {neg["anchor_item_id"]: np.sign(pos["score"] - neg["score"])
               for pos, neg in matched_rows(reference_rows, neg_type)}
        new = {neg["anchor_item_id"]: np.sign(pos["score"] - neg["score"])
               for pos, neg in matched_rows(candidate_rows, neg_type)}
        if set(ref) != set(new):
            raise ValueError("paired ranking requires identical anchors")
        counts = defaultdict(int)
        for anchor in ref:
            old = "win" if ref[anchor] > 0 else "tie" if ref[anchor] == 0 else "loss"
            current = "win" if new[anchor] > 0 else "tie" if new[anchor] == 0 else "loss"
            counts[f"{old}_to_{current}"] += 1
        output[neg_type] = {"n_anchors": len(ref), **dict(counts)}
    return output


def n3_exchange_bootstrap(rows, exchange_by_pair, threshold, n_resamples=1000, seed=0):
    pairs = matched_rows(rows, "N3")
    units = defaultdict(list)
    for positive, negative in pairs:
        exchange = exchange_by_pair.get(negative["pair_id"])
        if not exchange:
            raise ValueError(f"missing N3 exchange for {negative['pair_id']}")
        units[exchange].append((positive, negative))
    if any(len(value) != 2 for value in units.values()):
        raise ValueError("each reciprocal N3 exchange must contain two directions")
    keys = sorted(units)
    rng = np.random.default_rng(seed)
    fields = ("auc", "positive_recall", "negative_recall", "balanced_accuracy", "paired_ranking_accuracy")
    samples = {field: [] for field in fields}
    for _ in range(n_resamples):
        sampled = []
        for draw, index in enumerate(rng.integers(0, len(keys), size=len(keys))):
            for positive, negative in units[keys[int(index)]]:
                sampled.extend(({**positive, "pair_id": f"{positive['pair_id']}#{draw}",
                                 "anchor_item_id": f"{positive['anchor_item_id']}#{draw}"},
                                {**negative, "pair_id": f"{negative['pair_id']}#{draw}",
                                 "anchor_item_id": f"{negative['anchor_item_id']}#{draw}"}))
        result = matched_metrics(sampled, "N3", threshold)
        for field in fields:
            samples[field].append(result[field])
    return {
        "unit": "complete_reciprocal_exchange", "n_exchanges": len(keys),
        "n_resamples": n_resamples, "seed": seed,
        "intervals": {field: {"low": float(np.percentile(values, 2.5)),
                              "high": float(np.percentile(values, 97.5))}
                      for field, values in samples.items()},
    }
