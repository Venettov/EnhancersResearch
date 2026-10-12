# DNABERT-Enhancer (2026)

## What is here

- `PAPERS/`: a 2025 bioRxiv preprint PDF and local full-text HTML for the published 2026 Bioinformatics paper.
- `SUPPLEMENTARY/`: the published article’s supplementary ZIP.
- `CODE/`: a snapshot of the public GitHub source repository.

## Recommended reading and limits

Read the published article HTML and supplement for the current method and results. The preprint PDF is the earlier version and may differ. This is a sequence-based prediction resource; predictions are model outputs, not experimental validation. The trained model archive (about 10.7 GB) is present locally with a verified reference checksum as of the 12 October recheck. It is excluded from Git; after a fresh clone, retrieve it with `python3 NEW_2026_DATA/download_project_resources.py --group optional`.

## Citation and links

Sathian R et al. “Genomic language model for predicting enhancers and their allele-specific activity in the human genome.” *Bioinformatics* 42(9), btag456 (2026). DOI: [10.1093/bioinformatics/btag456](https://doi.org/10.1093/bioinformatics/btag456).

Preprint: [bioRxiv 2025.03.18.644040](https://doi.org/10.1101/2025.03.18.644040). Code: [GitHub](https://github.com/DavuluriLab/DNABERT-Enhancer). Trained models: [Zenodo 19157566](https://doi.org/10.5281/zenodo.19157566). Prediction browser: [DNABERT-Enhancer data repository](https://dnabert-enhancer-datarepo.streamlit.app/).

## Code readiness and evaluation limits

The archived `src/prediction/Predict.sh` calls missing `src/training/run_finetune_WANDB_rekha.py`. The snapshot contains `run_finetune_WANDB.py`, but it has not been validated as a replacement. Paths, quoting, dependencies, checkpoint compatibility and a smoke test remain necessary before inference; having the weights does not establish a working predictor.

The first 100 enhancer sequences in the local legacy independent test file also appear in the development file. Those files cannot currently support sequence-independent evaluation. This is a finding about the local benchmark, not a claim about the training or evaluation of every published model. See [report 02](../../reports/02_workspace_audit_and_qc.md).
