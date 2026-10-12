# Large-scale ENCODE lentiMPRA (2025)

## What is here

Eight ENCODE experiment folders contain processed TSV, gzip-compressed BED (`*.bed.gz`), and BigBed files. The BED downloads remain compressed in their original ENCODE format. `PAPERS/` holds the Nature article. `SUPPLEMENTARY/` contains the methods/results document, reporting summary, supplementary figures and tables, and peer-review file.

## Verified local QC · 11 October, rechecked 12 October 2026

- The joint library uses **ENCSR405QCT (HepG2)**, **ENCSR203UFY (K562)**, and **ENCSR336MKI (WTC11)**. The other five accessions are pilot or large-scale libraries, not interchangeable joint-library inputs.
- Each experiment has three replicate TSVs and one combined TSV holding those same rows. All 32 files contain **3,850,212 rows**, but only **1,925,106 distinct complete rows within experiments**. Import either representation per experiment, preserving source, cell, replicate and construct identifiers.
- The S10 design has 60,000 constructs. Two control-name differences have a proposed explicit crosswalk; confirm it against the original FASTA before assigning sequences. Separate the `no_BC` processing sentinel.
- Requiring **at least one replicate with ≥10 observed barcodes in each of the three cells** recovers exactly the **55,977 names** in S11’s specificity table. Requiring all replicates to pass produces 55,863 names, so it is not an equivalent rule.
- **Numerical specificity scores remain unreproduced.** The direct reconstruction has RMSE 0.1067 and maximum absolute difference 1.5764. Trace normalization, filtering population, replicate aggregation and rounding before interpreting new selectivity results. Membership recovery is not score reproduction.

See [report 02](../../reports/02_workspace_audit_and_qc.md), [full recheck evidence](../../reports/assets/2026-10-12_workspace_recheck.json), and the [bilingual research notes](https://venettov.github.io/EnhancersResearch/notes.html#qc). This is initial local QC, not a reproduced biological result.

## Recommended reading

Read the main paper, then `lentiMPRA_supplementary_methods_and_results.docx` and the supplementary table ZIP. The study measures reporter activity for sequences in HepG2, K562, and WTC11 cells. These are experimental activity measurements; they do not, on their own, establish native enhancer–target-gene links in the genome.

## Citation and links

Agarwal V, Inoue F et al. “Massively parallel characterization of transcriptional regulatory elements.” *Nature* (2025). DOI: [10.1038/s41586-024-08430-9](https://doi.org/10.1038/s41586-024-08430-9).

ENCODE files can be traced by their `ENCFF...` IDs and experiment accessions `ENCSR...` in the folder names and [ENCODE](https://www.encodeproject.org/).
