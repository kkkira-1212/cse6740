"""Matched-anchor metrics for fixed-image image/title pairs.

Each unit pairs one negative row with the positive row of the same
``anchor_item_id``. This keeps a negative type's corresponding positives from
being replaced by unrelated positives from the rest of the dataset. N3 units
can be clustered by reciprocal exchange so bootstrap intervals resample whole
exchanges rather than individual directions.

The module is pure: it reads rows and provenance dictionaries, and returns
metrics. CLI/reporting stay in ``eval.py``.
"""
from collections import defaultdict
from typing import NamedTuple

import numpy as np
from sklearn.metrics import roc_auc_score

MATCHED_METRIC_NAMES = (
    "auc",
    "positive_recall",
    "negative_recall",
    "balanced_accuracy",
    "paired_ranking_accuracy",
)
EXCHANGE_CLUSTER = "reciprocal_exchange"
ANCHOR_CLUSTER = "image_anchor_group"


class Unit(NamedTuple):
    cluster_key: tuple
    cluster: str
    split: str
    anchor_item_id: str
    positive: dict
    negative: dict


def _label(row):
    try:
        return int(row.get("label"))
    except (TypeError, ValueError):
        raise ValueError(f"invalid label {row.get('label')!r} for {row.get('pair_id')!r}") from None


def build_exchange_map(rows, provenance_rows):
    """Map each N3 negative pair to its reciprocal exchange id.

    Supports both provenance schemas in use:

    - ID v3 ``n3_provenance.csv``: ``pair_id`` matches the pairs table directly.
    - OOD v3 ``eval_n3_provenance.csv``: ``pair_id`` keeps an internal suffix
      such as ``_N3R2``, so the join must use ``anchor_item_id``.

    A direct ``pair_id`` match wins; otherwise the anchor mapping is used. Every
    N3 negative in ``rows`` must resolve, or the function raises.
    """
    direct = {}
    by_anchor = {}
    for line, provenance in enumerate(provenance_rows, start=2):
        exchange = (provenance.get("exchange_id") or "").strip()
        if not exchange:
            raise ValueError(f"provenance row {line}: empty exchange_id")
        pair_id = (provenance.get("pair_id") or "").strip()
        if pair_id:
            if pair_id in direct and direct[pair_id] != exchange:
                raise ValueError(f"provenance pair {pair_id!r} maps to multiple exchanges")
            direct[pair_id] = exchange
        anchor = (provenance.get("anchor_item_id") or "").strip()
        if anchor:
            if anchor in by_anchor and by_anchor[anchor] != exchange:
                raise ValueError(f"provenance anchor {anchor!r} maps to multiple exchanges")
            by_anchor[anchor] = exchange

    result = {}
    missing = []
    conflicts = []
    for row in rows:
        if _label(row) != 0 or row.get("neg_type") != "N3":
            continue
        pair_id = row["pair_id"]
        anchor = (row.get("anchor_item_id") or "").strip()
        exchange = direct.get(pair_id)
        anchor_exchange = by_anchor.get(anchor) if anchor else None
        if exchange is not None and anchor_exchange is not None and exchange != anchor_exchange:
            conflicts.append(pair_id)
            continue
        exchange = exchange if exchange is not None else anchor_exchange
        if exchange is None:
            missing.append(pair_id)
        else:
            result[pair_id] = exchange
    if conflicts:
        raise ValueError(
            f"{len(conflicts)} N3 pairs have conflicting pair_id/anchor exchange ids "
            f"(e.g. {conflicts[:3]})"
        )
    if missing:
        raise ValueError(
            f"{len(missing)} N3 pairs have no exchange_id in the provenance "
            f"(e.g. {missing[:3]}); matched by pair_id or anchor_item_id"
        )
    return result


def negative_types(rows):
    """Negative types present in ``rows``, excluding the positive rows."""
    return sorted({row["neg_type"] for row in rows if _label(row) == 0})


def matched_units(rows, neg_type, exchange_map=None):
    """Pair each negative of ``neg_type`` with its anchor's positive.

    ``exchange_map`` is a ``pair_id -> exchange_id`` mapping. When it is
    non-empty and ``neg_type`` is N3, clusters are reciprocal exchanges and each
    exchange must contain both directions. Otherwise clusters are image-anchor
    groups, matching the existing v2/v3 evaluator convention.
    """
    positives = {}
    for row in rows:
        if _label(row) != 1:
            continue
        key = (row.get("split", ""), row.get("anchor_item_id", ""))
        if key in positives:
            raise ValueError(f"duplicate positive for anchor {key!r}")
        positives[key] = row

    units = []
    for row in rows:
        if _label(row) != 0 or row.get("neg_type") != neg_type:
            continue
        split = row.get("split", "")
        anchor = (row.get("anchor_item_id") or "").strip()
        if not anchor:
            raise ValueError(f"negative {row['pair_id']} has no anchor_item_id")
        positive = positives.get((split, anchor))
        if positive is None:
            raise ValueError(
                f"no positive for anchor {anchor!r} in split {split!r} "
                f"(negative {row['pair_id']})"
            )
        if neg_type == "N3" and exchange_map:
            exchange = exchange_map.get(row["pair_id"])
            if exchange is None:
                raise ValueError(f"missing exchange_id for N3 pair {row['pair_id']}")
            cluster_key = (split, exchange)
            cluster = EXCHANGE_CLUSTER
        else:
            cluster_key = (split, row.get("anchor_group_id") or anchor)
            cluster = ANCHOR_CLUSTER
        units.append(Unit(cluster_key, cluster, split, anchor, positive, row))

    if not units:
        return []
    clusters = {unit.cluster for unit in units}
    if len(clusters) != 1:
        raise ValueError(f"mixed cluster units for {neg_type}: {sorted(clusters)}")
    if EXCHANGE_CLUSTER in clusters:
        by_exchange = defaultdict(list)
        for unit in units:
            by_exchange[unit.cluster_key].append(unit)
        incomplete = {
            key: len(group) for key, group in by_exchange.items() if len(group) != 2
        }
        if incomplete:
            raise ValueError(
                "N3 exchange must contain both directions: "
                + ", ".join(f"{key}={count}" for key, count in sorted(incomplete.items()))
            )
    units.sort(key=lambda unit: (unit.split, unit.anchor_item_id, unit.negative["pair_id"]))
    return units


def matched_metrics(units, threshold=None):
    """Point metrics for matched units.

    ``threshold`` may be None when only threshold-free metrics (AUC and paired
    ranking) are needed, as in ``controls.matched_auc``.
    """
    empty = {
        "n_pos": 0, "n_neg": 0, "n_anchors": 0, "n_clusters": 0,
        "n_exchanges": None, "cluster": None,
        "auc": None, "positive_recall": None, "negative_recall": None,
        "balanced_accuracy": None, "paired_ranking_accuracy": None,
        "paired_ranking_ties": 0, "threshold": threshold,
    }
    if not units:
        return empty

    labels = np.array([1] * len(units) + [0] * len(units), dtype=np.int8)
    values = np.array(
        [unit.positive["score"] for unit in units]
        + [unit.negative["score"] for unit in units],
        dtype=np.float64,
    )
    auc = float(roc_auc_score(labels, values))
    positive_recall = negative_recall = balanced = None
    if threshold is not None:
        positive_recall = float(
            np.mean([unit.positive["score"] >= threshold for unit in units])
        )
        negative_recall = float(
            np.mean([unit.negative["score"] < threshold for unit in units])
        )
        balanced = (positive_recall + negative_recall) / 2.0
    paired_ranking = float(
        np.mean([unit.positive["score"] > unit.negative["score"] for unit in units])
    )
    ties = int(sum(
        unit.positive["score"] == unit.negative["score"] for unit in units
    ))
    cluster = units[0].cluster
    n_clusters = len({unit.cluster_key for unit in units})
    return {
        "n_pos": len(units),
        "n_neg": len(units),
        "n_anchors": len({(unit.split, unit.anchor_item_id) for unit in units}),
        "n_clusters": n_clusters,
        "n_exchanges": n_clusters if cluster == EXCHANGE_CLUSTER else None,
        "cluster": cluster,
        "auc": auc,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": balanced,
        "paired_ranking_accuracy": paired_ranking,
        "paired_ranking_ties": ties,
        "threshold": threshold,
    }


def matched_bootstrap(units, threshold=None, n_resamples=1000, seed=0):
    """Percentile 95% intervals resampling complete clusters.

    N1/N2 clusters are image-anchor groups; N3 clusters are complete reciprocal
    exchanges. Repeated cluster draws keep both directions and their positive
    and negative rows together.
    """
    if n_resamples <= 0 or not units:
        return None

    by_cluster = defaultdict(list)
    for unit in units:
        by_cluster[unit.cluster_key].append(unit)
    keys = sorted(by_cluster)
    rng = np.random.default_rng(seed)
    samples = {name: [] for name in MATCHED_METRIC_NAMES}
    for _ in range(n_resamples):
        drawn = []
        for index in rng.choice(len(keys), size=len(keys), replace=True):
            drawn.extend(by_cluster[keys[int(index)]])
        metrics = matched_metrics(drawn, threshold)
        for name in MATCHED_METRIC_NAMES:
            value = metrics[name]
            if value is not None and np.isfinite(value):
                samples[name].append(value)
    return {
        name: {
            "low": float(np.percentile(values, 2.5)),
            "high": float(np.percentile(values, 97.5)),
            "valid_resamples": len(values),
        } if values else None
        for name, values in samples.items()
    }
