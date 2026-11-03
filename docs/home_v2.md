# Furniture + Decor v2: Data Handoff

Version: `abo-home-v2-20261103`. Status: **generated candidate data, awaiting human quality review**. This is separate from the original furniture pilot and its scores.

## Deliverables

- Main experiment data: [release README](../data/releases/abo-home-v2-20261103/README.md).
- Generation configuration: [abo_home_v2.json](../configs/abo_home_v2.json).
- Product/pair tables, counts, provenance and structural checks: `data/releases/abo-home-v2-20261103/`.
- Download both deliverables from [the GitHub Release](https://github.com/kkkira-1212/cse6740/releases/tag/abo-home-v2-20261103). The [tracked review batch](../data/reviews/abo-home-v2-20261103/README.md) contains blank CSV inputs and provenance; image-embedded HTML and the full image ZIP are release assets, not Git blobs.

## What changed from the pilot

All 16 official ABO listing shards are scanned. Furniture and explicit decor types are considered; mixed HOME categories require a qualifying Furniture/Home Decor path. Lighting and footwear are held out, and globally connected held-out groups are removed from the main scope.

Group signals are shared non-frequent main images, exact case-folded titles, and product-type-specific normalized titles. Normalization removes full attribute phrases with word boundaries and size/pack expressions. These are conservative heuristics, not human-confirmed product identity. One deterministic representative is selected per group. Raw duplicate/group membership is retained in the release ledger.

Categories are ranked by representative-group count. This candidate version requires at least 100 groups total, with at least 50/10/10 groups in train/val/test. Splits are stratified by product type at approximately 80/10/10. Small types are logged, not silently pooled or used only for easy negatives.

Every image anchor has one original positive and one candidate negative. N1 selects another product type's real title; N2 selects a same-type real title; both remain in the same split and exclude the same group/image and positive-input collisions. N3 keeps the image and swaps a color phrase using Sean's conservative raw-metadata checks. N3 is capped at one third of each split's negatives, and N1/N2 divide the remainder with at most one example difference.

Donor selection prefers the least-used legal title-source groups and randomizes ties with a fixed seed. Three uses per split across N1/N2 is a soft limit; any excess is recorded. It is not a hard one-use policy. This release happens to achieve one use per selected donor group without relaxation.

## Review before final claims

The 100 examples are sampled from the exact train N2 pairs in this release, across all retained types. Their titles are not independently regenerated. Test labels have not been manually inspected to tune the new random N2 rule. Earlier project exploration did inspect the old pilot, so this release is not claimed to be a wholly pristine new source-level holdout.

N1/N2 mismatches are not guaranteed by swapping. N3 candidates are not automatically human-approved, and the four target colors can introduce text-only shortcuts. Run the planned human audit and text-only/image-only controls before interpreting results as final benchmark performance.

Do not apply the old pilot threshold or reuse old model/API scores. Every model must score the new exact pairs. The provided evaluator is classification-only; one negative per anchor is not the earlier three-way R@1 task.

## Regenerate locally

```bash
python src/data/fetch_raw.py --out-dir data/raw
python src/data/build_home_release.py \
  --config configs/abo_home_v2.json \
  --out-dir data/releases/abo-home-v2-20261103 \
  --audit-dir ../output/n2_home_v2_20261103 \
  --download-images
```

Existing releases are not overwritten. To finish/retry image verification without regenerating pairs, add `--resume-images`. Changing selection rules, seed or metadata requires a new release path/version. Raw images, image-embedded HTML, caches and API logs stay outside Git.

## Shared model and evaluation code

Aaron PR #4 and Jane PR #5 are merged with v2 source/anchor compatibility. Prefer `src/eval/eval.py` in the repository for current classification evaluation; it uses explicit v2 source fields, image-anchor group bootstrap clusters and rejects legacy three-way R@1 on v2. Baseline subset sampling keeps v2 anchor pairs together, and API cache fingerprints include exact input/prompt contents.

The data ZIP's standalone evaluator is a frozen snapshot from the data build, retained for independent use. Its classification metrics match the shared evaluator; its ranking flag is blocked. This immutable data ZIP does not contain subsequent main-branch changes. No new model inference or paid API result is included. Broader documentation cleanup and AI-attribution history changes remain separate work.
