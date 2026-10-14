# iEnhancer-2L reproduction workspace

Start with the website guide: [English](https://venettov.github.io/EnhancersResearch/reproduce.html) · [Español](https://venettov.github.io/EnhancersResearch/es/reproduce.html).

Only the data-preparation stage is implemented here. There is no trained model, feature extractor, or reproduced accuracy yet. The guide describes the remaining work and unresolved counting, normalization, and SVM settings.

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

Data preparation is complete for this checkpoint. Evaluation grouping and the PseKNC implementation remain next: exact uniqueness alone does not establish independence from related sequences or overlapping loci. No model has been trained and no published performance has been reproduced.

## Preparation workflow

From the repository root, with Python 3.10 or newer:

```sh
python replication/ienhancer_2l/prepare_data.py
python -m unittest discover -s replication/ienhancer_2l -p 'test_*.py'
```

The helper uses only the standard library. It checks original file bytes against the 12 October review, validates 200-base FASTA records, verifies row/header/sequence hashes against the reviewed crosswalk, and exports:

- `output/benchmark.csv`: 2,968 records, including recovered strong/weak labels and source pages. `non_enhancer` in the original crosswalk becomes `non-enhancer` in `class_label`. Strength is blank for non-enhancers, not zero.
- `output/legacy_test_diagnostic_only.csv`: 400 historical test records, with an exact training-overlap flag. This is not an independent test set or the first paper's leave-one-out benchmark. Test labels come from the current iEnhancer-EL S4 through the reviewed crosswalk.
- `output/data_audit.json`: counts, source/output hashes, and limitations.

Rerunning replaces those three derived files. Use `--output PATH` to keep separate runs. Outputs and `.venv` are ignored by Git. No original files are modified. Preserve byte-level line endings; a fresh clone can use `git clone --config core.autocrlf=false https://github.com/Venettov/EnhancersResearch.git`.

These checks do not establish independence from similar sequences, reverse complements, or overlapping loci. The 100 exact historical test overlaps are all strong enhancers. The original chromatin-based labels are not experimental lentiMPRA activity measurements.
