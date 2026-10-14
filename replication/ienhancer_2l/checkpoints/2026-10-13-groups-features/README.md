# Evaluation groups and PseKNC features · 13 October 2026

This checkpoint completes the grouping and sequence-feature stage, **not model training or reproduction of published accuracy**. Follow the [workspace instructions](../../README.md) to regenerate the outputs.

| Artifact | Purpose |
| --- | --- |
| `checkpoint.json` | Run commands, artifact/source hashes, scope and limitations. |
| `reference_receipts.json` | All 2,968 benchmark intervals matched hg19 in forward orientation; per-record sequence hashes, UCSC URLs and retrieval times. |
| `evaluation_assignments.csv` | 2,451 groups and frozen 5-outer / 3-inner folds. `inner_fold_outer_N = -1` means the record is in outer fold N's test set. Indices begin at zero. |
| `group_edges.csv` | 1,321 genomic-proximity edges and 12 sequence-similarity edges; a pair may qualify for both reasons. See the [policy](../../evaluation_policy.json) for exact thresholds. |
| `evaluation_audit.json` | Group sizes, class counts per fold, and zero edges crossing any outer/inner boundary. |
| `features_audit.json` | Feature parameters, five variants, matrix shapes and hashes, rounding comparison, environment and source hashes. |
| `validation.json` | Seventeen passing tests and full-run alignment, numerical and repeatability checks. |
| `environment-lock.txt` | Packages in the isolated Python 3.14.3 environment used for this run. |

The five feature archives remain local in `replication/ienhancer_2l/output/2026-10-13-groups-features/`. The checked-in inputs and receipts support offline regeneration. Each archive contains two float64 matrices with 4,105 columns: 2,968 rows for identification and 1,484 known-enhancer rows for strength classification. Join record IDs to the saved fold table, rather than assuming the two layers have identical row positions.

Whole-group folds address the declared proximity/edit-distance criteria. They are not the paper's leave-one-out protocol and do not establish complete independence. The historical 400-record test is excluded. The implemented feature equations pass numerical checks, but the author's counting convention remains unresolved; no variant has been selected using prediction accuracy.
