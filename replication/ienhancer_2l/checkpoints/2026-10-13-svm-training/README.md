# Trained two-layer SVM reconstruction · 13 October 2026

Both models and the five-outer / three-inner grouped evaluation are complete. The parameter-search protocol was committed before fitting as `9275f63`; this is **not** a reproduction of the original paper's leave-one-out evaluation.

| Task | Outer-fold mean accuracy | Conditional 95% interval | Mean ROC AUC |
| --- | ---: | ---: | ---: |
| Enhancer / non-enhancer | 76.21% | 74.64–77.90% | 0.841 |
| Strong / weak, known enhancers only | 60.98% | 58.38–63.73% | 0.668 |

Intervals resample whole groups within each outer fold. They condition on fitted models and saved folds, without refitting; ROC AUC is averaged across within-fold rankings. The second task is not overall two-stage cascade accuracy.

- `training_audit.json`: protocol, source and input hashes, package versions, complete metric summaries, runtime and all generated artifact hashes.
- `layer*_held_out_predictions.csv`: one held-out prediction per eligible sequence, with group, fold, truth, predicted label and decision score.
- `layer*_outer_*_search.json`: every candidate's three inner-fold scores and solver iterations. `layer*_outer_*_result.json` records the chosen setting and outer evaluation.
- `layer*_final_search.json`: separate five-fold searches used to select full-data model settings. These search scores are not independent test results.
- `layer*_summary.json`: metrics, group-bootstrap intervals, outer-fold settings and final-model metadata.
- `models/layer*_outer_*.npz`: ten fold-specific numeric models, retained for held-out replay.
- `models/layer1_final.npz`, `models/layer2_final.npz`: final models trained on 2,968 and 1,484 records. Safe numeric arrays with no pickle; include support-record IDs and feature metadata.
- `environment-lock.txt`, `validation.json`: exact dependency versions and implementation checks, including the initial numerical export-check failure and its resolution.

Final settings are C=32768 / gamma=0.0078125 for layer I, and C=2048 / gamma=2 for layer II. The first model's C reaches the grid boundary; the search was not expanded after seeing outer results. Neither the historical contaminated test nor lentiMPRA data was used.

See the [rerun and prediction commands](../../README.md) and [frozen scientific protocol](../../training_protocol.json). Remaining work includes GC-only/k-mer baselines, feature-counting sensitivity, historical-protocol reproduction and experimental transfer. The original strong/weak labels are not measured high/low reporter activity.
