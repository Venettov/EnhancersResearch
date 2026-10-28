# Research reports

This folder holds readable summaries, research strategies, analysis results, and decisions for EnhancersResearch. Reports are editable in VS Code; HTML copies provide a reading view.

## Start here

- [Independent evaluation of the iEnhancer-2L reconstruction](04_ienhancer_2l_independent_evaluation.md) — 20 October 2026: fixed saved model, proposed VISTA assay cohort, prior-exposure exclusions, family and reference checks, metrics, and the separate three-cell handoff. [HTML reading copy](04_ienhancer_2l_independent_evaluation.html). The design is defined; cohort independence is not verified and no external evaluation has run.

- [Original enhancer publications and replication plan](03_original_publications_replication_plan.md) — 12 October 2026: feasibility for all four original methods, recovered strong/weak labels, publisher and public-code test overlap, and connections to all seven new resource groups. [HTML reading copy](03_original_publications_replication_plan.html) · [Computed evidence](assets/2026-10-12_original_publications_review.json) · [Sequence-label crosswalk](assets/2026-10-12_original_publications_review_sequence_labels.tsv).

- [Workspace audit and data quality](02_workspace_audit_and_qc.md) — completed 11 October 2026: legacy test-set overlap, duplicated ENCODE measurements, joint-library membership, unresolved specificity scores, and file/code readiness. [HTML reading copy](02_workspace_audit_and_qc.html) · [Computed evidence](assets/2026-10-11_workspace_audit.json) · [Audit script](assets/audit_workspace.py).

- [Enhancer biology and research strategy](01_enhancers_evidence_and_strategy.md) — foundational biology, summaries of all ten collected publication files, the resource inventory, and a proposed analysis-first research direction. [HTML reading copy](01_enhancers_evidence_and_strategy.html).
- [Decision log](decisions.md) — proposed scope, decisions, and unresolved choices.
- [Inspection inventory](assets/2026-10-10_inspection_inventory.json) — limited file-level observations supporting report 01.

The first report recommends studying measured enhancer activity and reliability across cellular contexts. Developing another prediction model is not the default objective. Novel extensions remain proposals until feasibility and prior literature are checked.

## Conventions

Use numbered, descriptive filenames such as `02_data_dictionary_and_qc.md`. Put the date, question, data versions, status, methods, results, limitations, and next decision near the beginning of each analysis report. Label source-paper findings, our own computed findings, and hypotheses distinctly.

Keep the Markdown version as the editable source and regenerate its HTML reading copy after edits. Link to exact source accessions, publications, and supporting tables. Keep small report assets in `assets/`; put large generated analysis tables outside this directory and record how to rebuild them.

Preserve downloaded inputs in `NEW_2026_DATA/`. Do not copy datasets into reports or treat an article, its preprint, and a reused dataset as independent evidence. Include exclusions and unresolved observations in analysis summaries.

## Recheck · 12 October 2026

A fresh full execution reproduced every non-metadata section of the 11 October audit, including hashing all 51.07 GB. [Recheck evidence](assets/2026-10-12_workspace_recheck.json). The dated report remains the record of the original findings.

## Current stage and next deliverable

As of 20 October 2026, the iEnhancer-2L reconstruction, both saved SVMs, grouped evaluations, feature comparisons, and author-server checks are complete. Report 04 defines a separate external evaluation using the fixed layer-I model; its cohort and execution checks remain pending. Numerical specificity-score reproduction and an end-to-end experimental-transfer pipeline remain unresolved. A documented import, reviewed control-name mapping, and reproduced normalization/aggregation are prerequisites for the later lentiMPRA comparison. The contaminated legacy test cannot certify independent performance. Reports 02 and 03 retain their historical findings and dates; see the [decision log](decisions.md).

The reports preserve the status at their stated dates. Original paper links replace machine-specific download paths in report 01; the bilingual [website reading edition](https://venettov.github.io/EnhancersResearch/strategy.html) is also available.

## Reproduce the local audit

The audit requires Python 3.10+, NumPy, pandas, openpyxl, and the downloaded resources. Its historical input logs are local, so a fresh clone can prepare them from the published snapshots before running the audit:

```bash
mkdir -p NEW_2026_DATA/DOWNLOAD_LOGS
cp -n website/data/download_audit.json NEW_2026_DATA/DOWNLOAD_LOGS/download_audit.json
cp -n website/data/publication_receipts.json NEW_2026_DATA/DOWNLOAD_LOGS/publication_receipts.json
python3 reports/assets/audit_workspace.py --output /tmp/enhancers_workspace_audit.json
```

The `-n` option preserves existing local logs. This hashes roughly 51 GB and checks tables and archive/code structure; it does not download resources, repair the downloader or DNABERT launcher, or run model inference.
