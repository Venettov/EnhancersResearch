# Enhancer Prediction Research

This repository is a curated research workspace for computational enhancer prediction and functional validation. It brings together the original benchmark files and literature already in the project, plus a 2026 update of public genomic annotations, reporter-assay datasets, papers, supplementary materials, and code snapshots.

It is a research data collection and literature map. It does not yet contain a single end-to-end analysis pipeline or claim that the different datasets have been harmonized into one training set.

## Research scope

The materials support work on questions such as:

- How well do sequence-based enhancer predictors generalize to newer functional assays?
- How do candidate annotations such as ENCODE cCREs compare with measured activity from MPRA, STARR-seq, and in-vivo VISTA experiments?
- How do assay, cell type, species, genome assembly, and label definition affect model performance?
- Can newer sequence models add value over classical sequence features when evaluated on independent experimental data?

Treat each source as a distinct experiment. An ENCODE candidate regulatory element, a reporter-assay hit, and an in-vivo validated VISTA enhancer are different evidence types; they should not be merged into a single positive class without a documented study design.

## Repository contents

| Path | Contents |
|---|---|
| `enhancer.cv.txt`, `enhancer.ind.txt`, and matching `non.*` files | Existing cross-validation and independent benchmark sequences. |
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

The large data files, article PDFs, supplementary files, and code archives are intentionally excluded from Git. Their folders and source manifests remain in the repository. From the repository root, run:

```bash
python3 NEW_2026_DATA/download_project_resources.py --group data
python3 NEW_2026_DATA/download_project_resources.py --group papers
```

Use `--group all` to fetch both groups. At the current manifest snapshot, the selected data total about 2.14 GB and the papers, supplements, and code total about 1.22 GB; sizes can change if sources are updated. The script streams each file, checks its recorded size and available checksum, and saves it into the study folder listed in the manifest. Python 3.9 or newer and its standard library are sufficient.

To fetch **all downloadable resources, including the optional large archives**, run this from the repository root on a computer with ample free space:

```bash
python3 NEW_2026_DATA/download_project_resources.py --group all --include-optional
```

The optional group adds about **47.7 GB**, bringing the current downloadable collection to about **51.1 GB** before extracting archives. It includes the MPRA/STARR raw archive (516 MB), uniform-processed archive (25.4 GB), reference archive (11.1 GB), and DNABERT-Enhancer model archive (10.7 GB). The downloader attempts to resume interrupted transfers where the source supports HTTP range requests; if not, it safely restarts that file. These archives remain compressed. Keep additional free space if you plan to extract them.

The existing benchmark text files and project documentation are tracked directly. The older papers already present in the original working folder are listed in `legacy_references.tsv`; use those DOI or publisher links to retrieve them. Full-text copies are not included in Git.

## Large or externally hosted resources

The large MPRA/STARR and DNABERT archives have direct URLs, byte sizes, and checksums in `NEW_2026_DATA/download_manifest.tsv`; the optional download command above fetches them. They are excluded from the default download so a regular clone does not unexpectedly retrieve nearly 48 GB.

- The AlphaGenome Atlas is approximately 1 petabyte and is not a single clone-time archive. Use the [official AlphaGenome downloads portal](https://alphagenome.google/downloads) or [API and Atlas documentation](https://github.com/google-deepmind/alphagenome) for the available access options and terms. The repository includes the Atlas preprint and supplements, not a copy of the full Atlas.

All source links, current file sizes, and available checksums are recorded in the manifests. Upstream file versions and download terms can change; cite the original data record and follow its terms when using the files.

## Notes for analysis

1. Check genome assembly and species before joining BED files or variants. VISTA includes human and mouse coordinates.
2. Preserve assay and cell-type labels. MPRA and STARR-seq measurements depend on experimental design and processing.
3. Keep candidate annotations separate from experimentally measured enhancer activity unless the analysis defines a defensible label mapping.
4. Use sequence- or locus-level independent splits where possible. Near-duplicate sequences and overlapping genomic regions can leak across train and test sets.
5. Record the exact source version and checksum for every downloaded file; upstream records can change.

## Citation and reuse

Cite the original publication and data record for any resource used. Follow the license and terms stated by each publisher or data host. The manifests preserve source links and checksums where available; they do not replace the original license or citation requirements.
