# EnhancersResearch — Exploring the signals that control genes

Student research at the [Center for Computational and Integrative Biology (CCIB)](https://ccib.camden.rutgers.edu/), Rutgers University–Camden.

Our goal is to **reproduce published enhancer prediction methods, starting with iEnhancer-2L, then connect their predictions to measured activity in HepG2, K562, and WTC11**. We begin with the four original papers and sequence files supplied by Prof. Dehzangi. The matched lentiMPRA study provides the main experimental comparison after reconstruction and data preparation; its shared design and traceable measurements make it useful, not file size alone.

[Website in English](https://venettov.github.io/EnhancersResearch/) · [Sitio en español](https://venettov.github.io/EnhancersResearch/es/) · [Current research notes](https://venettov.github.io/EnhancersResearch/notes.html#qc)

This is a curated research workspace with completed file/QC audits, initial reconciliation of the experimental data, a trained two-layer iEnhancer-2L reconstruction and a **repaired MCSE-Enhancer reconstruction**. **Numerical lentiMPRA specificity-score reproduction remains unresolved.** Experimental transfer and biological hypothesis testing have not been completed. The datasets have not been combined into one training set.

Start with the **[step-by-step reproduction guide](https://venettov.github.io/EnhancersResearch/reproduce.html)** ([español](https://venettov.github.io/EnhancersResearch/es/reproduce.html)): workspace setup, original files, preparation, features, training commands, grouped evaluations and plain-language explanations of the comparison results.

**17 October review release:** the repository and bilingual website collect the completed iEnhancer feature comparisons, repaired MCSE benchmark, 2-mer/3-mer comparison, normalization comparison and the planned VISTA evaluation. These analyses reuse the historical grouped benchmark and do not establish exact reproduction or independent confirmation.

- **MCSE reconstruction:** the original 2-mer version reaches **75.74%** accuracy; the 3-mer version reaches **76.82%**. Changing only the standalone 3-mer normalization gives **76.48%**, a −0.34-point change with a conditional paired 95% interval of −0.85 to +0.17 points. These results do not establish a clear normalization benefit or loss. [Methods, source provenance and checkpoints](replication/mcse_enhancer/README.md) · [Website explanation](https://venettov.github.io/EnhancersResearch/reproduce.html#mcse-normalization-results).
- **VISTA evaluation plan:** preliminary screening retains **1,847 candidate fragments: 953 positive and 894 negative**. **Independence is not verified.** Sequence-family, genomic-coordinate, lentiMPRA-reservation and final-model checks remain pending; no external predictions or performance results exist. The planned model remains the original 2-mer reconstruction, rather than a variant selected for its later observed accuracy. [Protocol and screening evidence](replication/mcse_enhancer/independent_evaluation/README.md) · [Website explanation](https://venettov.github.io/EnhancersResearch/reproduce.html#mcse-independent-plan).

Source code, compact checkpoints and downloadable evidence are versioned. Large downloaded resources, Python environments, vendor caches and full generated run directories remain local under the existing ignore rules. Frozen analysis records retain their original local-only instructions and dates; this later release does not rewrite them or run the next scientific step.

**13 October feature checkpoint:** all 2,968 benchmark sequences match their hg19 intervals. A predeclared grouping policy yields **2,451 groups**, saved as 5 outer / 3 inner folds with no recorded related pair crossing a boundary. PseKNC matrices have **4,105 features** per sequence for both classification layers. Five explicitly documented counting/normalization variants are saved locally; sample standard deviation matches the supplement's normalized table within its rounding. The [implementation and rerun instructions](replication/ienhancer_2l/README.md) and [feature checkpoint](replication/ienhancer_2l/checkpoints/2026-10-13-groups-features/) preserve the details.

**13 October SVM checkpoint:** both classifiers are trained using the primary features and the saved groups. The protocol was committed before fitting; C/gamma tuning stayed inside each outer training set.

| Task | Mean held-out accuracy | Conditional 95% interval | Mean ROC AUC |
| --- | ---: | ---: | ---: |
| Enhancer / non-enhancer | **76.21%** | 74.64–77.90% | 0.841 |
| Strong / weak, known enhancers | **60.98%** | 58.38–63.73% | 0.668 |

These are means over five outer folds, with whole-group bootstrap intervals conditional on the fitted models and folds. They are **not reproduced leave-one-out results** or lentiMPRA performance. The final identification model reaches the C search boundary, and original counting ambiguities remain. [Saved models, held-out predictions and full evidence](replication/ienhancer_2l/checkpoints/2026-10-13-svm-training/) are versioned; the training checkpoint passed 26 tests.

**Baseline and feature-sensitivity comparison:** comparisons are complete on the same grouped folds. Ordinary overlapping 6-mers reach **75.91% / 63.68%** accuracy (identification / strength), versus **76.21% / 60.98%** for primary PseKNC; GC alone reaches **75.13% / 61.79%**. Disjoint counting lowers performance, while the other interpretations have smaller aggregate effects that can still change individual predictions. These are exploratory comparisons, not grounds to select a replacement model or claim experimental transfer. All **34 tests** and the saved-artifact validation passed at this stage. The [methods and interpretation](replication/ienhancer_2l/README.md#local-baseline-and-feature-sensitivity-review) document paired intervals, prediction differences and limitations. The [website summary and evidence downloads](https://venettov.github.io/EnhancersResearch/reproduce.html#baseline-results) provide the reading copy; full generated models and run outputs remain local in `replication/ienhancer_2l/output/2026-10-13-baselines-sensitivity-verified/`. Experimental transfer remains unfinished.

## Original papers and the current replication plan

| Original paper | Corresponding data and role |
|---|---|
| [iEnhancer-2L](bioinformatics_32_3_362.pdf) | First reconstruction target. The shared 2,968 training fragments and labels are in [Supplement S1](bioinformatics_32_3_362_s1/Supp-S1.pdf); [S2](bioinformatics_32_3_362_s1/Supp-S2.pdf) provides structural-property tables. |
| [EnhancerPred](srep38741.pdf) | Second baseline using the same benchmark; label-dependent features and selection must remain inside training folds. |
| [iEnhancer-EL](bioinformatics_34_22_3835.pdf) | Later ensemble reconstruction. Its current publisher S4 matches the 400 local test sequences, including 100 strong sequences already in training. |
| [MCSE-Enhancer](1-s2.0-S0022283623004254-main.pdf) | Public code and matching benchmark data support a repaired reconstruction. The original snapshot has incomplete cells, test-label optimization and the same training/test overlap; [our implementation](replication/mcse_enhancer/README.md) documents repairs, recovered supplementary settings, completed comparisons and unresolved choices. |

The [12 October original-publication review](reports/03_original_publications_replication_plan.md) recovered **742 strong, 742 weak, and 1,484 non-enhancer training labels**. Removing the 100 overlapping strong test examples leaves no strong class for strength evaluation. Two legacy training sequences also match inserts in the new lentiMPRA design. The [evidence](reports/assets/2026-10-12_original_publications_review.json) and [sequence-label crosswalk](reports/assets/2026-10-12_original_publications_review_sequence_labels.tsv) record these findings and their source hashes.

Reconstructing a method, matching its published accuracy, and evaluating it on new experimental measurements are separate milestones. The old strong/weak annotations are not high/low lentiMPRA activity labels. Both SVMs have a first grouped evaluation. Baseline, feature-sensitivity, structural-component, scale-aware and training-only block-balance comparisons are complete; the [reconstruction workspace](replication/ienhancer_2l/README.md) records their results and limits. The latest balanced words+summaries model reaches **63.14%** strength accuracy versus **62.80%** for words alone: a small, uncertain +0.34-point difference (conditional 95% interval −1.86 to +2.57). This does not establish an added structural-feature benefit. All 57 scientific tests and independent saved-artifact checks passed at this stage. Reproducing lentiMPRA processing remains separate. Experimental transfer must use sequences independent of training. Retraining on measured activity is a separate analysis; historical published accuracy has not been reproduced.

## Current findings and analysis limits

These are findings about the local files audited on **11 October 2026**, not a claim about every copy of the published datasets. A [full recheck on 12 October 2026](reports/assets/2026-10-12_workspace_recheck.json) reproduced every non-metadata audit section exactly. See [report 02](reports/02_workspace_audit_and_qc.md) and its [computed evidence](reports/assets/2026-10-11_workspace_audit.json).

1. **The legacy “independent” test set is contaminated by development-set overlap.** The first 100 sequences in `enhancer.ind.txt` exactly match sequences in `enhancer.cv.txt`: 100/200 test positives (**50%**) and 100/400 total test records (**25%**). These local files cannot currently support a sequence-independent evaluation. Removing those duplicates alone would not establish independence from related loci or near-duplicates.
2. **ENCODE TSVs can silently double measurements.** Each of eight experiments has three replicate TSVs plus a combined TSV containing those same measurements. Concatenating all 32 files gives **3,850,212 rows from 1,925,106 distinct complete rows within experiments**. Use the combined file *or* its three replicate files, preserving experiment and replicate identity; do not deduplicate unrelated experiments together.
3. **The matched lentiMPRA population largely reconciles.** The joint experiments are HepG2 **ENCSR405QCT**, K562 **ENCSR203UFY**, and WTC11 **ENCSR336MKI**. Two control-name differences have an explicit proposed crosswalk, which still needs confirmation against the original construct FASTA before sequence assignment. Requiring **at least one replicate with ≥10 observed barcodes in each of the three cells** recovers exactly the **55,977 names** in the published specificity table. This reproduces membership, not numerical scores.
4. **Specificity scores are not yet reproduced.** A direct reconstruction from the rounded shared means differs from the supplied scores (RMSE **0.1067**, maximum absolute difference **1.5764**). Trace normalization, filtering population, replicate aggregation, and rounding before interpreting new selectivity results. This mismatch does not by itself establish an error in the paper.
5. **All 109 manifest-listed resources are present locally: 51.07 GB.** The audited files total **51,069,049,058 bytes** (decimal GB; approximately **47.56 GiB**), including the optional compressed archives. Verification is not uniform: **55** match reference checksums, **5** match previously reviewed publication receipts, and **49** match recorded sizes without an upstream checksum; new local hashes identify those 49 copies. Local hashes alone do not establish upstream identity. Large downloaded resources remain excluded from Git.
6. **Two code paths need repair before use.** The project downloader does not consult accepted publication receipts and rejects five previously accepted copies against historical manifest expectations (four checksum mismatches and one six-byte size difference). The archived DNABERT prediction launcher calls missing `run_finetune_WANDB_rekha.py`; the presence of another training script is not a verified replacement. DNABERT inference has not been validated; this limitation is separate from the new SVM reconstruction.

The current reproduction-first goal adds the original method reconstruction to these data-preparation requirements. Trace lentiMPRA specificity processing before experimental transfer; consider a cross-assay extension only after checking shared tested loci and independent measurements. Model evaluation requires a suitable test design and verified code.

## Research reports

The [reports folder](reports/README.md) holds study summaries, strategies, and analysis decisions. Start with [Original enhancer publications and replication plan](reports/03_original_publications_replication_plan.md), also available as an [HTML reading copy](reports/03_original_publications_replication_plan.html). [Enhancer biology and research strategy](reports/01_enhancers_evidence_and_strategy.md) preserves the foundational 10 October analysis.

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
| `replication/ienhancer_2l/` | Audited inputs, grouped folds, PseKNC features, two trained SVMs, held-out predictions, inference/training commands and checkpoint evidence. |
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
