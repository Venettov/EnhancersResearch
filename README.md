# EnhancersResearch — Exploring the signals that control genes

Our goal is to understand how enhancer activity changes across cellular contexts and how reliably experiments support those patterns. The starting analysis uses the matched lentiMPRA library measured in HepG2, K562, and WTC11. Its shared design and traceable measurements make it useful for this question; file size alone does not determine priority.

[Website in English](https://venettov.github.io/EnhancersResearch/) · [Sitio en español](https://venettov.github.io/EnhancersResearch/es/) · [Current research notes](https://venettov.github.io/EnhancersResearch/notes.html#qc)

This is a curated research workspace with completed local file/QC audits and an initial reconciliation of the published data. **Numerical specificity-score reproduction remains unresolved.** There is no executed end-to-end research pipeline, new biological discovery, or validated new predictor. The datasets have not been combined into one training set.

## Current findings and analysis limits

These are findings about the local files audited on **11 October 2026**, not a claim about every copy of the published datasets. A [full recheck on 12 October 2026](reports/assets/2026-10-12_workspace_recheck.json) reproduced every non-metadata audit section exactly. See [report 02](reports/02_workspace_audit_and_qc.md) and its [computed evidence](reports/assets/2026-10-11_workspace_audit.json).

1. **The legacy “independent” test set is contaminated by development-set overlap.** The first 100 sequences in `enhancer.ind.txt` exactly match sequences in `enhancer.cv.txt`: 100/200 test positives (**50%**) and 100/400 total test records (**25%**). These local files cannot currently support a sequence-independent evaluation. Removing those duplicates alone would not establish independence from related loci or near-duplicates.
2. **ENCODE TSVs can silently double measurements.** Each of eight experiments has three replicate TSVs plus a combined TSV containing those same measurements. Concatenating all 32 files gives **3,850,212 rows from 1,925,106 distinct complete rows within experiments**. Use the combined file *or* its three replicate files, preserving experiment and replicate identity; do not deduplicate unrelated experiments together.
3. **The matched lentiMPRA population largely reconciles.** The joint experiments are HepG2 **ENCSR405QCT**, K562 **ENCSR203UFY**, and WTC11 **ENCSR336MKI**. Two control-name differences have an explicit proposed crosswalk, which still needs confirmation against the original construct FASTA before sequence assignment. Requiring **at least one replicate with ≥10 observed barcodes in each of the three cells** recovers exactly the **55,977 names** in the published specificity table. This reproduces membership, not numerical scores.
4. **Specificity scores are not yet reproduced.** A direct reconstruction from the rounded shared means differs from the supplied scores (RMSE **0.1067**, maximum absolute difference **1.5764**). Trace normalization, filtering population, replicate aggregation, and rounding before interpreting new selectivity results. This mismatch does not by itself establish an error in the paper.
5. **All 109 manifest-listed resources are present locally: 51.07 GB.** The audited files total **51,069,049,058 bytes** (decimal GB; approximately **47.56 GiB**), including the optional compressed archives. Verification is not uniform: **55** match reference checksums, **5** match previously reviewed publication receipts, and **49** match recorded sizes without an upstream checksum; new local hashes identify those 49 copies. Local hashes alone do not establish upstream identity. Large downloaded resources remain excluded from Git.
6. **Two code paths need repair before use.** The project downloader does not consult accepted publication receipts and rejects five previously accepted copies against historical manifest expectations (four checksum mismatches and one six-byte size difference). The archived DNABERT prediction launcher calls missing `run_finetune_WANDB_rekha.py`; the presence of another training script is not a verified replacement. No model inference run has been validated.

The next milestone is a provenance-preserving lentiMPRA import and a numerically reproduced published comparison. Trace specificity processing first; evaluate a bounded cross-assay extension only after checking shared tested loci and independent measurements. Model evaluation additionally requires an uncontaminated test design and a working, verified launcher.

## Research reports

The [reports folder](reports/README.md) holds study summaries, strategies, and analysis decisions. Start with [Enhancer biology and research strategy](reports/01_enhancers_evidence_and_strategy.md), also available as an [HTML reading copy](reports/01_enhancers_evidence_and_strategy.html).

The [completed workspace audit and QC report](reports/02_workspace_audit_and_qc.md) records the findings above and their limits. The initial strategy explores measured enhancer activity across cellular contexts and the reliability of evidence across assays. It does not assume that the next objective is to develop another prediction model. The report distinguishes published findings, local file inspection, and proposed analyses.

## Research scope

The materials support work on questions such as:

- How does activity of the same DNA fragment change across cellular settings, and how stable is the supporting evidence?
- How do candidate annotations such as ENCODE cCREs compare with measured activity from MPRA, STARR-seq, and in-vivo VISTA experiments?
- How do assay, cell type, species, genome assembly, and label definition affect model performance?
- Can newer sequence models add value over classical sequence features when evaluated on independent experimental data?

Treat each source as a distinct experiment. An ENCODE candidate regulatory element, a reporter-assay hit, and an in-vivo validated VISTA enhancer are different evidence types; they should not be merged into a single positive class without a documented study design.

## Repository contents

| Path | Contents |
|---|---|
| `enhancer.cv.txt`, `enhancer.ind.txt`, and matching `non.*` files | Legacy development/test sequences; the local test positives overlap development data and are not sequence-independent. |
| `*.unigram.txt` | Existing unigram representations of the benchmark sequences. |
| `NEW_2026_DATA/01_ENCODE4_SCREEN/` | ENCODE4 SCREEN candidate cis-regulatory elements (cCREs), with a focus on enhancer-like elements. |
| `NEW_2026_DATA/02_LENTIMPRA_ENCODE_2025/` | Processed ENCODE lentiMPRA outputs for eight experiments. |
| `NEW_2026_DATA/03_MPRA_STARR_CROSS_ASSAY_2025/` | Selected data from a cross-assay MPRA/STARR-seq comparison. |
| `NEW_2026_DATA/04_VISTA/` | VISTA enhancer-browser tables for in-vivo developmental validation. |
| `NEW_2026_DATA/05_HEMATOPOIESIS_MPRA/` | MPRA data for synthetic and genomic sequences across blood-cell states. |
| `NEW_2026_DATA/06_DNABERT_ENHANCER_2026/` | DNABERT-Enhancer paper, supplement, code snapshot, and model-resource notes. |
| `NEW_2026_DATA/07_ALPHAGENOME_2026/` | AlphaGenome paper and supplements, plus the AlphaGenome Atlas preprint and related materials. |
| `Links.docx` | Links retained from the original project folder. |
| `legacy_references.tsv` | Citation and source links for the original papers in this folder. |
| Original article PDFs, `bioinformatics_32_3_362_s1.zip`, and `bioinformatics_32_3_362_s1/` | Four original papers, the iEnhancer-2L supplement archive, and its two extracted PDFs, tracked directly in Git. |
| `reports/` | Dated strategy, completed QC audit, evidence JSON, audit script, and decision log. |
| `website/` and `docs/` | Bilingual website source and generated GitHub Pages output. See [website instructions](website/README.md). |

Each numbered new-study folder has a `STUDY_GUIDE.md` with the study's purpose, data description, and interpretation notes. Begin with [`NEW_2026_DATA/00_START_HERE.md`](NEW_2026_DATA/00_START_HERE.md), then use the guides and manifests below.

## New research material added

The 2026 collection is documented in [`NEW_2026_DATA/README_NEW_DATA.md`](NEW_2026_DATA/README_NEW_DATA.md). The files that explain or locate the new materials are:

- `NEW_2026_DATA/00_START_HERE.md` — bilingual folder map and suggested reading order.
- `NEW_2026_DATA/01_ENCODE4_SCREEN/STUDY_GUIDE.md` — ENCODE4 candidate regulatory-element resource.
- `NEW_2026_DATA/02_LENTIMPRA_ENCODE_2025/STUDY_GUIDE.md` — ENCODE lentiMPRA experiments and processed output.
- `NEW_2026_DATA/03_MPRA_STARR_CROSS_ASSAY_2025/STUDY_GUIDE.md` — assay comparison, selected Zenodo files, and omitted large bundles.
- `NEW_2026_DATA/04_VISTA/STUDY_GUIDE.md` — VISTA tables and genome-assembly notes.
- `NEW_2026_DATA/05_HEMATOPOIESIS_MPRA/STUDY_GUIDE.md` — hematopoiesis MPRA data and cell-state context.
- `NEW_2026_DATA/06_DNABERT_ENHANCER_2026/STUDY_GUIDE.md` and `RESOURCE_NOTES.md` — sequence-model paper, code, and model-weight access.
- `NEW_2026_DATA/07_ALPHAGENOME_2026/STUDY_GUIDE.md` and `RESOURCE_NOTES.md` — AlphaGenome paper and Atlas access notes.
- `NEW_2026_DATA/download_manifest.tsv` — selected data files, source URLs, recorded sizes, download status, and checksums where available.
- `NEW_2026_DATA/COMPANION_MATERIALS_MANIFEST.tsv` — article copies, supplements, code snapshots, source URLs, and SHA-256 checksums.
- `NEW_2026_DATA/download_project_resources.py` — clone-time downloader for the selected data and companion materials.
- `NEW_2026_DATA/download_public_resources.py` — original resource-collection script retained for provenance; use the project downloader below for a fresh clone.

The source collection includes ENCODE4 SCREEN, eight ENCODE lentiMPRA experiments, selected MPRA/STARR-seq comparison files, official VISTA exports, a hematopoiesis MPRA data file, DNABERT-Enhancer materials, and AlphaGenome materials. At the current manifest snapshot, this is 64 selected data files and 41 companion files (10 papers, 25 supplements, and 6 code snapshots). The manifests are the authoritative file-level record of what is included and where it came from.

## Get the downloadable resources after cloning

The large data files, article PDFs, supplementary files, and code archives under `NEW_2026_DATA/` are intentionally excluded from Git. Their folders and source manifests remain in the repository. From the repository root, run:

```bash
python3 NEW_2026_DATA/download_project_resources.py --group data
python3 NEW_2026_DATA/download_project_resources.py --group papers
```

Use `--group all` to fetch both groups. At the current manifest snapshot, the selected data total about 2.14 GB and the papers, supplements, and code total about 1.22 GB; sizes can change if sources are updated. The script streams each file, checks its recorded size and available checksum, and saves it into the study folder listed in the manifest. **Known limitation:** its paper verification does not yet accept the five reviewed publication versions recorded in the [receipt snapshot](website/data/publication_receipts.json); do not describe `--group papers` or `--group all` as a fully verified restoration workflow until that path is repaired. Existing originals are preserved when a replacement download fails verification. Python 3.9 or newer and its standard library are sufficient.

To fetch **all downloadable resources, including the optional large archives**, run this from the repository root on a computer with ample free space:

```bash
python3 NEW_2026_DATA/download_project_resources.py --group all --include-optional
```

Those four optional archives are already present in the audited local workspace, but remain opt-in after a fresh clone. The optional group adds about **47.7 GB**, bringing the current downloadable collection to about **51.1 GB** before extracting archives. It includes the MPRA/STARR raw archive (516 MB), uniform-processed archive (25.4 GB), reference archive (11.1 GB), and DNABERT-Enhancer model archive (10.7 GB). The downloader attempts to resume interrupted transfers where the source supports HTTP range requests; if not, it safely restarts that file. These archives remain compressed. Keep additional free space if you plan to extract them.

The existing benchmark text files and project documentation are tracked directly. The legacy test-set overlap warning above applies to these tracked sequence files. The four original article PDFs listed in `legacy_references.tsv`, the iEnhancer-2L supplement ZIP, and its extracted `Supp-S1.pdf` and `Supp-S2.pdf` are also tracked directly. On 12 October 2026, all seven files (5,690,584 bytes) were verified by SHA-256 against the supplied originals; the ZIP passed its integrity check, and both extracted PDFs matched its contents. These original materials are separate from the 109 manifest-listed downloadable resources. DOI and publisher links remain in `legacy_references.tsv` for provenance.

## Large or externally hosted resources

The large MPRA/STARR and DNABERT archives have direct URLs, byte sizes, and checksums in `NEW_2026_DATA/download_manifest.tsv`; the optional download command above fetches them. They are excluded from the default download so a regular clone does not unexpectedly retrieve nearly 48 GB.

- The AlphaGenome Atlas is approximately 1 petabyte and is not a single clone-time archive. Use the [official AlphaGenome downloads portal](https://alphagenome.google/downloads) or [API and Atlas documentation](https://github.com/google-deepmind/alphagenome) for the available access options and terms. The repository includes the Atlas preprint and supplements, not a copy of the full Atlas.

All source links, current file sizes, and available checksums are recorded in the manifests. Upstream file versions and download terms can change; cite the original data record and follow its terms when using the files.

## Notes for analysis

1. Check genome assembly and species before joining BED files or variants. VISTA includes human and mouse coordinates.
2. Preserve assay and cell-type labels. MPRA and STARR-seq measurements depend on experimental design and processing.
3. Keep candidate annotations separate from experimentally measured enhancer activity unless the analysis defines a defensible label mapping.
4. Do not use the current legacy independent-test files as a sequence-independent evaluation. Establish sequence/locus groups and check reverse complements, near-duplicates, and overlapping genomic regions before defining a clean split.
5. Record the exact source version and checksum for every downloaded file; upstream records can change.

## Citation and reuse

Cite the original publication and data record for any resource used. Follow the license and terms stated by each publisher or data host. The manifests preserve source links and checksums where available; they do not replace the original license or citation requirements.
