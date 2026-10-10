# Cross-assay evaluation of MPRA and STARR-seq

## What is here

The local data archives are `lab_reported_data.tar.gz`, `output.tar.gz`, and `qc.tar.gz`; they remain compressed. `PAPERS/` contains the Genome Biology article. `SUPPLEMENTARY/` contains the detailed assay descriptions, figures, and tables S1–S5. `CODE/` contains the citable Zenodo v1.0 source archive.

## Recommended reading

Read the paper and supplementary information before combining the assay outputs. The study compares different MPRA/STARR designs and shows why assay design and processing need to be tracked when building labels or benchmarks.

## Citation and links

Zhang J et al. “Comprehensive evaluation of diverse massively parallel reporter assays to functionally characterize human enhancers genome-wide.” *Genome Biology* 26, 378 (2025). DOI: [10.1186/s13059-025-03828-8](https://doi.org/10.1186/s13059-025-03828-8).

Data: [Zenodo 16887276](https://doi.org/10.5281/zenodo.16887276). Code: [Zenodo 17254278](https://doi.org/10.5281/zenodo.17254278), source repository [on GitHub](https://github.com/haiyuan-yu-lab/Analysis_Code_Comprehensive_Evaluation_MPRA_and_STARR_seq).

The optional `raw_data.tar.gz` (516 MB), `uniform_processed_data.tar.gz` (25.4 GB), and `reference.tar.gz` (11.1 GB) archives have direct source URLs, sizes, and MD5 checksums in the parent `download_manifest.tsv`. Retrieve them with `python3 NEW_2026_DATA/download_project_resources.py --group optional`. The downloader attempts to resume interrupted transfers when supported by the source; the archives stay compressed.
