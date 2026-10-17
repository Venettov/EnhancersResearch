# MCSE-Enhancer: code-assisted replication

Status, 14 October 2026: **the first repaired MCSE-Enhancer benchmark is complete.** The prespecified notebook-compatible configuration achieved **75.74% held-out accuracy** across all 2,968 training records, compared with **76.21%** for the earlier reconstructed iEnhancer-2L binary SVM on identical folds. All 125 fits completed without warnings. This is a reported-parameter diagnostic, not an exact reproduction of the published pipeline. Everything remains local.

Open the [local result report](output/2026-10-14-benchmark-notebook-k2/report.html) or the [compact benchmark checkpoint](checkpoints/2026-10-14-benchmark-notebook-k2/benchmark_summary.json).

MCSE-Enhancer classifies **enhancers versus non-enhancers**. Its direct comparison is with the first iEnhancer-2L classifier, not the strong-versus-weak classifier. The objective is to recover the published analysis where possible and distinguish documented repairs and unresolved choices from an exact reproduction.

Sources: Mir et al. (2023), [Improving Enhancer Identification with a Multi-Classifier Stacked Ensemble Model](https://doi.org/10.1016/j.jmb.2023.168314); the [author code at commit d76c489](https://github.com/MirBilalAhmad/DNA-Enhancers/tree/d76c48946de9c46e0845df12c119a27b7e455444); and [iLearn at commit 507aae1](https://github.com/Superzchen/iLearn/tree/507aae17d9fea3d74a7c77984f1f1750eb734f53). That iLearn commit dates to March 2021, before the publication, but the authors did not identify their exact version. The user supplied the supplementary PDF containing Table S1; its bytes and provenance are recorded in `supplement_receipt.json` and `model_settings.json`.

## What is complete

- All nine saved author files were checksum-verified and retained unchanged.
- All 2,968 training sequences and 400 historical test sequences match our audited legacy exports, in order and binary labels. The training set contains 1,484 positives and 1,484 negatives; the historical test contains 200 per class.
- The same 100 test positives exactly duplicate training sequences. They are the 100 legacy strong enhancers. The historical test remains diagnostic-only; the new evaluation driver does not load it.
- All training records retain the existing 2,451 sequence/locus groups and the frozen five outer and three inner folds. Group separation and binary-class coverage are checked.
- The notebook numerical/count block and all five external iLearn descriptor families have been generated for training rows only. Labels and IDs are explicitly excluded from numerical features.
- Table S1 settings for all six base classifiers were visually checked and transcribed. Notebook search ranges were extracted separately without running the original optimization code.
- Repaired CV and stacking code now checks group separation, scores every candidate fold, and generates meta-training predictions out of fold. Candidate tuning is nested within each cross-fit training partition.
- **23 preflight tests passed.** The earlier synthetic check performed **31 fits**, exercising all six S1 classifiers individually and a complete six-base ensemble with no warnings. These checks are software validation.
- **The real benchmark completed 125 fits over five outer folds**, with three inner cross-fitting folds, no warnings and no parameter search. The final audit checked every fit against the frozen record and group assignments, all 90 base OOF partitions, all 120 fixed-candidate selections, and complete held-out prediction coverage.
- **Four additional statistical tests passed**, including independent rank-based AUROC checks and a row-level oracle verifying paired resampling of unequal-sized groups.

The initial recovery checkpoint and its README are preserved under `checkpoints/`. The previous runner and README are also archived under `checkpoints/2026-10-14-pre-benchmark/`. Previously completed iEnhancer-2L work, website changes and original data have not been altered.

## First benchmark results

`benchmark_protocol.json` was saved before fitting. It selected `notebook_k2_full` because it follows the recovered notebook commands and complete numerical/count block, without looking at MCSE performance. The six reported S1 base-model settings and repaired CatBoost meta-model were fixed; no candidate search, feature-variant selection or threshold optimization took place. Runtime was 36.3 minutes in the isolated environment.

| Model | Held-out accuracy | Mean fold AUROC | Pooled MCC |
| --- | ---: | ---: | ---: |
| Repaired MCSE combined model | **75.74%** | **0.847** | **0.516** |
| Earlier reconstructed iEnhancer-2L binary SVM | 76.21% | 0.841 | 0.526 |

In simple terms, the combined MCSE model correctly classified about 76 out of every 100 sequences. It did **not establish an accuracy improvement** over the earlier binary SVM. The observed difference was −0.47 percentage points, with a conditional paired group-bootstrap 95% interval of **−1.69 to +0.67 points**. The MCSE accuracy interval was **74.00%–77.37%**. These intervals use 2,000 paired resamples of whole sequence/locus groups within each outer fold, with seed 20261014; they do not include model refitting or uncertainty from parameter selection.

MCSE classified 1,067 enhancers and 1,181 non-enhancers correctly; it missed 417 enhancers and called 303 non-enhancers positive. Sensitivity was 71.90% and specificity 79.58%. Outer-fold accuracies were 75.42%, 79.26%, 72.34%, 75.93% and 75.76%. Its mean fold AUROC was slightly higher than the SVM's, but no uncertainty analysis for that ranking-metric difference was specified, so it is descriptive only. Pooled AUROC, which mixes separately fitted fold scores, was 0.845.

Among the individually recorded base classifiers, LightGBM had the highest observed accuracy (76.95%). This is a descriptive observation, **not** a held-out-data-driven selection of a replacement model. All six base results are retained in `model_metrics.csv`.

The comparison uses exactly matched record IDs, group IDs, labels and outer folds. It is not a controlled comparison of stacking alone: feature sets and parameter-selection procedures differ. Published S1 settings may already have been selected using these labels, and these benchmark folds have informed previous exploratory analyses. The paper's historical 81.5% should not be treated as a directly comparable target.

The independently checked audit confirms complete predictions for all 2,968 records, disjoint train/prediction groups at every fit, unchanged input/source hashes, fixed reported settings and no convergence warnings. Fitted estimators were not serialized; source snapshots and OOF/base/meta predictions are retained, and model-level replay requires rerunning the saved source. No model was fitted on all 2,968 records for deployment.

## Recovered feature definitions

The original MCSE notebook invokes iLearn for five descriptors. The pinned implementation resolves the omitted defaults as follows:

| Block | Recovered settings | Numerical columns |
| --- | --- | ---: |
| DCC | Dinucleotides; lag 1–5; six default properties; both directions for each property pair | 150 |
| PseKNC | 3-mer frequencies; lambda 2; weight 0.1; six properties; correlations computed over dinucleotides | 66 |
| SCPseDNC | Dinucleotide frequencies; lambda 2; weight 0.1; six properties | 28 |
| PCPseDNC | Dinucleotide frequencies; lambda 2; weight 0.1; **38** properties | 18 |
| Kmer, notebook command | Default **k=2**; overlapping frequencies divided by L−k+1 | 16 |
| Explicit Kmer3 alternative | k=3; overlapping frequencies divided by L−k+1 | 64 |
| Notebook numerical/count block | Seven summaries, 84 nonoverlapping 1–3-mer counts, 14,800 gapped counts; gap 1–5 | 14,891 |

The six-property order is Rise, Roll, Shift, Slide, Tilt, Twist. All 38 values and their dinucleotide order are preserved in `ilearn_properties.json`; the values are already tabulated by iLearn and are not standardized across training/test samples. `ilearn_features.py` loads only inspected, hash-pinned functions and constants. It does not execute the notebooks, upstream CLIs, arbitrary imports or pickle code. The original data-only property pickle was decoded with class loading prohibited and checked against the numeric JSON.

The original iLearn CSV writer retains a label column and omits sequence IDs. Our recovery instead retains unique legacy record IDs, checks their order and removes both metadata fields before assembling arrays. Actual labels are not passed to the iLearn functions. The incomplete original merge cells cannot establish which columns were retained in the publication.

Independent vectorized formulas agree with the recovered iLearn loops within 1e-12; the largest observed discrepancy was below 9e-16. Tests also cover overlapping-word counting, denominators, property tables, dummy-label invariance and malformed input. The earlier notebook block was independently checked against the original author functions.

### Explicit variants, not an inferred published matrix

| Variant | Word block | Numerical/count block | Total columns |
| --- | --- | --- | ---: |
| `notebook_k2_full` | 2-mers | Full notebook block | 15,169 |
| `k3_full` | 3-mers | Full notebook block | 15,217 |
| `notebook_k2_basic7` | 2-mers | Seven basic summaries only | 285 |
| `k3_basic7` | 3-mers | Seven basic summaries only | 333 |

The common four physicochemical blocks are included in every variant. Variants are assembled on demand with checked IDs, hashes and column names. No variant has been selected using benchmark performance.

Important unresolved differences:

- The paper describes 3-mers, but the notebook's iLearn command defaults to 2-mers. The paper writes the frequency denominator as sequence length L; iLearn uses L−k+1. The current 3-mer alternative follows iLearn normalization and is not asserted to reproduce that equation literally.
- The paper's NPCP description includes contradictory dimensional descriptions; the seven-summary view and the much larger notebook block are both preserved.
- Supplement Figure S5, captioned kmer, includes feature indices up to 14,798; Figure S6, captioned NPCP, includes Feature 83. Figure S4, captioned PCPseDNC, includes Feature 27, while the recovered lambda-2 parallel descriptor has 18 columns. These figures do not resolve the feature mapping. No corrected captions or hidden column selections have been invented.

## Reported model settings recovered from Table S1

The exact transcribed dictionaries are in `model_settings.json` and the original PDF is preserved locally at `vendor/publication/supplement_mmc1.pdf` (SHA-256 `58fa4336c2a91566f7cf7316bd46c9f24bf049853349960a631d330ca356e8cc`).

| Model | Selected reported settings |
| --- | --- |
| Random Forest | 34 trees; depth 31; maximum 38 leaves; gini; sqrt feature sampling |
| ExtraTrees | 214 trees; depth 61; maximum **60** leaves; entropy; sqrt feature sampling |
| LightGBM | 1,000 estimators; 10 leaves; depth 25; learning rate 0.0117 |
| XGBoost | 662 estimators; depth 2; learning rate 0.2105 |
| CatBoost | 60 iterations; depth 10; learning rate 0.0146 |
| MLP | One hidden layer of 20 units; adam; logistic activation; alpha 0.01 |

All other supplied settings, including regularization and sampling values, are retained in the dictionaries. The singular CatBoost table entry `iteration` is mapped to the API's `iterations`. The reported ExtraTrees 60-leaf limit lies outside the printed and notebook search ranges, and its 214 trees cannot arise from the notebook's step-5 grid. These reported optima are retained and flagged, not clamped. The supplement's LightGBM optimum 1,000 also exceeds the exclusive endpoint of its printed Python range.

The supplement resolves the missing **base** settings. It does not establish the final ensemble membership, meta-model settings, seeds, package versions or feature matrix. The code contains multiple ensemble definitions. `notebook_search_spaces.json` preserves the actual notebook search calls and documents differences from S1; no Optuna search has been executed.

## Evaluation repairs

The executable protocol is in `repair_protocol.json`.

1. **All folds are evaluated.** Each candidate is cloned, fitted and scored separately in every tuning fold. Selection uses mean fold accuracy with deterministic tie breaking; it cannot use only the final split left by a loop.
2. **Training groups stay separate from prediction groups.** Every fit checks IDs and group membership and records both sets in an audit. The same inherited outer/inner assignments permit a matched diagnostic comparison with the earlier work.
3. **Stacking uses out-of-fold predictions.** Each training row's meta-feature comes from a model that excluded that row's group. When several base candidates are supplied, their selection is repeated using only that cross-fit training subset. Tests deliberately change the held-out labels and verify that their own OOF predictions remain unchanged.
4. **Preprocessing is fitted within training folds.** The repaired MLP uses a StandardScaler inside its cloned pipeline. This is an explicit repair choice; the publication's preprocessing was not recovered.
5. **No test-label optimization.** Prediction-set labels are absent from the stacking API. The historical test is not loaded by the benchmark driver, and no held-out labels are used for early stopping.
6. **Probability columns are checked.** The code selects the column for class 1 using each estimator's class labels, validates probabilities, and uses a documented 0.5 threshold.
7. **Meta settings remain fixed.** A search over a precomputed OOF matrix is not implemented because it would require additional nesting of the entire stack. The present executable diagnostic uses six bases and CatBoost as meta-model, based on notebook testing cell 73, with positive-class probabilities and no raw-feature passthrough. Reusing S1 CatBoost settings for the meta-model is an explicit implementation choice, not a recovered published setting.
8. **Nonconvergence is surfaced.** Benchmark execution rejects ConvergenceWarning. An initial synthetic check found five MLP warnings at the library's 200-iteration default. The explicit cap was increased to 2,000 (S1 gives no cap); the final 31-fit synthetic validation had no warnings. This does not guarantee convergence on the real data.

The six-base architecture, probability meta-features, scaling, larger MLP cap, seeds and current package versions are documented repairs/runtime choices. Unspecified library defaults are recorded for inspection. LightGBM's `subsample_freq` remains zero: its reported `subsample` value alone does not activate bagging. CatBoost receives no evaluation set, so its overfitting detector is not fed held-out outcomes.

**Reported S1 settings may themselves have been selected using this benchmark.** Reusing them in grouped CV is a published-parameter diagnostic, not an unbiased new parameter-selection experiment. In addition, the inherited benchmark folds have informed earlier exploratory analyses. Freshly tuned comparisons must freeze their candidate spaces before running the nested selection path; the published 81.5% remains a historical result, not a target to optimize against.

## Software and local artifacts

A separate Python 3.12.14 environment is at `.venv/` inside this folder. Versions are pinned in `requirements-repaired.txt`: NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, LightGBM 4.7.0, XGBoost 3.4.1 and CatBoost 1.2.10, plus dependencies. These are compatible current versions, not recovered author versions. The root environment was not changed.

On this Mac, LightGBM and XGBoost need OpenMP. `run.py` launches the isolated interpreter with the OpenMP library already bundled in its scikit-learn wheel. It changes the child process's library path only, installs no system library and limits execution to one CPU thread. Direct invocation of the environment without that library path may fail on this machine.

Run from the repository root:

```sh
# Scientific/data-integrity regression tests.
python3 replication/mcse_enhancer/run.py -m unittest discover \
  -s replication/mcse_enhancer -p 'test_*.py' -v

# Generate the external descriptor blocks in a new output folder.
python3 replication/mcse_enhancer/run.py replication/mcse_enhancer/build_ilearn.py \
  --prepared replication/mcse_enhancer/output/2026-10-14-recovery \
  --output replication/mcse_enhancer/output/ilearn-rerun

# Verify all six classifiers and the ensemble using synthetic data only.
python3 replication/mcse_enhancer/run.py replication/mcse_enhancer/smoke_repaired.py \
  --output replication/mcse_enhancer/output/smoke-rerun

# Write a plan; this command does not train on the benchmark.
python3 replication/mcse_enhancer/run.py replication/mcse_enhancer/evaluate_repaired.py \
  --variant notebook_k2_full --mode plan \
  --output replication/mcse_enhancer/output/plan-rerun
```

Output folders must be new. The completed first benchmark used:

```sh
python3 replication/mcse_enhancer/run.py -u replication/mcse_enhancer/evaluate_repaired.py \
  --variant notebook_k2_full --mode run \
  --output replication/mcse_enhancer/output/2026-10-14-benchmark-notebook-k2

python3 replication/mcse_enhancer/run.py replication/mcse_enhancer/summarize_benchmark.py \
  replication/mcse_enhancer/output/2026-10-14-benchmark-notebook-k2
```

Use a new output name when rerunning; the existing folder is evidence to preserve. A variant must be selected explicitly. A nonconverged fit stops the run and writes a failure audit rather than publishing incomplete aggregate metrics. The summarizer checks all saved fits, recomputes metrics independently and applies the prespecified paired group bootstrap. The runner now records per-fit progress, saves base/OOF/meta predictions and freezes sources/effective settings before fitting; the evaluation algorithm was unchanged from the tested repair stage.

Current artifacts:

- `output/2026-10-14-benchmark-notebook-k2/`: complete first benchmark, readable report, all fit membership audits, OOF/base/meta arrays, matched held-out predictions, effective settings, frozen code, validation and checksums.
- `checkpoints/2026-10-14-benchmark-notebook-k2/`: compact reviewable results, held-out predictions, exact run/analysis source snapshots, provenance and preservation receipts. Large audit logs and OOF arrays remain in the ignored output folder.

- `output/2026-10-14-recovery/`: verified training crosswalk and diagnostic-only historical test.
- `output/2026-10-14-notebook-features/`: original recovered numerical/count block and seven-summary view.
- `output/2026-10-14-ilearn-validated/`: all external descriptor matrices, the 3-mer alternative and formula-comparison audit. The earlier `2026-10-14-ilearn/` copy is retained; the arrays are byte-identical after adding input validation.
- `output/2026-10-14-repaired-smoke-validated/`: final synthetic fit audit. The earlier smoke result is retained to document the convergence-cap repair.
- `output/2026-10-14-repaired-plan/`: validated five-fold execution plan for the notebook-compatible full variant.
- `checkpoints/2026-10-14-features-and-evaluation.json`: stage evidence, environment, validation and checksums.
- `checkpoints/2026-10-14-initial-recovery-README.md`: prior stage instructions and historical limitations.

Large outputs, upstream vendor files and the isolated environment are Git-ignored; manifests, code, settings and checkpoint receipts are local reviewable files. Recovering on another machine requires the listed pinned upstream files and the supplied supplement. Source hashes are in `source_manifest.json`, `ilearn_source_manifest.json` and `supplement_receipt.json`. The prepared legacy CSV files can be regenerated using the [iEnhancer-2L preparation guide](../ienhancer_2l/README.md). Keep their recorded identities and folds intact.

## Next study step

The first diagnostic and matched binary comparison are complete. A next analysis should freeze its question and candidate spaces before fitting: for example, a controlled comparison of the ambiguous feature definitions, or fresh nested selection under matched conditions. These would remain exploratory on the already-inspected folds; stronger confirmation requires an independently held-out evaluation. The present results do not justify choosing the highest-scoring base model after seeing held-out outcomes. Resolve or explicitly carry forward the feature/ensemble ambiguities before claiming an exact reproduction.

Transfer to `NEW_2026_DATA` remains a separate study: legacy enhancer annotations and measured lentiMPRA activity are different targets. A frozen MCSE score could become a baseline or feature after sequence overlap, assay preprocessing and target definitions are resolved. The outstanding specificity-score normalization issue is unchanged.

This stage produced the local benchmark results and report. It made no website edits, commits or pushes. Historical recovery-stage checkpoints and the frozen `repair_protocol.json` retain their original “not run” status as evidence of the earlier recovery stage; `benchmark_protocol.json` and the completed benchmark checkpoint document the subsequent run.
