"""ID-fitted shortcut probes evaluated on the v3 OOD candidate.

Fits text-only TF-IDF controls on the frozen ID v3 train split, selects their
threshold on ID val, and then scores the OOD candidate. No fitting, prompt
selection or threshold tuning happens on OOD.

The image-only probe is a structural null. Fixed-image pairs share the same
image for their positive and negative, so every image-only model is constant
per anchor. We use a constant 0.5 score and threshold 0.5; the informative
result is AUC 0.5 and paired-ranking ties, not a model-quality claim. OOD images
are therefore not needed.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import sklearn

_EVAL_DIR = str(Path(__file__).resolve().parent)
if _EVAL_DIR not in sys.path:
    sys.path.insert(0, _EVAL_DIR)
import controls  # noqa: E402
import matched_metrics  # noqa: E402

OOD_VERSION = "abo-ood-v3-20261115-candidate"
OOD_DIR = controls.REPO / "data" / "releases" / OOD_VERSION


def load_shared_eval():
    spec = importlib.util.spec_from_file_location(
        "shared_eval", Path(__file__).resolve().parent / "eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared_eval = load_shared_eval()


def release_hash(path, manifest_names=("screening_manifest.json", "manifest.json")):
    """Verify a table against an adjacent release manifest when one exists."""
    path = Path(path)
    actual = controls.sha256_file(path)
    for manifest_name in manifest_names:
        manifest_path = path.with_name(manifest_name)
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest.get("output_sha256", {}).get(path.name)
        if expected:
            if actual != expected:
                raise ValueError(
                    f"{path.name} SHA-256 {actual} does not match "
                    f"{manifest_name} {expected}"
                )
            return {
                "manifest": manifest_name,
                "manifest_sha256": controls.sha256_file(manifest_path),
                "output_sha256": expected,
            }
    return None


def load_id_data(path, expected_version):
    rows = controls.validate_rows(controls.read_pairs(path))
    controls.check_fixed_image_layout(rows)
    splits = controls.split_rows(rows)
    versions = sorted({
        row.get("dataset_version", "") for row in rows if row.get("dataset_version")
    })
    if versions != [expected_version]:
        raise ValueError(
            f"ID dataset versions {versions} do not match {expected_version!r}"
        )
    pairs_sha256 = controls.sha256_file(path)
    if pairs_sha256 != controls.V3_PAIRS_SHA256:
        raise ValueError(
            f"ID pairs SHA-256 {pairs_sha256} does not match the pinned v3 candidate "
            f"{controls.V3_PAIRS_SHA256}"
        )
    return rows, splits, pairs_sha256


def load_ood_data(path, splits_requested, expected_version, provenance_path):
    rows = shared_eval.load_pairs(path)
    controls.check_fixed_image_layout(rows)
    versions = sorted({
        row.get("dataset_version", "") for row in rows if row.get("dataset_version")
    })
    if versions != [expected_version]:
        raise ValueError(
            f"OOD dataset versions {versions} do not match {expected_version!r}"
        )
    selected = [row for row in rows if row["split"] in splits_requested]
    for split in splits_requested:
        subset = [row for row in selected if row["split"] == split]
        if not subset:
            raise ValueError(f"no rows in OOD split {split!r}")
        if len({row["label"] for row in subset}) < 2:
            raise ValueError(f"OOD split {split!r} must contain both labels")
    n3_present = any(
        row["label"] == 0 and row["neg_type"] == "N3" for row in selected
    )
    if n3_present and not provenance_path:
        raise ValueError("N3 provenance is required when OOD splits contain N3 negatives")
    provenance_rows = []
    provenance_sha256 = None
    if provenance_path:
        _, provenance_rows = shared_eval.read_csv_rows(provenance_path)
        provenance_sha256 = controls.sha256_file(provenance_path)
        matched_metrics.build_exchange_map(selected, provenance_rows)
    return rows, selected, provenance_rows, provenance_sha256


def fit_text_probe(train_rows, val_rows, analyzer, seed):
    vectorizer, classifier = controls.fit_text(train_rows, seed, analyzer)
    val_scores = controls.score_text(val_rows, vectorizer, classifier)
    scored = [dict(row, score=val_scores[row["pair_id"]]) for row in val_rows]
    threshold, _ = shared_eval.select_threshold(scored, "accuracy")
    return {
        "name": f"text-only {analyzer}",
        "kind": "text",
        "analyzer": analyzer,
        "vectorizer": vectorizer,
        "classifier": classifier,
        "threshold": float(threshold),
        "threshold_source": (
            "ID val accuracy; rule score >= threshold; smallest threshold on ties"
        ),
        "id_val_metrics": shared_eval.compute_metrics(scored, threshold, False),
        "train_auc": controls.text_train_auc(train_rows, vectorizer, classifier),
    }


def image_null_probe():
    return {
        "name": "image-only structural null",
        "kind": "image_null",
        "analyzer": None,
        "threshold": 0.5,
        "threshold_source": (
            "structural null: constant 0.5 per pair because fixed-image positives "
            "and negatives share the image; no OOD images or fitting"
        ),
        "id_val_metrics": None,
        "train_auc": None,
    }


def score_probe(probe, ood_rows):
    if probe["kind"] == "text":
        return controls.score_text(ood_rows, probe["vectorizer"], probe["classifier"])
    return {row["pair_id"]: 0.5 for row in ood_rows}


def fmt_metric(metrics, name, formatter):
    value = metrics.get(name)
    if value is None:
        return "—"
    interval = (metrics.get("ci") or {}).get(name)
    if interval is None:
        return formatter(value)
    return f"{formatter(value)} [{formatter(interval['low'])}, {formatter(interval['high'])}]"


def summary_markdown(meta, probes):
    lines = [
        "# OOD shortcut probe (ID-fitted)",
        "",
        f"- ID probes fitted on: `{meta['id']['pairs_csv']}` "
        f"(SHA-256 `{meta['id']['pairs_sha256']}`)",
        f"- ID rows: train {meta['id']['train_rows']}, val {meta['id']['val_rows']}",
        f"- OOD table: `{meta['ood']['pairs_csv']}` "
        f"(SHA-256 `{meta['ood']['pairs_sha256']}`)",
        f"- OOD splits: {', '.join(f'`{s}`' for s in meta['ood']['splits'])}",
        "- Fitting/threshold selection: ID train / ID val only; no OOD fitting or tuning",
        "- Status: diagnostic before OOD adoption; not a model benchmark result",
        "",
    ]
    for probe in probes:
        report = probe["report"]
        lines.extend([
            f"## {probe['name']} (threshold `{probe['threshold']!r}`)",
            "",
            f"- Threshold source: {probe['threshold_source']}",
            f"- Scores: `{probe['scores_csv']}`",
        ])
        if probe["kind"] == "text":
            lines.append(
                f"- ID fit: train AUC {shared_eval.fmt_num(probe['train_auc'])}; "
                f"ID val AUC {shared_eval.fmt_num(probe['id_val_metrics']['auc'])}, "
                f"accuracy {shared_eval.fmt_pct(probe['id_val_metrics']['accuracy'])}"
            )
        else:
            lines.append(
                "- Structural null: every pair gets 0.5; AUC is 0.5 and all "
                "positive/negative rankings tie by construction."
            )
        lines.append("")
        headers = ["Split", "n", "Acc", "AUC", "Balanced", "Pos recall", "Neg recall"]
        rows = []
        for split in meta["ood"]["splits"]:
            metrics = report["test_by_split"][split]
            rows.append([
                split,
                str(metrics["n"]),
                shared_eval.fmt_pct(metrics["accuracy"]),
                shared_eval.fmt_num(metrics["auc"]),
                shared_eval.fmt_pct(metrics["balanced_accuracy"]),
                shared_eval.fmt_pct(metrics["positive_recall"]),
                shared_eval.fmt_pct(metrics["negative_recall"]),
            ])
        lines.extend(shared_eval.md_table(headers, rows))
        lines.append("")
        headers = ["Split", "Type", "n_pos/n_neg", "Clusters", "AUC",
                   "Pos recall", "Neg recall", "Balanced", "Paired rank", "Ties"]
        rows = []
        for split in meta["ood"]["splits"]:
            for neg_type, metrics in sorted(
                report.get("matched_types", {}).get(split, {}).items()
            ):
                clusters = (
                    f"{metrics['n_clusters']} exchanges"
                    if metrics.get("cluster") == matched_metrics.EXCHANGE_CLUSTER
                    else f"{metrics['n_clusters']} groups"
                )
                rows.append([
                    split,
                    neg_type,
                    f"{metrics['n_pos']}/{metrics['n_neg']}",
                    clusters,
                    fmt_metric(metrics, "auc", shared_eval.fmt_num),
                    fmt_metric(metrics, "positive_recall", shared_eval.fmt_pct),
                    fmt_metric(metrics, "negative_recall", shared_eval.fmt_pct),
                    fmt_metric(metrics, "balanced_accuracy", shared_eval.fmt_pct),
                    fmt_metric(metrics, "paired_ranking_accuracy", shared_eval.fmt_pct),
                    str(metrics.get("paired_ranking_ties", 0)),
                ])
        lines.extend(shared_eval.md_table(headers, rows))
        lines.append("")

    text_probes = [probe for probe in probes if probe["kind"] == "text"]
    if text_probes:
        lines.extend([
            "## ID text features",
            "",
            "Top negative and positive logistic-regression features from the ID fit.",
            "",
            "| Probe | Top negative | Top positive |",
            "|---|---|---|",
        ])
        for probe in text_probes:
            features = controls.top_text_features(
                probe["vectorizer"], probe["classifier"]
            )
            negative = ", ".join(
                f"`{name}` ({value:+.3f})" for name, value in features["negative"]
            )
            positive = ", ".join(
                f"`{name}` ({value:+.3f})" for name, value in features["positive"]
            )
            lines.append(f"| {probe['name']} | {negative} | {positive} |")
        lines.append("")

    lines.extend([
        "## Caveats",
        "",
        "- The text probe is a simple TF-IDF/logistic-regression shortcut check, not a model.",
        "- The image probe is structural and cannot detect any image-side signal in this layout.",
        "- OOD table and its model-assisted QC are not frozen or human-certified.",
        "- Do not use these probe scores for threshold selection, model selection or final claims.",
        "",
    ])
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--id-pairs-csv", default=str(controls.V3_PAIRS))
    parser.add_argument("--expected-id-version", default=controls.V3_DATASET_VERSION)
    parser.add_argument("--ood-pairs-csv",
                        default=str(OOD_DIR / "eval_pairs.csv"))
    parser.add_argument("--ood-n3-provenance",
                        default=str(OOD_DIR / "eval_n3_provenance.csv"))
    parser.add_argument("--expected-ood-version", default=OOD_VERSION)
    parser.add_argument("--splits", nargs="+", default=["ood_near", "ood_far"])
    parser.add_argument("--text-features", choices=("word", "char", "both"),
                        default="both")
    parser.add_argument("--out-dir", default=str(controls.REPO / "scores"))
    parser.add_argument("--output-prefix", default="ood_v3_probe")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    if args.bootstrap < 0:
        parser.error("--bootstrap must be non-negative")
    splits_requested = list(dict.fromkeys(args.splits))
    if not splits_requested:
        parser.error("--splits must contain at least one split")

    _, id_splits, id_pairs_sha256 = load_id_data(
        args.id_pairs_csv, args.expected_id_version
    )
    id_sha_meta = release_hash(args.id_pairs_csv)
    _, ood_selected, _, provenance_sha256 = load_ood_data(
        args.ood_pairs_csv, splits_requested, args.expected_ood_version,
        args.ood_n3_provenance,
    )
    ood_sha_meta = release_hash(args.ood_pairs_csv)
    provenance_meta = (
        release_hash(args.ood_n3_provenance) if args.ood_n3_provenance else None
    )

    if args.ood_n3_provenance and provenance_sha256 is None:
        raise ValueError("N3 provenance path is not a file")
    if any(row["neg_type"] == "N3" for row in ood_selected) and not args.ood_n3_provenance:
        raise ValueError("N3 provenance is required when OOD splits contain N3 negatives")

    analyzers = ["word", "char"] if args.text_features == "both" else [args.text_features]
    probes = [fit_text_probe(id_splits["train"], id_splits["val"], analyzer, args.seed)
              for analyzer in analyzers]
    probes.append(image_null_probe())

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scored_rows = ood_selected
    for probe in probes:
        suffix = (
            f"text_{probe['analyzer']}" if probe["kind"] == "text"
            else "image_identity"
        )
        scores = score_probe(probe, scored_rows)
        scores_path = out_dir / f"{args.output_prefix}_{suffix}.csv"
        controls.write_scores(scores_path, scored_rows, scores)
        probe["scores_csv"] = controls.display_path(scores_path)
        probe["score_sha256"] = controls.sha256_file(scores_path)

        print(            f"evaluating {probe['name']} at ID-val threshold {probe['threshold']!r}",
            flush=True,
        )
        shared_eval.main([
            "--pairs-csv", str(args.ood_pairs_csv),
            "--scores-csv", str(scores_path),
            "--test-splits", *splits_requested,
            "--fixed-threshold", repr(probe["threshold"]),
            "--matched-type-metrics",
            "--n3-provenance", str(args.ood_n3_provenance),
            "--bootstrap", str(args.bootstrap),
            "--seed", str(args.seed),
        ])
        stem = scores_path.stem
        report_path = scores_path.with_name(f"{stem}_eval.json")
        probe["report"] = json.loads(report_path.read_text(encoding="utf-8"))
        probe["eval_json"] = controls.display_path(report_path)
        probe["eval_md"] = controls.display_path(
            report_path.with_name(f"{stem}_eval.md")
        )
        probe["eval_matched_csv"] = controls.display_path(
            scores_path.with_name(f"{stem}_eval_matched.csv")
        )
        if probe["kind"] == "text":
            probe["vocabulary"] = len(probe["vectorizer"].vocabulary_)
            probe["top_features"] = controls.top_text_features(
                probe["vectorizer"], probe["classifier"]
            )
        else:
            probe["vocabulary"] = None
            probe["top_features"] = None

    meta = {
        "tool": "src/eval/ood_shortcut.py",
        "status": "DIAGNOSTIC_NO_OOD_FITTING_NOT_A_MODEL_RESULT",
        "id": {
            "pairs_csv": controls.display_path(args.id_pairs_csv),
            "pairs_sha256": id_pairs_sha256,
            "dataset_version": args.expected_id_version,
            "train_rows": len(id_splits["train"]),
            "val_rows": len(id_splits["val"]),
            "release": id_sha_meta,
        },
        "ood": {
            "pairs_csv": controls.display_path(args.ood_pairs_csv),
            "pairs_sha256": controls.sha256_file(args.ood_pairs_csv),
            "dataset_version": args.expected_ood_version,
            "splits": splits_requested,
            "n_pairs": len(ood_selected),
            "release": ood_sha_meta,
            "n3_provenance": (
                controls.display_path(args.ood_n3_provenance)
                if args.ood_n3_provenance else None
            ),
            "n3_provenance_sha256": provenance_sha256,
            "n3_provenance_release": provenance_meta,
        },
        "protocol": {
            "fit_split": "ID v3 train",
            "selection_split": "ID v3 val",
            "objective": "accuracy",
            "rule": "score >= threshold",
            "tie_break": "smallest threshold among maximum-accuracy candidates",
            "ood_fitting": False,
            "ood_threshold_tuning": False,
            "image_probe": "structural null (constant 0.5; fixed-image layout)",
            "bootstrap_resamples": args.bootstrap,
            "seed": args.seed,
        },
        "probes": [
            {key: value for key, value in probe.items() if key not in (
                "vectorizer", "classifier"
            )}
            for probe in probes
        ],
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
        "git": controls.git_state(),
        "notes": [
            "Text probes are fitted on ID train only; thresholds come from ID val only.",
            "OOD is used only for scoring; no fitting, prompt or threshold selection.",
            "The image-only probe is a structural null, not an image-quality check.",
            "OOD data is a model-assisted QC candidate, not frozen or human-certified.",
        ],
    }

    meta_path = out_dir / f"{args.output_prefix}_meta.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary_path = out_dir / f"{args.output_prefix}_summary.md"
    summary_path.write_text(
        "\n".join(summary_markdown(meta, probes)), encoding="utf-8"
    )
    print(f"wrote {meta_path}", flush=True)
    print(f"wrote {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
