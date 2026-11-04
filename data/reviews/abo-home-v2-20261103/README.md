# N2 Human-Review Batch

Batch ID: `6f34fd22854c0ca8157f`. Source release: `abo-home-v2-20261103`.

**[Download the offline review ZIP](https://github.com/kkkira-1212/cse6740/releases/download/abo-home-v2-20261103/n2-home-v2-100-review.zip).** Open `N2_v2_review.html` in a modern browser. All 100 images are embedded; no server, network connection or API key is needed.

For each displayed image/title, select a clear mismatch, a title that still matches, or uncertain. Omitted details alone do not establish mismatch. Add reasons, particularly for match/uncertain decisions. Back up progress as JSON and export the completed CSV. Filters affect display only; export retains the whole batch, including pending rows.

The 100 rows are sampled from the exact train N2 pairs in the main release, approximately proportional to category counts: CHAIR 21, RUG 19, TABLE 13, WALL_ART 13, SOFA 10, HOME_FURNITURE_AND_DECOR 7, STOOL_SEATING 5, OTTOMAN 5, PILLOW 4, HOME 3. All decisions are initially blank. No val/test labels or model scores were used for audit selection.

Tracked files here contain only the blank sample and provenance. The ZIP also contains review instructions and a standalone `summarize_review.py` that validates exported IDs, batch identity and immutable input fields. Report pending/uncertain counts separately. The match-flag rate is a reviewer statistic, not independently adjudicated population ground truth. Do not treat a reviewed sample as certification of all generated negatives.

Do not import backups from the previous furniture-only prototype batch. Refer to [the main release](../../releases/abo-home-v2-20261103/README.md) for data-generation rules and model usage.

## Completed train audit

Yichi completed this exact 100-row batch. `review_completed.csv` preserves all
original judgments and comments; `review_summary.json` is validated against the
blank sample's immutable source fields. Results: **94 mismatch, 1 match,
5 uncertain, 0 pending**. Among determinate judgments, the match-flag rate is
1/95 (1.05%); uncertainty is 5/100. These are sample reviewer statistics, not
a certified population noise rate. No release labels, split tables or manifests
were overwritten, and no val/test judgments were used to tune rules.

A separate [reciprocal N3 development review](../n3-reciprocal-dev-v1/README.md)
records the color-shortcut mitigation experiment and its accepted subset.
