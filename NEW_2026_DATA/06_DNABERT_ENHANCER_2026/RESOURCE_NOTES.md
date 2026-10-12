# DNABERT-Enhancer (2026)

The paper, supplement, and code snapshot are organized in `PAPERS/`, `SUPPLEMENTARY/`, and `CODE/`. The 10,682,051,673-byte (~10.7 GB) trained-model archive is present locally and its checksum was rechecked on 12 October 2026. It remains excluded from Git and optional for a fresh clone; retrieve it using `python3 NEW_2026_DATA/download_project_resources.py --group optional`. Its direct Zenodo URL and MD5 checksum are in `NEW_2026_DATA/download_manifest.tsv`; the downloader attempts to resume interrupted transfers when supported by the source.

- Published article: https://doi.org/10.1093/bioinformatics/btag456
- Earlier preprint: https://doi.org/10.1101/2025.03.18.644040
- Code: https://github.com/DavuluriLab/DNABERT-Enhancer
- Trained models: https://doi.org/10.5281/zenodo.19157566
- Prediction browser: https://dnabert-enhancer-datarepo.streamlit.app/

**Not yet runnable as documented:** the archived prediction launcher references a missing Python file. Inference and a compatible checkpoint/environment have not been verified. See [the study guide](STUDY_GUIDE.md#code-readiness-and-evaluation-limits) before model use.
