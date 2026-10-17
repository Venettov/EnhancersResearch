# MCSE-Enhancer: code-assisted replication

Status, 14 October 2026: **replication started; data and one notebook feature block recovered. No classifier trained and no published performance reproduced.** All work is local.

The objective is to recover the authors' analysis as far as the available artifacts permit, document every necessary repair, and evaluate a repaired implementation using the same sequence groups as the iEnhancer-2L reconstruction. MCSE-Enhancer classifies **enhancers versus non-enhancers**. It does not supply a second classifier for strong versus weak enhancers.

Source: Mir, Rehman, Tayara and Chong (2023), [Improving Enhancer Identification with a Multi-Classifier Stacked Ensemble Model](https://doi.org/10.1016/j.jmb.2023.168314). Author repository: [DNA-Enhancers](https://github.com/MirBilalAhmad/DNA-Enhancers), inspected commit [`d76c48946de9c46e0845df12c119a27b7e455444`](https://github.com/MirBilalAhmad/DNA-Enhancers/tree/d76c48946de9c46e0845df12c119a27b7e455444). This pinned snapshot is not asserted to be the latest repository version or the exact publication-time environment. See also [the original-publication review](../../reports/03_original_publications_replication_plan.md).

## Completed checkpoint

- Verified all nine saved source/data files against the hashes recorded during the original review, and retained their unmodified bytes in `vendor/DNA-Enhancers/`.
- Confirmed exact sequence order **and binary labels** against the previously audited legacy exports: 2,968 distinct training sequences, 1,484 per class; 400 historical test sequences, 200 per class. Every sequence is 200 bases of A/C/G/T.
- Confirmed that 100 historical test positives occur in training. They are the 100 legacy strong enhancers: 50% of test positives and 25% of the test set. The test export is explicitly diagnostic-only. Removing these rows would leave 100 positives and 200 negatives and would not establish similarity or locus independence.
- Mapped all training rows to the existing 2,451 sequence/locus groups, five outer folds, and three inner folds per outer training set. Verified group separation and both binary classes in every evaluation partition. These splits have already been explored during the earlier analyses; subsequent comparisons remain exploratory.
- Recovered the pure-Python block in feature-notebook cell 15, using the call settings in cells 16 and 19: `kGap=5`, `kTuple=3`. Generated **2,968 × 14,891** finite float64 features for training only. Labels are excluded from the matrix.
- Checked exact equality with the pinned author function on nine actual training rows, including class boundaries and GC extremes, and six synthetic/adversarial sequences. Ten tests passed, including changed-input rejection, group-leakage rejection, hand-calculated features and count conservation.
- Independently reopened the saved matrices, verified hashes and row/column identities, recomputed all seven basic summaries for every training row, and checked conservation of counts in all 40 gapped-feature blocks for every row.

The feature export consists of seven basic summaries, 84 nonoverlapping one-to-three-base word counts, and 14,800 gapped word counts. The seven summaries are also exported separately for a future paper/code comparison. That smaller export is not asserted to resolve the paper's complete NPCP specification.

## What currently prevents an exact rerun

Cell numbers below are **zero-based notebook indices**; original source files are preserved. Findings apply to the pinned snapshot, not to an uninspected later version.

| Issue | Evidence | Required treatment |
| --- | --- | --- |
| Incomplete input assembly | Training cells 4–5 and 9–10; testing cells 3–4 and 6–7 contain invalid placeholders. Eight cells fail syntax parsing after notebook directives are excluded. | Recover the six feature files and specify their row IDs, column order and metadata/label exclusions explicitly. |
| Feature description differs from code | Paper p. 4 describes an NPCP concatenation with dimensions totaling seven; it also refers to 16 properties. Feature cell 15 and its calls produce 14,891 features before the appended label. | Treat the notebook-compatible and paper-described variants separately until the actual published input is established. Do not silently choose the larger block as the published NPCP implementation. |
| Five external descriptor implementations not yet recovered | Feature cells 1, 3, 5, 7 and 9 invoke external iLearn scripts absent from this repository. | Pin and inspect [iLearn](https://github.com/Superzchen/iLearn), its property tables, defaults, normalization and output columns. The command settings below are evidence, not a complete feature specification. |
| Missing final settings | Several final classifier constructors contain strings such as `best_params` in place of parameter dictionaries; notebooks contain no saved output cells. Paper p. 5 refers to supplementary Table S1. | Recover Table S1 and reconcile it with code. The supplement was not found locally; publisher-page retrieval returned HTTP 403 and searches did not recover it. This does not establish that it is unavailable to readers. |
| Broken cross-validation | Training cell 14 fits and scores RF outside the fold loop, using only its final split. Cell 21 similarly exits the loop before the ExtraTrees evaluation. | A repaired experiment must fit and score each fold separately and aggregate the intended folds. Preserve the original source for audit. |
| Optimization/final-fit discrepancies | RF suggests `criterion` and `max_leaf_nodes` but omits them from the objective estimator; ExtraTrees has a leading space in the ` min_samples_split` trial key and inconsistent study variable names. | Use the same validated parameter dictionary during selection and final fitting; log repairs explicitly. |
| Test-label optimization | Testing cell 77 returns accuracy against `y_test_ind` as the Optuna objective. | Never use historical test outcomes for model/feature/ensemble selection in the repaired evaluation. Historical results may only be separately labeled diagnostics. |
| Several ensemble definitions | Testing cell 61 uses five bases plus CatBoost as meta-model with original features passed to it; cell 73 uses six bases plus CatBoost; cells 77–79 search base learners, meta-learner and fold count. | Establish which configuration produced the published result. Freeze one documented configuration and generate meta-training predictions out of fold, with group separation, for the repaired study. |
| Environment unspecified | No dependency lock or fitted model is supplied in the inspected tree. Old APIs occur in the notebooks. | Use a separate training environment, record compatible versions and verify probabilities/class ordering. The existing iEnhancer-2L environment has not been changed. |

The paper reports 81.5% independent-test accuracy. Matching that number would not establish sequence-independent generalization on these local files. A corrected analysis may produce a different result and should be identified as a repaired replication/reanalysis, not an exact rerun.

### Descriptor commands recovered from the notebook

| Descriptor | Explicit settings | Still to establish |
| --- | --- | --- |
| DCC | DNA; lag 5 | iLearn version and property-index defaults |
| PseKNC | DNA; lambda 2; weight 0.1 | Default k, index set, counting and normalization |
| SCPseDNC | DNA; lambda 2; weight 0.1 | Property-index set and column order |
| PCPseDNC | DNA; lambda 2; weight 0.1 | Reconcile paper's 38-index statement with the actual tool configuration |
| Kmer | No explicit k in the command | Paper specifies 3-mers; establish tool default and denominator |
| Notebook numerical/count block | Gap 5; maximum contiguous word length 3 | Determine whether all 14,891 columns were used in the published merged matrix |

The notebook's function named `pseudoKNC` simply uses Python `str.count` on words of lengths 1–3. It is separate from the iLearn PseKNC descriptor. Overlapping matches are **not** counted for those contiguous-word features; gapped windows **are** counted at every valid starting position. The recovery preserves those behaviors rather than substituting the earlier iEnhancer-2L feature implementation.

## Re-running the completed stage

Only Python and NumPy are needed for this checkpoint. The executed environment was Python 3.14.3 and NumPy 2.5.4 in the existing root `.venv`; no packages were installed or changed. This is a recovery environment, not a claim about the authors' training environment.

Run from the repository root. Both output directories must be new; existing checkpoints are not overwritten.

```sh
.venv/bin/python replication/mcse_enhancer/prepare.py \
  --source replication/mcse_enhancer/vendor/DNA-Enhancers \
  --output replication/mcse_enhancer/output/recovery-rerun

.venv/bin/python -m unittest discover \
  -s replication/mcse_enhancer -p 'test_*.py' -v

.venv/bin/python replication/mcse_enhancer/build_features.py \
  --prepared replication/mcse_enhancer/output/recovery-rerun \
  --output replication/mcse_enhancer/output/features-rerun

.venv/bin/python replication/mcse_enhancer/validate.py \
  --prepared replication/mcse_enhancer/output/recovery-rerun \
  --features replication/mcse_enhancer/output/features-rerun \
  --report replication/mcse_enhancer/output/features-rerun/validation.json
```

The vendor copy and large outputs are ignored by Git. On another machine, obtain the author repository at the commit above and pass its checkout directory to `--source`; `prepare.py` checks all nine hashes and retains only the listed files. It also requires the existing iEnhancer-2L prepared CSV exports and evaluation assignments with the exact hashes in `source_manifest.json`. Regenerate missing CSV exports using [that reconstruction's documented preparation](../ienhancer_2l/README.md); do not substitute newly shuffled data.

Files in this folder:

- `source_manifest.json`: pinned author files and local crosswalk checksums.
- `prepare.py`: verified data recovery, existing-fold mapping and static notebook syntax audit.
- `features.py`: optimized recovery plus a hash-pinned oracle containing only inspected author functions. Notebook imports, file operations and model cells are not executed.
- `build_features.py`: training-only features with IDs, names, hashes and parity checks.
- `test_recovery.py`: ten scientific/data-integrity checks.
- `validate.py`: saved-matrix identity, checksum, summary and count-conservation checks.
- `checkpoints/2026-10-14-recovery.json`: recorded run, source/output hashes and limitations.
- `output/2026-10-14-recovery/`: training export, quarantined historical-test export and audit.
- `output/2026-10-14-notebook-features/`: recovered numerical/count matrix, separate seven-summary view and audit.

## Next stages and connection to the new data

1. Recover the remaining iLearn descriptors and supplementary Table S1; reconcile feature width, merged-column order and the final ensemble. Record unresolved choices as explicit variants rather than silently filling them in.
2. Freeze a repair protocol and isolated software environment. All preprocessing and parameter selection must use training partitions only. Meta-training predictions must be out of fold, and tuning inside the stacking procedure must not consult held-out fold labels. Preserve the inherited sequence groups throughout.
3. Run a small end-to-end validation, then evaluate the frozen ensemble against a matched binary baseline on the existing outer groups. Report all folds, uncertainty and the exploratory nature of repeated use of this benchmark. Historical test diagnostics remain separate.
4. Only then define transfer to `NEW_2026_DATA`. Legacy enhancer/non-enhancer annotations and measured lentiMPRA activity are different targets. A frozen MCSE score could be tested as a baseline or feature for the matched-cell study after construct overlap, assay preprocessing and target definitions are resolved. The unresolved specificity-score normalization remains a prerequisite for interpreting selectivity; it is not solved by this checkpoint.

No historical test features, trained models, benchmark accuracy claims, website edits, commits or pushes were produced in this stage.
