# iEnhancer-2L reproduction workspace

Start with the website guide: [English](https://venettov.github.io/EnhancersResearch/reproduce.html) · [Español](https://venettov.github.io/EnhancersResearch/es/reproduce.html).

Only the data-preparation stage is implemented here. There is no trained model, feature extractor, or reproduced accuracy yet. The guide describes the remaining work and unresolved counting, normalization, and SVM settings.

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
