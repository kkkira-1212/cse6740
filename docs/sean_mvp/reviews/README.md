# Initial human review records

## Current d40b8f3 view

- `ID_review_current_d40b8f3.csv`: current 200-row ID view; 39 changed N2 inputs use the new review, 61 unchanged N2 and all 100 unchanged N3 image/text inputs reuse initial judgments. Splits come from current items.
- `N2_recheck_d40b8f3_completed.csv`: complete 39-row recheck export, including dataset/commit/group identifiers; 28 mismatch, 8 match, 3 uncertain. Source upload hash in `current_review_summary.json`.
- `ID_N3_retained_current.csv`: the 100 individually accepted N3 pairs with current splits. Use this instead of the historical retained ID table.
- `current_review_summary.json`: combined counts, alignment and structural checks. Current N2 is 59 mismatch, 35 match, 6 uncertain. These are reviewer judgments, not independently adjudicated ground truth. The 39 changed-only cases are not a random new sample.
- `historical_*_bd3.*`: prior sample, offline-page manifest, validation and provenance. Original `ID_review_completed.csv`, initial summaries and retained tables remain historical bd3 records. OOD selection/group IDs were rerun against current items and are identical.

The two cases in `n2_adjudication_queue.csv` did not change inputs and were not in the 39-row recheck; they remain pending. Neither their labels nor the historical records were silently overwritten.

## Historical initial review

These files preserve Sean's 200 ID and 60 OOD judgments. They are initial review data, not independently adjudicated ground truth. The original sample files remain blank templates.

- `ID_review_completed.csv` / `OOD_review_completed.csv`: original judgment values, normalized to UTF-8 and LF for git; uploaded-byte hashes in `review_sources.json`.
- `initial_review_summary.json`: counts and initial match-flag rates. The legacy `false_negative_rate` key is computed from these judgments; interpret N2 as preliminary flag rates pending adjudication.
- `ID_N3_retained_initial_review.csv` / `OOD_N3_retained_initial_review.csv`: 100 / 19 N3 negatives retained under the initial review, with original splits. These files contain negatives only.
- `n2_adjudication_queue.csv`: two specifically observed disagreements needing a second reviewer decision. Labels are not silently changed; this is not an exhaustive dispute list.
- `upstream_n2_diagnostics.json`: deterministic structural issues in the upstream ID N2 table, separate from subjective review disagreements.

N3 acceptance does not establish absence of text-only shortcuts: the MVP substitutes only four simple target colors and undercovers complex color names. No text-only control has been run. Other N3 candidates remain unreviewed. Near/far OOD category choices remain provisional; no OOD threshold tuning or training is permitted.
