# ABO furniture/decor V3 frozen experiment release

Release ID and Git tag: `abo-home-v3-20261115`.

Kira authorized this release for the team's main experiments after review of
PR #12, its QC follow-up, and Aaron's PR #13 shortcut diagnostics.
The accepted snapshot contains 3,335 anchors and 6,670 pairs.

## Exact experiment inputs

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Images: `data/releases/abo-home-v2-20261103/images`
- CSV dataset_version: `abo-home-reciprocal-v3-candidate`
- Pairs SHA-256: `14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003`
- Data construction commit: `b1b0aaa7a6d2e999225f87e3b51af38df6252bb0`
- QC follow-up commit: `f3524aacfde3d5ce225043d7618fbe317f21e530`
- Integration source: `cb63a01` (includes controls PR #13).

The release ID names the adopted snapshot. The existing candidate-named directory
and CSV version are retained as its storage identity. All six source CSVs are
byte-identical to the reviewed candidate. Existing controls and validation
scores with this exact input hash remain attributable to this snapshot.
The candidate's historical manifest records its construction-time status;
this release manifest records adoption for main experiments.

| Split | Positives | N1 | N2 | N3 | Total |
|---|---:|---:|---:|---:|---:|
| train | 2664 | 1199 | 1199 | 266 | 5328 |
| val | 328 | 152 | 152 | 24 | 656 |
| test | 343 | 156 | 157 | 30 | 686 |

## Accepted construction and quality limitations

Images stay fixed. N1 uses a different-type real title and N2 a same-type real
title, within split and across groups/images. Reciprocal N3 uses paired color
exchanges. The 450 fallback rows remain generated/unreviewed. Donor reuse reaches
a maximum of two in the final N1/N2 pool. Group identity is heuristic.

Four train fallback rows retain uncertainty flags and remain in training:
`B07Q88MYL4_N1`, `B07TTCHRB2_N2`, `B07JD7RFRN_N2`, `B075H8JNZT_N2`.
Apply the follow-up QC ledger over the original spot check by pair_id when
reporting judgments. Reviewer types and original judgments remain explicit.

Aaron's test controls give overall word/char AUC 0.5160/0.5204 and N3 AUC
0.5189/0.5056. These probes show a substantial reduction in the earlier N3 text
signal. N1 retains a weak text signal (0.5698/0.5649); the historical similarity
alone cannot isolate the effect of fallback generation. Semantic label noise
remains possible. N3 test comprises 30 negatives in 15 exchanges. Its AUC
intervals resample exchanges; overall reported intervals use image-anchor groups
and omit exchange dependence. Controls have already examined test, and the
source population was explored during development. Report this history.

## Verify and run

From the repository root or extracted data-package root:

```sh
python data/releases/abo-home-v3-20261115/verify.py
python data/releases/abo-home-v2-20261103/tools/verify.py --images
```

The first command verifies frozen tables, audit evidence and controls artifacts.
The second checks the reused v2 image assets against their original manifest.
The package places all 3,335 images at the image-root path above. A source-only
checkout can fetch them using the v2 `tools/download_images.py` script.

Configure each model with the exact pairs path, dataset_version and image root
above. Use a fresh run/output location with this release ID. Jack's LoRA/full
runs start from pretrained weights. Record model revision, config, seed and
selected checkpoint. Fit on train, select thresholds/checkpoints on val, and
report test with the agreed fixed settings. Bind score provenance to the pairs
hash. Historical v2 training results use a different input table.

Jane's candidate validation scores share this data hash. Capture the actual
loaded model revisions before using those scores as reproducible final evidence.
Use the shared `src/eval/eval.py` for classification metrics. For N3-specific
analysis select the corresponding anchor positives and account for reciprocal
exchange dependence as in `src/eval/controls.py`.

Changes to rows, labels or splits require a new version and manifest. Keep this
snapshot available for reproducibility. OOD and cross-source tests are separate
artifacts and are outside this main-domain freeze.
