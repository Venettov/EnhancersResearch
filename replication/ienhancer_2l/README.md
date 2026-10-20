# iEnhancer-2L reproduction workspace

Step-by-step technical guide, software/data-flow diagram, and code-folder map: [English](https://venettov.github.io/EnhancersResearch/methods.html) · [Español](https://venettov.github.io/EnhancersResearch/es/methods.html). Research findings: [English](https://venettov.github.io/EnhancersResearch/reproduce.html) · [Español](https://venettov.github.io/EnhancersResearch/es/reproduce.html).

Data preparation, grouped evaluation, PseKNC features and **both trained RBF SVM classifiers** are implemented. The first nested evaluation is complete. Counting ambiguities, missing original SVM settings and a different evaluation design still prevent a claim of exact author-code or published-performance reproduction.

The 17 October 2026 review release includes the comparison source code, compact checkpoints, and [bilingual website explanations and evidence downloads](https://venettov.github.io/EnhancersResearch/reproduce.html#block-results). Links into `output/` refer to full local run artifacts, which remain excluded from Git; the website and checkpoint links are the public reading copies. Frozen protocols retain their original local-only instructions as historical records.

## Author-server example agreement · 19 October 2026

The deployed author server and our existing final models matched on all **13** 200-base windows from its five public example queries: nine strong, two weak, and two non-enhancer predictions. No retraining or tuning was performed. Nine overlapping windows come from the first query; four windows exactly match training sequences. This is a functional agreement check, **not proof of complete reproduction or independent accuracy**. The server returned class labels without numeric decision scores.

[Results and downloadable sequences/predictions](https://venettov.github.io/EnhancersResearch/reproduce.html#server-examples) · [Compact evidence record](checkpoints/2026-10-19-author-server-examples.json) · [Replay instructions](https://venettov.github.io/EnhancersResearch/methods.html#server-example-replay).

## Local training-only block balance · 14 October 2026

This follow-up is **complete**. The [block protocol](block_protocol.json) was frozen before fitting, after the scale-aware results were known. It tests whether the nine structural summaries help when their aggregate distance contribution is balanced with the 4,096 ordinary word frequencies. The four previous scale-aware models are verified, unchanged controls; two balanced representations are newly fitted.

| Representation | Identification accuracy | Strong/weak accuracy | ROC AUC, layer I / II |
| --- | ---: | ---: | ---: |
| Ordinary 6-mers · F, saved control | 75.91% | 62.80% | 0.8394 / 0.6800 |
| Rescaled words · F/Z, saved control | 76.08% | 61.86% | 0.8361 / 0.6616 |
| Words + summaries · [F,T], saved control | 76.15% | 62.13% | 0.8375 / 0.6788 |
| Full PseKNC · [F,T]/Z, saved control | 75.88% | 59.37% | 0.8361 / 0.6457 |
| Words + summaries, balanced blocks | **75.94%** | **63.14%** | **0.8381 / 0.6800** |
| Full PseKNC, balanced blocks | **75.24%** | **61.19%** | **0.8381 / 0.6612** |

**Balancing makes the unrescaled structural model competitive with words alone, but does not establish an added predictive benefit.** Its strength accuracy is only **+0.34 percentage points** above words (paired conditional 95% interval **−1.86 to +2.57**); the AUC difference is approximately zero (−0.00003; −0.01741 to +0.01773). The models still disagree on 273/1,484 strength predictions, so similar aggregate scores do not imply identical behavior or equivalence.

Relative to its unbalanced version, words+summaries gains **+1.01 points** (−0.02 to +2.00) for strength. Balancing full PseKNC raises strength accuracy from **59.37% to 61.19%**, a **+1.82-point** change (+0.16 to +3.44), and AUC by +0.0156 (+0.0034 to +0.0282). It still trails ordinary words by 1.61 points (difference −1.61; −4.01 to +0.91), and adding balanced summaries after rescaling does not clearly improve on rescaled words alone (−0.67 points; −3.07 to +1.67). These intervals are pointwise and exploratory, without multiple-comparison correction.

For identification, balanced words+summaries remains near words alone: +0.03 points (−1.02 to +0.96). Balanced full PseKNC falls from 75.88% to 75.24% (−0.64 points; −1.23 to −0.10), while its AUC difference remains uncertain. Accuracy and ranking performance need not move together; balancing is not universally beneficial.

**What was balanced:** in each inner-training subset, calculate the exact mean squared pair distance `q_b` separately for the word and structural blocks, excluding the diagonal but retaining duplicate-pair zeros. Divide each block's coordinates by `sqrt(q_b)`. Each block then contributes **50% of the aggregate training-pair squared distance**, not 50% for every pair or equal predictive information. In the five strength outer-training sets, structural summaries originally contributed **93.26–93.61%** before Z rescaling and **75.54–77.98%** afterward. The new balance changes these to 50% each. It can reduce numerical dominance without adding information, and can also amplify noise. These are fixed-table sequence summaries, not measured DNA structures.

After balancing, compute the median combined training-pair distance `m` and use `exp(-alpha * (D_F/q_F + D_T/q_T) / m)`. Both q values and m are refitted separately inside each inner-training subset; after inner selection, they are refitted using outer-training rows only. Validation/test records never fit these statistics. The 5 outer / 3 inner grouped folds, solver, feature definitions, and 90-setting C/alpha grid are unchanged. No per-coordinate standardization, block-weight tuning or post-result grid expansion is added. Single-block scaling cancels under median normalization, allowing reuse of the word-only controls.

No new unrescaled balanced model selects a C/alpha endpoint. Balanced full PseKNC reaches maximum C in one fold per layer (zero-based fold 1 for identification and fold 3 for strength); no selected alpha reaches an endpoint. The analysis therefore retains finite-search limitations. Equal balance is a specified diagnostic, not an established optimum. No replacement or new full-data model is selected.

The [plain-language explanation](output/2026-10-14-block-balance/interpretation.html), [full report](output/2026-10-14-block-balance/report.html), [summary CSV](output/2026-10-14-block-balance/block_summary.csv), [paired contrasts](output/2026-10-14-block-balance/block_contrasts.csv), [audit](output/2026-10-14-block-balance/block_audit.json) and [validation](output/2026-10-14-block-balance/validation.json) are local artifacts ignored by Git. The [compact checkpoint](checkpoints/2026-10-14-block-balance.json) retains protocol, results, fold scales, source/input hashes and delivery hashes outside that folder. Earlier archives and checkpoints remain unchanged.

**Verification:** all **57 scientific tests passed**. The run completed **5,420 new fits** and saved **20 new outer models**, plus 40 unchanged control copies. Independent validation recomputed all **80 training-only scaler fits**, using sample variances as an independent route to the pair-distance means, and checked all **26,712 held-out prediction rows** from raw sequences. Every predicted class agrees; maximum replay score error is about 8.70e-8. All 181 original run artifacts, 183 inputs and 30 source snapshots pass hash checks; paired group-bootstrap intervals are reproduced.

The 1,000-resample intervals are conditional on saved folds/models, omit retraining and protocol-selection uncertainty, and do not make repeated use of this benchmark an independent confirmation. Historical strong/weak labels are distinct from lentiMPRA activity. No contaminated historical-test or `NEW_2026_DATA` records were fitted; original author-code and numerical reproduction remain unresolved. Confirmation requires a separately specified evaluation with suitable independent records and targets.

```sh
.venv/bin/python -m unittest discover -s replication/ienhancer_2l -p 'test_*.py' -v
.venv/bin/python replication/ienhancer_2l/compare_blocks.py --output replication/ienhancer_2l/output/new-block-run --workers 8
.venv/bin/python replication/ienhancer_2l/validate_blocks.py replication/ienhancer_2l/output/new-block-run
```

The runner requires the verified scale-aware archive and checkpoint, plus frozen preparation/features inputs, and refuses a nonempty output directory. A fresh checkout must regenerate ignored prerequisite archives first. The fits took approximately 21 seconds on the recorded machine; verification and report preparation are additional. New NPZ files use **`kernel_format=block_rbf_v1`**, retain raw support vectors and both block scales, and must be replayed with **`compare_blocks.block_scores`** on the matching raw feature representation. The older plain-RBF `portable_scores` and default prediction CLI do not implement this block kernel; the original final models remain unchanged.

## Local scale-aware comparison · 14 October 2026

The next comparison is **complete**. The [scale-aware protocol](scale_protocol.json) was frozen before these fits, after the earlier component results were known. All four representations retain the same feature definitions and frozen grouped evaluation.

| Representation | Identification accuracy | Strong/weak accuracy | ROC AUC, layer I / II |
| --- | ---: | ---: | ---: |
| Ordinary 6-mers · F | 75.91% | 62.80% | 0.8394 / 0.6800 |
| Rescaled words · F/Z | 76.08% | 61.86% | 0.8361 / 0.6616 |
| Words + structural summaries · [F,T] | 76.15% | 62.13% | 0.8375 / 0.6788 |
| Full PseKNC · [F,T]/Z | 75.88% | 59.37% | 0.8361 / 0.6457 |

**Ordinary words remain ahead of full PseKNC for strength, while the gap with unrescaled structural features is now much smaller.** Words minus full: **+3.44 percentage points** (paired conditional 95% interval +1.04 to +5.75), AUC +0.0343 (+0.0127 to +0.0567). Words minus words+summaries: **+0.67 points** (−1.52 to +2.79), AUC +0.0013 (−0.0164 to +0.0186). Words minus rescaled words: +0.94 points (−0.84 to +2.94), AUC +0.0184 (+0.0024 to +0.0347). Intervals crossing zero do not prove equivalence. These are exploratory, uncorrected comparisons on a repeatedly used benchmark.

Words+summaries improve from 60.45% to 62.13% strength accuracy under the changed search (+1.68 points, −0.15 to +3.55); AUC improves by +0.0237 (+0.0074 to +0.0380). Ordinary words change from 63.68% to 62.80%. Full PseKNC changes from 60.98% to 59.37% (−1.62 points, −3.85 to +0.78); AUC decreases by −0.0220 (−0.0411 to −0.0024). Tuning affects the earlier comparison, but these results do not isolate a biological mechanism or establish that structural summaries are unhelpful. All identification accuracies remain near 76%, without a clear ordinary-word accuracy advantage.

For each inner-training split, **m is the exact median squared Euclidean distance over all unordered pairs of distinct training records**, retaining off-diagonal zeros and excluding the diagonal. The kernel is `exp(-alpha * distance² / m)`, equivalent to raw-feature `gamma = alpha / m`. The outer refit recomputes m on outer-training records only. Validation/test records never enter m. No per-coordinate/block scaler or structural-weight selection is added. This cancels uniform changes of units, but leaves relative block geometry and per-sequence Z effects intact.

Every representation receives **90 C/alpha settings**: the original six C values and alpha = 2 raised to −19, −17, …, 9. Selection uses mean three-fold inner balanced accuracy, then smaller C and smaller alpha for exact ties. This differs from the earlier 48-setting raw-gamma search in density and candidate locations; it is not a strict superset and cannot isolate normalization alone. A denser search need not improve held-out scores.

No selected alpha hits an endpoint. Words+summaries hit maximum C in three strength folds and one identification fold; full PseKNC hits it in two identification folds. The grid is not expanded after results. No winner or replacement full-data model is selected. Training-only block scaling was the proposed follow-up at this checkpoint and is now reported above. Confirmation still needs an untouched evaluation. The historical labels remain distinct from lentiMPRA activity; no new experimental data were fitted.

The [plain-language interpretation](output/2026-10-14-scale-aware/interpretation.html), [full report](output/2026-10-14-scale-aware/report.html), [summary CSV](output/2026-10-14-scale-aware/scale_summary.csv), [contrasts CSV](output/2026-10-14-scale-aware/scale_contrasts.csv), [audit](output/2026-10-14-scale-aware/scale_audit.json) and [validation](output/2026-10-14-scale-aware/validation.json) are local artifacts ignored by Git. The [compact checkpoint](checkpoints/2026-10-14-scale-aware.json) retains protocol, summaries, paired intervals and verification outside that folder. Source snapshots, settings, training IDs, numeric models and hashes preserve the run.

**Validation:** 48 tests passed; 10,840 new fits, 40 new outer models, 80 model files including unchanged reference copies, 40 complete searches, 160 training-only medians, and all 35,616 stored held-out predictions checked. Raw-sequence replay matches all predicted classes; maximum score difference is approximately 1.10e-7. All 265 original run artifacts, 123 input hashes and 26 source snapshots passed checks. Bootstrap intervals were recomputed with the same paired group draws. They omit retraining/protocol-selection uncertainty and are pointwise, conditional and unadjusted for multiple comparisons.

```sh
.venv/bin/python -m unittest discover -s replication/ienhancer_2l -p 'test_*.py' -v
.venv/bin/python replication/ienhancer_2l/compare_scale.py --output replication/ienhancer_2l/output/new-scale-run --workers 8
.venv/bin/python replication/ienhancer_2l/validate_scale.py replication/ienhancer_2l/output/new-scale-run
```

The runner requires the completed component archive and its compact checkpoint, plus the earlier preparation/features inputs. A fresh checkout must regenerate ignored prerequisite archives first. It verifies the previous delivery manifest, rejects a nonempty output directory and preserves prior models. The run took approximately 36 seconds on the recorded machine; validation and report preparation are additional.

## Local structural-component comparison · 14 October 2026

The follow-up now separates the nine structural coordinates from the per-sequence PseKNC denominator. It is **complete**. The [component protocol](component_protocol.json) was frozen before the new fits, after the earlier baseline results were known. It is exploratory reuse of the same benchmark.

Let **F** be the 4,096 overlapping word frequencies, **T = w × theta** the nine weighted property summaries, and **Z = sum(F) + w × sum(theta)**. The same Z is used in both rescaled arms; F/Z still contains sequence-derived structural information through its denominator. We retain w=0.1 for identification and w=0.4 for strength. These summaries are calculated from the fixed dinucleotide-property table, not measured three-dimensional structures.

| Representation, with inner-fold retuning | Identification accuracy | Strong/weak accuracy | ROC AUC, layer I / II |
| --- | ---: | ---: | ---: |
| Words only · F | 75.91% | 63.68% | 0.8379 / 0.6878 |
| Rescaled words · F/Z | 76.58% | 61.18% | 0.8417 / 0.6601 |
| Words + structural coordinates · [F,T] | 75.71% | 60.45% | 0.8360 / 0.6551 |
| Full PseKNC · [F,T]/Z | 76.21% | 60.98% | 0.8412 / 0.6677 |

For strength classification, rescaling words alone changes accuracy by **−2.50 percentage points** (paired conditional 95% interval −4.62 to −0.50), while adding structural coordinates without rescaling changes it by **−3.23 points** (−5.68 to −0.78). Adding coordinates after rescaling changes accuracy by −0.20 points (−2.80 to +2.40). The effects cannot be added: accuracy interaction is +3.03 points (−0.28 to +6.34), and AUC interaction is +0.0403 (+0.0160 to +0.0664). The full-versus-words result reuses the verified previous evaluation; it is not an independent confirmation.

**Tuning changes the rescaling conclusion.** With the same primary C/gamma in all arms within each fold, strength accuracies are 61.59%, 62.33%, 57.62% and 60.98%, respectively. Rescaling words then changes accuracy by +0.75 points (−1.70 to +3.19), and rescaling words plus coordinates by +3.37 (+0.70 to +6.63). These primary-selected settings favor the reference representation; the comparison diagnoses tuning sensitivity. In the retuned strength searches, F/Z reaches maximum gamma in four folds and [F,T] reaches maximum C in three. Identical numeric grids do not provide equivalent effective search coverage at different feature scales.

The nine coordinates account for 93.5% of total sampled squared feature distance before rescaling and 77.2% afterward in layer II (20,000 deterministic, label-free sampled pairs). Median Z is 7.01. This provides a numerical explanation to investigate, not proof of a sole cause or a biological mechanism. Layer I shows no accuracy-contrast interval excluding zero among the retuned models. At this checkpoint, a scale-aware search or training-only block scaling was a proposed follow-up. Both are now reported above. No replacement model was selected at this component checkpoint.

The [plain-language interpretation](output/2026-10-14-component-ablation/interpretation.html), [full results](output/2026-10-14-component-ablation/report.html), [summary CSV](output/2026-10-14-component-ablation/component_summary.csv), [paired contrasts](output/2026-10-14-component-ablation/component_contrasts.csv) and [validation](output/2026-10-14-component-ablation/validation.json) are local artifacts under `output/2026-10-14-component-ablation/`, ignored by Git. The audit preserves feature matrices, predictions, source snapshots, settings, environment and SHA-256 hashes. Existing reference model files are copied unchanged and retain their original metadata; only new fits carry the component-protocol hash. The delivery manifest additionally covers interpretation, tests and validation files written after the run.

The compact [component checkpoint](checkpoints/2026-10-14-component-ablation.json) retains the protocol, metrics, paired contrasts, geometry and verification summary outside the ignored output folder, ready for review with the code. It records the full local audit and delivery-manifest hashes.

The run made **2,930 new fits**, saving **50 new outer-fold models**. All **40 tests** pass. Read-only validation checks 241 original run-artifact hashes, 65 input hashes, 80 model files including reference copies, 20 complete inner searches, and all **35,616 held-out prediction rows** rebuilt from raw sequences. Replayed classes agree exactly; maximum score difference is approximately 1.10e-7. All paired contrasts, intervals and geometry summaries are recomputed. Original inputs and models are preserved; no final full-data model is fitted.

```sh
.venv/bin/python -m unittest discover -s replication/ienhancer_2l -p 'test_*.py' -v
.venv/bin/python replication/ienhancer_2l/compare_components.py --output replication/ienhancer_2l/output/new-component-run --workers 8
.venv/bin/python replication/ienhancer_2l/validate_components.py replication/ienhancer_2l/output/new-component-run
```

The runner requires the previous verified baseline archive as well as the frozen preparation, feature and training checkpoints; a fresh checkout must regenerate the ignored archives first. It refuses a nonempty output directory. The 1,000 paired whole-group bootstrap intervals are pointwise, conditional on fitted models/folds and unadjusted for multiple comparisons. No historical test or `NEW_2026_DATA` records are used. Historical strong/weak annotations remain a different target from lentiMPRA activity.

## Local baseline and feature-sensitivity review

This stage is **complete**. The [comparison protocol](comparison_protocol.json) was recorded before the comparison fits, after the primary SVM results were known. It is an exploratory analysis, not a preregistration or a new independent test set. The original saved models, inputs, groups and historical checkpoints are preserved.

### Results for review

| Representation | Enhancer / non-enhancer accuracy | Strong / weak accuracy | ROC AUC, layer I / II |
| --- | ---: | ---: | ---: |
| Primary PseKNC reference | 76.21% | 60.98% | 0.841 / 0.668 |
| Majority class | 49.97% | 49.87% | 0.500 / 0.500 |
| GC only | 75.13% | 61.79% | 0.828 / 0.645 |
| Ordinary overlapping 6-mers | 75.91% | 63.68% | 0.838 / 0.688 |
| Disjoint windows, retuned | 73.08% | 59.57% | 0.808 / 0.625 |
| Per-word non-overlap, retuned | 76.25% | 60.71% | 0.845 / 0.663 |
| Rounded property table, retuned | 76.15% | 60.98% | 0.841 / 0.667 |
| Population SD, retuned | 76.08% | 61.46% | 0.842 / 0.668 |

**Simpler baselines are competitive.** Ordinary 6-mers differ from primary by −0.30 percentage points in layer I (paired conditional 95% interval −1.27 to +0.65) and +2.69 points in layer II (+0.10 to +5.15). The layer-II interval is exploratory and unadjusted for multiple comparisons; it is not a confirmed general advantage. GC-only accuracy differs by −1.08 points (−2.38 to +0.06) and +0.81 points (−2.38 to +3.77), respectively. Primary has a higher layer-I AUC than GC only (0.841 versus 0.828; comparator-minus-primary AUC interval −0.0209 to −0.0048). Conclusions depend on the metric; similar accuracy does not establish equivalent classifiers.

**The counting interpretation matters.** Disjoint windows reduce layer-I accuracy by 3.13 points with retuning, and by 5.52 points when keeping primary parameters. For layer II, the decreases are 1.41 and 2.96 points. Small aggregate changes can hide disagreement: retuned per-word counting changes **41/2,968** layer-I predictions and **106/1,484** layer-II predictions despite similar accuracy. Retuned ordinary 6-mers change **229** and **336** predictions, respectively. Retuned rounding changes just **4** and **2**; population SD changes **22** and **27**. None of these results identifies which counting implementation the authors used.

The original model is retained. These results support carrying a simple 6-mer baseline into further planned comparisons; they do not select a replacement from the outer scores, reproduce the paper's leave-one-out evaluation, or validate experimental transfer. The component comparison above now follows this checkpoint and separates the nine correlation coordinates from the PseKNC denominator.

### Methods and files

| Comparison | Question | Implementation |
| --- | --- | --- |
| Majority class | What happens without using DNA at all? | Predict the outer training set's majority label; ties choose 0. |
| GC only | How informative is overall G/C composition? | One sequence-level fraction, with an RBF SVM tuned inside training folds. |
| Ordinary 6-mers | Are DNA word frequencies sufficient for comparable performance? | 4,096 overlapping 6-mer frequencies; no property correlations or PseKNC denominator. |
| Disjoint windows | Does interpreting “non-overlapping” as a tiling matter? | Starts at 0,6,12,…; 33 windows, leaving the incomplete tail out. |
| Per-word non-overlap | Does avoiding overlap within each identical word matter? | Each word is counted with `str.count`; different words can still overlap. |
| Published rounded table | Does using the printed S2-2 values matter? | Use the two-decimal property table directly. |
| Population SD | Does a different property-table normalization matter? | Population rather than sample standard deviation. |

Every SVM uses the existing five outer / three inner group assignments and the original 48-setting C/gamma grid. Each feature variant is evaluated twice: once with inner-fold retuning and once with the primary model's parameters for that same outer fold. The latter changes the feature representation at fixed parameters; it is not an independently optimized competitor. The GC and ordinary 6-mer baselines are retuned. No feature variant is selected by outer-fold performance, and no new full-benchmark deployment model is fitted.

The ordinary 6-mer baseline removes both the nine correlation terms **and** the sequence-dependent PseKNC denominator. Its comparison cannot isolate the causal contribution of the nine terms alone. Likewise, strong GC-only performance would demonstrate a predictive association with composition, not a biological mechanism or proof that the primary classifier relies only on GC.

The completed local run is saved in `output/2026-10-13-baselines-sensitivity-verified/`. Its `report.html`, `comparison_summary.csv`, `comparison_audit.json` and `validation.json` provide the results. Every method/layer directory contains held-out predictions, parameter searches where applicable, and numeric outer-fold models. Source/protocol snapshots, SHA-256 hashes and the environment lock preserve the execution record. Large generated run artifacts remain ignored by Git.

The verified run contains **8,740 SVM fits**, **100 saved outer-fold SVM models**, 10 majority-rule fold evaluations and 12 result rows per classification layer including the primary reference. It took approximately **9.2 minutes** with eight fit workers on this machine, excluding the earlier interrupted attempt. All **34 tests** pass. Post-run validation checks 53,424 prediction rows, all 100 model identities/training membership, all 60 parameter searches and 600 raw-sequence replay predictions (maximum score difference approximately 6.75e-8). The reference bootstrap intervals also match the earlier checkpoint.

An initial attempt in `output/2026-10-13-baselines-sensitivity/` was stopped after two completed GC-only folds because gamma-batched scheduling left a long single-worker tail. Its partial artifacts and source snapshot are retained. The completed run schedules individual inner fits, without changing the protocol, candidate grid, solver or selection rules. Unit tests verify identical search results; the completed real-data searches shared by the two runs also agree exactly. This is an execution change, not a change chosen from held-out performance.

Accuracy, balanced accuracy, ROC AUC, MCC, sensitivity, specificity and average precision are reported by fold and as equal-weight fold means. Ranking metrics stay within folds. Whole groups are resampled 1,000 times within each outer fold, using the same draws for every method. Pointwise 95% intervals are saved for accuracy, balanced accuracy, AUC and their paired differences from primary. These conditional intervals exclude retraining and protocol-selection uncertainty, are not adjusted for multiple comparisons, and do not establish equivalence when they cross zero. Individual prediction disagreements and search-boundary selections are reported alongside aggregate scores.

Run from the repository root after preparing the original five feature archives:

```sh
source .venv/bin/activate
python -m unittest discover -s replication/ienhancer_2l -p 'test_*.py' -v
python replication/ienhancer_2l/compare_features.py --output replication/ienhancer_2l/output/new-comparison-run --workers 4
```

The output directory must be new or empty. The runner reuses the pinned training environment and verifies alternate matrices against the frozen feature audit. The GC-only grid can take substantially longer to converge than the original PseKNC fits. It uses the same solver tolerance without an iteration cap; no grid is expanded after viewing results. The original paper's benchmark-wide feature selection and imperfect biological independence of the grouping remain limitations. The contaminated historical test and all `NEW_2026_DATA` measurements remain excluded.

## SVM training checkpoint · 13 October 2026

The [training protocol](training_protocol.json) was committed as `9275f63` **before model fitting**. It fixes the primary feature interpretation, no additional scaling, 48 C/gamma combinations, balanced-accuracy selection, tie breaking and the reporting rules. The [checkpoint folder](checkpoints/2026-10-13-svm-training/) contains the complete searches, held-out predictions, ten outer-fold models, two final models, metrics and provenance. Original sequence files and the earlier checkpoints are unchanged.

| Task | Held-out sequences | Mean accuracy | Conditional 95% interval | Mean MCC | Mean ROC AUC | Mean average precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Layer I: enhancer / non-enhancer | 2,968 | **76.21%** | 74.64–77.90% | 0.527 | 0.841 | 0.838 |
| Layer II: strong / weak, known enhancers only | 1,484 | **60.98%** | 58.38–63.73% | 0.220 | 0.668 | 0.654 |

These are equal-weight means of the five outer-fold metrics. ROC AUC and average precision rank scores **within each fold**, then average, because raw scores from different fitted models need not be comparable. Average precision is the non-interpolated summary, not trapezoidal PR area. The intervals resample whole groups within each outer fold 1,000 times with seed 42. They are conditional on the fitted models and folds; they do not include retraining or uncertainty from choosing the research protocol. The saved summaries also contain pooled confusion counts and threshold metrics.

The paper's reported leave-one-out accuracies are 76.89% and 61.93%. Their numerical proximity to this run **does not establish reproduction**: our evaluation is grouped and nested, our C/gamma choices are reconstructed, and the original feature-counting convention remains unresolved. The strength result measures a separate task on known enhancers, not overall cascade accuracy. It also indicates substantially weaker discrimination than layer I. No lentiMPRA data or contaminated historical-test records entered fitting or tuning.

### What was trained

- For each layer and outer fold, search 6 values of `C = 2**[-5,-1,3,7,11,15]` and 8 values of `gamma = 2**[-15,-11,-7,-3,1,5,9,13]` using only the three saved inner folds. Select the greatest mean balanced accuracy; exact ties favor smaller C, then smaller gamma. Fit on that outer training set and predict its held-out fold exactly once.
- Features are the primary, unscaled equation-6 vectors. Cached pairwise RBF kernels depend only on the two fixed vectors; they fit no population statistic. SVM inputs are sliced to training/training and validation/training rows. Tests confirm the cached kernel agrees with direct RBF SVC and outer-test label changes cannot alter inner selection.
- Use scikit-learn 1.9.1's LIBSVM-based SVC, tolerance `0.001`, shrinking enabled, no class weighting, no iteration cap, no probability calibration and no threshold tuning. Positive scores favor enhancer in layer I and strong in layer II. Decision values are **not probabilities or measured biological activity**.
- After nested evaluation, perform a separate five-fold search over the saved outer assignments to select settings for a full-benchmark model. That selection score is not a new held-out performance estimate. Layer I's final settings are **C=32768, gamma=0.0078125**, with 1,916 support vectors; layer II uses **C=2048, gamma=2**, with 1,278 support vectors. Each final model is fitted on all eligible benchmark rows.
- Layer I's final C and one outer-fold C hit the maximum of the predeclared search grid. This limitation is reported; the grid was not expanded after reviewing outer performance. The local baseline and counting-sensitivity comparisons above now follow this checkpoint.

The completed run contains **1,932 fits**, separate from small implementation tests. Every held-out record has an ID, group, true label, predicted label, raw decision score and outer-fold assignment. All fitted models converged. The 26-test suite includes saved-artifact hashes, split isolation and replay of held-out scores directly from original sequences. Final model exports reproduce every benchmark class prediction exactly. Largest score differences on reloading are approximately 1.17e-7 and 3.37e-9; the 1e-6 final-export tolerance accounts for different floating-point summation and remains much smaller than the solver tolerance. The initial run stopped on an overly strict 1e-7 export check; the numerical diagnosis and unchanged held-out predictions are recorded in `validation.json`.

### Run training or apply the saved models

From the repository root, using Python 3.12+ and an activated virtual environment:

```sh
python -m pip install -r replication/ienhancer_2l/requirements-training.txt
python -m unittest discover -s replication/ienhancer_2l -p "test_*.py" -v
# Prepare inputs and feature matrices with the commands below if absent.
python replication/ienhancer_2l/train_svm.py --output replication/ienhancer_2l/output/new-svm-run --workers 4
```

Training requires the primary feature archive from the feature-stage commands below. The output directory must be new or empty. Defaults use `output/2026-10-13-preparation/benchmark.csv` and `output/2026-10-13-groups-features/features_primary.npz`; `--prepared` and `--features` accept other locations. Inputs are checked against the frozen benchmark and primary matrix hashes. A changed matrix requires a separately documented checkpoint, not silently bypassing validation. Runtime depends on hardware; the recorded two-layer run took about 54 seconds after input loading, with four search workers and cached kernels.

Saved final models can be used without retraining or loading the large new-study data:

```sh
python replication/ienhancer_2l/predict_svm.py --fasta path/to/queries.fasta --output replication/ienhancer_2l/output/query_predictions.csv
```

Queries must be exactly 200 A/C/G/T bases. The command uses the checked-in final models, reports non-enhancer/weak/strong, and leaves the strength score blank when layer I is negative. This is an inference interface, not a validated experimental-transfer analysis. Test sequences that overlap the training benchmark cannot provide independent performance evidence. Models are compressed numeric `.npz` arrays loaded with `allow_pickle=False`, with feature metadata, support-record IDs and the protocol hash; no pickled estimator is required.

## Evaluation and features · 13 October 2026

The [evaluation policy](evaluation_policy.json) is fixed before training. It uses only the 2,968-record benchmark. The contaminated 400-record historical test does not contribute to grouping, fold balancing, feature matrices, or tuning.

The completed run recovered **2,451 groups** (largest: 20 records), with **1,321 genomic-proximity edges** and **12 sequence-similarity edges**. All 2,968 reference matches are in the forward orientation. No group contains conflicting class labels, and no recorded edge crosses any outer or inner fold boundary. Each outer fold contains 148–149 strong, 148–149 weak and 296–297 non-enhancer records. All five feature variants passed finite-value, nonnegativity, row-sum and serialization checks; the largest row-sum error was **4.45 × 10⁻¹⁶** or less. See the [saved audit](checkpoints/2026-10-13-groups-features/features_audit.json).

Counting ambiguity has a measurable effect: per-word non-overlapping counting changes 1,238 of 2,968 layer-I vectors relative to the primary interpretation; disjoint windows change every vector. The maximum layer-I entry differences are 0.03790 and 0.06065, respectively. This does not establish how much a future model's predictions will change.

The new grouped evaluation is separate from the paper's historical leave-one-out reconstruction:

1. Verify every benchmark interval against **hg19**, using the UCSC sequence API and zero-based, end-exclusive coordinates. A filename or a few matching samples is insufficient. Saved receipts bind each record, reference sequence hash, interval, retrieval time and URL. The original sequence orientation is preserved.
2. Connect records on the same chromosome if their intervals overlap or have a gap of at most **1,000 bases**. Also compare **every sequence pair in both orientations**, connecting pairs with global unit-cost Levenshtein edit distance at most **40** over the 200-base sequences. This captures exact matches, reverse complements, substitutions and short shifts/indels. It is a project rule, **not** a reimplementation of CD-HIT's percentage-identity criterion.
3. Take the transitive closure of these connections. For example, if A connects to B and B to C, all three stay together even if A and C do not directly pass the threshold. Conflicting labels remain visible and are not relabeled or dropped.
4. Assign whole groups to **5 outer folds**, then **3 inner folds within each outer training set**, with seed **42**. A deterministic greedy algorithm balances strong, weak and non-enhancer counts. Layer II retains the same assignments after selecting known enhancers. Outer test records have inner-fold value `-1`; they cannot take part in tuning for that outer fold.

These safeguards reduce specific kinds of leakage; they do not prove complete biological independence. The thresholds are predeclared project choices, not established biological boundaries. Short shared motifs and longer-range genomic correlation can remain. The paper's feature settings were selected on this benchmark, so holding them fixed also does not independently validate that earlier selection process.

### Reproduce the saved run

Use Python **3.12 or newer** for this stage (the recorded local run uses 3.14.3). Data preparation alone still needs only Python 3.10+ and the standard library. From the repository root in an activated virtual environment:

```sh
python -m pip install -r replication/ienhancer_2l/requirements-training.txt
python -m pip check
python replication/ienhancer_2l/prepare_data.py --output replication/ienhancer_2l/output/2026-10-13-preparation
python -m unittest discover -s replication/ienhancer_2l -p 'test_*.py' -v
python replication/ienhancer_2l/build_features.py --receipts replication/ienhancer_2l/checkpoints/2026-10-13-groups-features/reference_receipts.json --output replication/ienhancer_2l/output/2026-10-13-groups-features
```

The checked-in receipts permit offline reruns. To independently refresh all 2,968 reference lookups, first run:

```sh
python replication/ienhancer_2l/verify_reference.py --output replication/ienhancer_2l/output/fresh-reference
```

Then pass that directory's `reference_receipts.json` to `build_features.py --receipts`. Reference responses are cached for resuming interrupted requests; a fresh output directory makes fresh requests. A mismatch stops the reference check and is also rejected by the grouping code. Do not change the assembly or hashes simply to bypass a mismatch.

Derived matrices are ignored by Git; compact audits, receipts and fold assignments are versioned in `checkpoints/2026-10-13-groups-features/`. No 51 GB download is needed. The output directory is replaced on rerun, so use a new directory to preserve a separate run. The source hashes in the audit identify the exact executed scripts, including when a run preceded its commit.

### Feature specification and unresolved details

[`properties_s2.json`](properties_s2.json) transcribes the six columns of Supplement S2, preserving the printed names and order: Rise, Roll, Shift, Slide, Tilt, Twist. Both PDF pages were visually checked, and the source PDF hash is recorded. Normalization uses only this fixed 16-row table, never the benchmark distribution or labels.

- Primary reconstruction: **sample standard deviation (`ddof=1`)**, recomputed from S2-1. Its maximum difference from the rounded S2-2 table is **0.004724**, within rounding to two decimal places. Population standard deviation differs by up to **0.085217**, so it is retained only as a sensitivity variant. This supports the sample convention; it does not establish whether author code used rounded or full-precision values.
- Frequencies: count all overlapping length-6 windows, normalize by the number of windows (**195** for 200 bases), and use lexical `A,C,G,T` order. This is an explicit project interpretation. The paper's “non-overlapping” wording remains unresolved without an author implementation or reference vectors.
- Two additional counting variants are saved: `disjoint` takes starts 0,6,12,… and discards the incomplete tail (**33** windows); `per_word_nonoverlap` uses Python `str.count` separately for each observed word and normalizes by the total counts. The latter allows different words to overlap each other. Neither is asserted to be the author convention.
- All variants use position-based, overlapping dinucleotides for equations 7–8: at lag `j`, average the six squared property differences over **L − j − 1** pairs. The Figure 2 caption's conflicting wording remains documented.
- Equation 6 gives **4,105** entries: 4,096 frequencies followed by nine correlation terms, each divided by `sum(f) + w*sum(theta)`. Parameters are `k=6`, `lambda=9`, `w=0.1` for layer I and `w=0.4` for layer II. No learned scaler is applied. Any future model scaler belongs inside training folds.
- Five complete variants are exported: `primary`, `disjoint`, `per_word_nonoverlap`, `published_rounded` (S2-2 directly), and `population`. Each changes only the indicated primary choice. They are sensitivity analyses, not candidates to select using outer-test accuracy. Model-choice comparisons must remain within training folds.

The compressed `.npz` files contain `X_layer1` (2,968 × 4,105), `y_layer1`, `record_ids_layer1`, `X_layer2` (1,484 × 4,105), `y_layer2`, `record_ids_layer2`, and `feature_names`. Load with `numpy.load(path, allow_pickle=False)`. Positive labels are enhancer for layer I and strong for layer II. Join fold assignments by `record_id`, never by an assumed subset row position. Matrices use float64. Audits include file hashes, little-endian float64 array hashes, and differences between variants; tiny floating-point differences across environments should be assessed numerically rather than mistaken for scientific disagreement.

### Validation and next stage

Tests cover the printed normalized table, a hand-calculated short sequence, a separate scalar implementation of equations 6–9, constant-base sequences, both layer weights, reverse-complement symmetry, counting alternatives, malformed inputs, edit-distance boundaries, transitive groups, genomic proximity, invalid reference receipts, deterministic fold assignments, and outer/inner isolation. The full run additionally checks finite/nonnegative values, row sums, matrix serialization and every recorded grouping edge against all evaluation boundaries.

At the feature checkpoint, no model had been trained. The SVM stage above now follows it. Original labels are chromatin-based annotations, not lentiMPRA measurements. The later experimental comparison remains separate.

Sources: [iEnhancer-2L paper](https://doi.org/10.1093/bioinformatics/btv604), [Supplement S2](../../bioinformatics_32_3_362_s1/Supp-S2.pdf), [author benchmark page](https://bliulab.net/iEnhancer-2L/data/), [UCSC sequence API](https://www.genome.ucsc.edu/goldenPath/help/api.html), [RapidFuzz edit distance](https://rapidfuzz.github.io/RapidFuzz/Usage/distance/Levenshtein.html).

## Data preparation checkpoint · 13 October 2026

The first recorded preparation run completed successfully at source commit `eb559bc178f8fdc188b55fb3f6484c438b01ec6b`. The [checkpoint record](checkpoints/2026-10-13-data-preparation.json) preserves the input/output hashes, commands, environment, and verification results.

| Check | Result |
| --- | --- |
| Original sequence files, paper, and S1/S2 supplements | All seven match the reviewed file sizes and SHA-256 hashes. |
| Labeled benchmark | 2,968 unique sequences: 742 strong, 742 weak, 1,484 non-enhancers. |
| Sequence format | All 3,368 benchmark and historical-test records contain exactly 200 A/C/G/T bases. |
| Label exports | Binary labels, source pages, and historical overlap flags pass checks. Non-enhancers have no strength label. |
| Historical test | 400 records; 100 exact benchmark overlaps, all strong. Diagnostic use only. |
| Preparation tests | All four pass, including changed-input rejection and repeatability. |

The run used an isolated `.venv` with Python 3.14.3 and no additional packages. This differs from the guide's suggested Python 3.13 but satisfies the helper's Python 3.10+ requirement. It does not establish the environment for future model training. Labels were joined through the previously reviewed crosswalk; this run did not re-extract labels from the PDFs.

The local run is archived under `output/2026-10-13-preparation/`, including both CSV exports, the audit, Python version, source commit, and environment records. Derived outputs remain ignored by Git; the compact checkpoint above is versioned. A fresh checkout can regenerate the CSVs and deterministic data audit with:

```sh
python replication/ienhancer_2l/prepare_data.py --output replication/ienhancer_2l/output/2026-10-13-preparation
```

At this earlier checkpoint, only data preparation was complete and no model had been trained. The grouping, feature and SVM stages above follow it. Exact uniqueness alone does not establish independence from related sequences or overlapping loci; published performance has not been reproduced.

## Preparation workflow

From the repository root, with Python 3.10 or newer:

```sh
python replication/ienhancer_2l/prepare_data.py
python -m unittest discover -s replication/ienhancer_2l -p 'test_prepare_data.py'
```

The helper uses only the standard library. It checks original file bytes against the 12 October review, validates 200-base FASTA records, verifies row/header/sequence hashes against the reviewed crosswalk, and exports:

- `output/benchmark.csv`: 2,968 records, including recovered strong/weak labels and source pages. `non_enhancer` in the original crosswalk becomes `non-enhancer` in `class_label`. Strength is blank for non-enhancers, not zero.
- `output/legacy_test_diagnostic_only.csv`: 400 historical test records, with an exact training-overlap flag. This is not an independent test set or the first paper's leave-one-out benchmark. Test labels come from the current iEnhancer-EL S4 through the reviewed crosswalk.
- `output/data_audit.json`: counts, source/output hashes, and limitations.

Rerunning replaces those three derived files. Use `--output PATH` to keep separate runs. Outputs and `.venv` are ignored by Git. No original files are modified. Preserve byte-level line endings; a fresh clone can use `git clone --config core.autocrlf=false https://github.com/Venettov/EnhancersResearch.git`.

These checks do not establish independence from similar sequences, reverse complements, or overlapping loci. The 100 exact historical test overlaps are all strong enhancers. The original chromatin-based labels are not experimental lentiMPRA activity measurements.

## Screened author-server comparison · 19 October 2026

The unchanged saved models matched **192 of 200 final labels (96%)**, with eight differences. Inputs were fixed before predictions and drawn from Table S10 of [Agarwal, Inoue et al. (Nature, 2025)](https://doi.org/10.1038/s41586-024-08430-9): 185 HepG2 candidate enhancers and 15 promoters with usable annotated hg19 coordinates. All 2,968 known training sequences were screened in both orientations; no exact/reverse-complement or ≤40-edit match remained. The minimum observed training edit distance was 55, and annotated locus separation was at least 10,823 bases. These finite rules do not establish complete biological independence or expose the server's full training history.

The [checkpoint](checkpoints/2026-10-19-author-server-200.json) preserves the frozen policy and source hashes, model hashes, four server receipts, validation results, and screenshot provenance. [Results](https://venettov.github.io/EnhancersResearch/reproduce.html#server-comparison) shows original author screenshots, all eight disagreements, and downloadable inputs, raw responses, and comparison records. Three existing disagreements were resubmitted only to capture a compact illustration; the 96% calculation uses the entire frozen sample. The [technical guide](https://venettov.github.io/EnhancersResearch/methods.html#server-200-replay) explains replay with the saved models. No experimental activity was evaluated, so agreement is not biological accuracy or complete reproduction.
