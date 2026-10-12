# Cross-assay evaluation of MPRA and STARR-seq

## What is here

All six archives are present locally and remain compressed: `lab_reported_data.tar.gz`, `output.tar.gz`, `qc.tar.gz`, `raw_data.tar.gz`, `uniform_processed_data.tar.gz`, and `reference.tar.gz` (verified on 11 October and rechecked on 12 October 2026). `PAPERS/` contains the Genome Biology article. `SUPPLEMENTARY/` contains the detailed assay descriptions, figures, and tables S1–S5. `CODE/` contains the citable Zenodo v1.0 source archive.

## Recommended reading

Read the paper and supplementary information before combining the assay outputs. The study compares different MPRA/STARR designs and shows why assay design and processing need to be tracked when building labels or benchmarks.

## Citation and links

Zhang J et al. “Comprehensive evaluation of diverse massively parallel reporter assays to functionally characterize human enhancers genome-wide.” *Genome Biology* 26, 378 (2025). DOI: [10.1186/s13059-025-03828-8](https://doi.org/10.1186/s13059-025-03828-8).

Data: [Zenodo 16887276](https://doi.org/10.5281/zenodo.16887276). Code: [Zenodo 17254278](https://doi.org/10.5281/zenodo.17254278), source repository [on GitHub](https://github.com/haiyuan-yu-lab/Analysis_Code_Comprehensive_Evaluation_MPRA_and_STARR_seq).

The optional `raw_data.tar.gz` (516 MB), `uniform_processed_data.tar.gz` (25.4 GB), and `reference.tar.gz` (11.1 GB) archives have direct source URLs, sizes, and MD5 checksums in the parent `download_manifest.tsv`. They are already local; after a fresh clone, retrieve them with `python3 NEW_2026_DATA/download_project_resources.py --group optional`. The downloader attempts to resume interrupted transfers when supported by the source; the archives stay compressed.

## Local analysis limits

The raw archive lists count/metadata tables, not FASTQ sequencing reads. Some lab-reported lentiMPRA measurements come from the same research lineage as folder 02 and cannot provide independent confirmation of themselves. Establish shared tested loci and measurement provenance before a K562 comparison. See [the completed audit](../../reports/02_workspace_audit_and_qc.md).
