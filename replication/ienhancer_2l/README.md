# iEnhancer-2L reproduction workspace

Start with the website guide: [English](https://venettov.github.io/EnhancersResearch/reproduce.html) · [Español](https://venettov.github.io/EnhancersResearch/es/reproduce.html).

Data preparation, evaluation grouping, and an explicitly specified PseKNC feature reconstruction are implemented. There is no trained model or reproduced accuracy yet. Counting ambiguities and missing SVM settings still prevent a claim of exact author-code reproduction.

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
python -m pip install -r replication/ienhancer_2l/requirements.txt
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

The next stage is to specify and implement RBF SVM fitting, training-only scaling if used, and a predeclared `C`/`gamma` search. No trained model, held-out predictions or new performance numbers exist at this checkpoint. Original labels are chromatin-based annotations, not lentiMPRA measurements. The later experimental comparison remains separate.

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

At this earlier checkpoint, only data preparation was complete. The grouping and feature work recorded above follows it; exact uniqueness alone does not establish independence from related sequences or overlapping loci. No model has been trained and no published performance has been reproduced.

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
