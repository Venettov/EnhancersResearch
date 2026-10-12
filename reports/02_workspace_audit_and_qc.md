# EnhancersResearch workspace audit and data quality

**Research report 02 · 11 October 2026**  
**Question:** What does this folder contain, which analyses are feasible, and what could undermine their interpretation?  
**Status:** completed folder audit and initial data QC. Specificity-score reproduction, cross-assay overlap analysis, and biological hypothesis testing remain open.

The collection supports a focused study of measured enhancer activity across cellular contexts. Its strongest starting point is the matched lentiMPRA library: design sequences, three-cell measurements, and replicate data are all locally available and largely reconcile. The immediate work is to establish the analysis population and reproduce the authors’ normalization. The folder does not yet contain an executed end-to-end research pipeline or a new biological result.

The most consequential new finding is in the older benchmark: **100 of the 200 independent-test enhancer sequences exactly match development-set enhancer sequences.** Those local files cannot serve as a sequence-independent train/test benchmark in their current form. This finding concerns the copies in this repository, not the provenance or validity of every published study using a similarly named benchmark.

## Evidence and scope

Computed findings are recorded in [the audit evidence](assets/2026-10-11_workspace_audit.json). Its `legacy`, `lenti`, `joint`, `refined`, `structural`, `integrity`, `archives`, and `provenance` sections support the corresponding results below. [The audit script](assets/audit_workspace.py) preserves the calculations. Original downloaded files and existing research documents were retained.

The audit covered all 109 manifest-listed resources, all eight legacy sequence/representation files, all 32 ENCODE activity TSVs, the full SCREEN ELS BED, VISTA experiment/locus tables, every sheet of lentiMPRA Tables S10–S11, download scripts, documentation, and selected source-code files. Publication text and relevant methods were inspected to interpret these inputs. Four cross-assay TAR archives were fully enumerated; the two largest cross-assay archives and the model archive were sampled internally. Their complete compressed bytes were hashed. The hematopoiesis R object was not deserialized, and no pretrained model or upstream analysis pipeline was executed.

This report extends [the existing evidence and strategy report](01_enhancers_evidence_and_strategy.md). It preserves the decision log’s direction: start with experimental measurements; consider a new predictor only if a defined scientific need emerges.

## What is present

The 109 resources occupy **51,069,049,058 bytes: 51.07 decimal GB, approximately 47.56 GiB**. That explains the roughly 48 G directory-size display. The collection contains ten publication files representing eight distinct works because two studies have both preprint and published versions.

| Resource | Files | Approximate GB | Research role and readiness |
|---|---:|---:|---|
| ENCODE4 SCREEN | 7 | 0.729 | Candidate regulatory annotation; ready for coordinate-aware annotation |
| ENCODE lentiMPRA | 54 | 0.804 | Main experimental starting point; explicit joins and filtering required |
| MPRA and STARR-seq comparison | 11 | 38.358 | K562 assay comparison; tested-region overlap and shared provenance must be established |
| VISTA | 12 | 0.008 | Developmental reporter evidence; retain experiment, stage, source organism, and backbone |
| Hematopoiesis MPRA | 10 | 0.354 | Alternative project on synthetic motif interactions; R ingestion remains necessary |
| DNABERT-Enhancer | 5 | 10.703 | Existing-model resource; launcher needs repair before a smoke test |
| AlphaGenome and Atlas | 10 | 0.114 | Papers, supplements, research code; no full Atlas or verified local inference installation |

The optional large archives and DNABERT weights are already present. Several guides still describe them as downloads to obtain on demand. That wording is useful for a fresh clone, but does not describe this machine’s current holdings. The large model and cross-assay bundles account for most storage; file size should not determine project priority.

## The legacy benchmark has test-set overlap

| Local sequence file | Records | Unique sequences | Mean GC fraction |
|---|---:|---:|---:|
| `enhancer.cv.txt` | 1,484 | 1,484 | 49.07% |
| `non.cv.txt` | 1,484 | 1,484 | 37.46% |
| `enhancer.ind.txt` | 200 | 200 | 48.51% |
| `non.ind.txt` | 200 | 200 | 37.22% |

All sequences are 200 nt and contain only A, C, G, and T. All four unigram files reconstruct their corresponding sequences exactly, in the same order. They are alternative encodings of the same observations.

**The first 100 records of `enhancer.ind.txt` occur verbatim in `enhancer.cv.txt`.** Thus 50% of the independent positive class, or 25% of the complete 400-record independent set, overlaps the development data. A second parser independently confirmed all matches. For example, independent record 1, `Chr11_6627824_6628024`, matches development record 1,202, `CHR11_6627824_6628024`, with identical DNA. The evidence file lists every matching record pair and a sequence hash.

No other between-file exact sequence overlap was found among the four FASTA-like files. Checking sequences together with their reverse complements introduced no additional between-file matches. This check does not rule out near-duplicates, shifted windows, or related loci.

Two negative-test headers each occur twice, leaving 198 distinct headers for 200 distinct negative-test sequences. A parser keyed only by header could silently overwrite two records. Preserve an input row ID and a sequence hash.

The roughly 11–12 percentage-point GC difference between positive and negative classes also warrants attention if these data are used for model evaluation. It is evidence of a composition difference, not proof that a particular model relies on GC. A composition-only baseline and a carefully defined negative sampling policy would help interpret any later performance claim.

**Recommended use:** retain these files for historical reference. Before any independent evaluation, trace their source, construct sequence/locus groups, and define an uncontaminated evaluation set. Removing the 100 duplicates alone would not establish that all remaining test sequences are independent.

## ENCODE TSVs duplicate measurements across files

There are eight experiments, each with three replicate TSVs and a fourth TSV containing those same three replicates together. Across all 32 files there are **3,850,212 rows but only 1,925,106 distinct complete rows after deduplication within each experiment**. Concatenating all four files per experiment doubles every measurement.

Eight TSVs have headers and 24 do not. None contained duplicate `(condition, replicate, name)` keys within an individual file, and the five numeric fields parsed without missing or non-finite values. These checks establish file structure, not assay-level quality.

| Experiment | Cell | Library | Distinct construct names, including `no_BC` where present |
|---|---|---|---:|
| ENCSR463IRX | HepG2 | Pilot | 9,318 |
| ENCSR460LZI | K562 | Pilot | 7,368 |
| ENCSR022GQD | HepG2 | Large-scale | 153,904 |
| ENCSR382BVV | K562 | Large-scale | 230,933 |
| ENCSR244FWB | WTC11 | Large-scale | 70,233 |
| ENCSR405QCT | HepG2 | Joint | 56,982 |
| ENCSR203UFY | K562 | Joint | 56,979 |
| ENCSR336MKI | WTC11 | Joint | 56,979 |

Library assignments agree with the article’s Data Availability section. The three joint experiments are the appropriate ENCODE inputs for matching the same constructs across cells. The other libraries are related experiments, not interchangeable copies of the joint library. [Agarwal and Inoue et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11903340/)

The TSV schema is:

| Field | Interpretation for import |
|---|---|
| `condition` | Measured cell context |
| `replicate` | Replicate identifier within the experiment |
| `name` | Construct identifier requiring design-table reconciliation |
| `dna_count`, `rna_count` | Processed normalized quantities; do not treat these decimal values as raw integer read counts |
| `ratio` | RNA/DNA ratio |
| `log2` | Log2 RNA/DNA activity |
| `n_obs_bc` | Number of observed barcodes; needed to define coverage eligibility |

Choose either the combined TSV or the three replicate TSVs for each experiment. Preserve accession, filename, original name, cell, and replicate in the source ledger. Generic deduplication across experiments would risk erasing genuine repeat measurements.

## The joint library mostly reconciles

Table S10 is the design sheet. Its first row is blank and its second row contains the header. It has **60,000 unique construct names**, all with 230-nt sequences: a constant 15-nt adapter, a 200-nt insert, and a constant 15-nt adapter. All insert sequences contain only A, C, G, and T.

There are 56,904 potential enhancers, 2,396 promoters, and 700 controls. These are design categories, not calls that every element was active. All 60,000 inserts are unique in the recorded orientation, but **149 pairs become identical after reverse-complement canonicalization**. Those pairs should remain linked for any future sequence-based split. Canonicalization is an independence check, not permission to collapse orientation-specific measurements.

Table S11 contains nine sheets: a shared activity summary, an element-specificity-score table, and replicate/summary sheets for each cell.

| Population | Number of constructs | Meaning |
|---|---:|---|
| Designed | 60,000 | S10 design universe |
| Present in shared S11 summary | 56,981 | At least one reported cell value |
| Complete values in all three cells | 56,977 | Completeness alone, before barcode eligibility |
| Present in published ESS table | 55,977 | Authors’ specificity-table population |
| At least 10 barcodes in all three replicates of every cell | 55,863 | A stricter alternative, not the authors’ recovered population |

The shared summary has no missing HepG2 values, three missing K562 values, and three missing WTC11 values spread over four constructs. A complete-case join therefore loses four rows, not six.

### Two control names require an explicit crosswalk

Two synthetic positive controls use square brackets in S10 and underscores in S11 around the same coordinate text. A literal name join matches 56,979 summary rows and leaves two unmatched. An explicit proposed mapping of those two names accounts for all 56,981 summary rows, leaving **3,019 design constructs absent from the summary**. The crosswalk is preserved in `refined.aliases` in the evidence file. Verify it against the original construct FASTA before using it to assign sequences; do not normalize punctuation indiscriminately across all identifiers.

Each per-cell summary additionally contains a `no_BC` row that is absent from the shared summary, design table, and replicate-level S11 sheet. Each ENCODE joint experiment contains three `no_BC` rows, one per replicate. Treat that identifier as a processing sentinel outside the designed-construct universe.

After accounting for `no_BC`, the joint ENCODE measurements match the corresponding S11 replicate measurements: 170,929 HepG2 rows, 170,924 K562 rows, and 170,894 WTC11 rows. Numerical differences are below 10^-15, consistent with floating-point parsing. These are two representations of the same measurements, not independent validation.

### Coverage eligibility can be recovered exactly

For each cell, retain a construct if **at least one replicate has 10 or more observed barcodes**, then intersect the three cell-specific sets. This produces exactly **55,977 names**, with no additions or omissions relative to the S11 ESS table.

Requiring all three replicates to have at least 10 barcodes produces 55,863 names and removes 114 members of the published population. The former rule empirically reconstructs table membership; it does not prove every downstream processing step or settle which rule is best for a new analysis.

The per-cell counts under the recovered rule are 56,017, 56,007, and 55,982 after excluding `no_BC`. Each is one below the corresponding count printed in the article. The ENCODE sentinel is a plausible explanation for that difference, but the authors’ filtering code should confirm it.

### Replicates agree well, but numerical ESS reproduction remains open

Pairwise Pearson correlations of replicate log2 activity, using available paired values in the unfiltered S11 replicate sheets, are:

| Cell | Replicate correlation range |
|---|---:|
| HepG2 | 0.9738–0.9761 |
| K562 | 0.9691–0.9789 |
| WTC11 | 0.9543–0.9570 |

The per-cell summary means agree with arithmetic means of the available replicate log2 values to within 0.0005, consistent with three-decimal rounding. Shared-summary entries exactly match the corresponding per-cell summary means.

Across cells, correlations in the shared summary are approximately 0.614 for HepG2–K562, 0.493 for HepG2–WTC11, and 0.601 for K562–WTC11, using pairwise complete values. These describe the supplied selected library before analysis filters. They are not a reproduced figure, evidence that every difference is biological, or estimates of genome-wide enhancer specificity.

A direct reconstruction that restricts the rounded shared means to the ESS names, z-scores each cell using its sample standard deviation, and subtracts each element’s across-cell mean **does not reproduce the supplied ESS values**: RMSE is 0.1067 and the maximum absolute difference is 1.5764. The article’s methods describe z-scoring and centering, but additional processing details or source versions are needed. This is a reproducibility question, not sufficient evidence that the published values are wrong.

**Next decision:** trace the authors’ normalization and ESS-generation code, explicitly accounting for barcode filtering, replicate aggregation, population used for standardization, and rounding. Membership is reproduced; specificity scores are not yet reproduced. Do not equate `log2 > 0` with a validated active call or compare broad/selective activity before establishing the appropriate control-based criteria.

## The other resources have distinct uses

### SCREEN provides candidate annotations

The ELS BED contains **1,718,669 nonduplicated intervals**: 1,469,205 dELS and 249,464 pELS. Interval lengths range from 150 to 350 bp, with a median of 272 bp; no negative starts or nonpositive lengths were found. This is the enhancer-like subset of the registry. It provides a useful annotation layer but cannot turn absence from ELS into an experimentally inactive label. Confirm assembly and use explicit overlap criteria when annotating 200-nt constructs.

### Cross-assay analysis is feasible to investigate

The full listings of the four smaller archives contain 23 files in `lab_reported_data`, 11 in `raw_data`, 67 in `qc`, and 44 in `output`. The raw archive contains TSV/count/metadata files and **no FASTQ members**. It is not a local copy of every original sequencing read. Some QC/output members are notebook-checkpoint copies, another reason not to count filenames as independent evidence.

The uniform-processing dictionary describes active/inactive regions, GRO-cap signals, cCRE overlaps, and promoter proximity. It explicitly permits missing `logFC` for inactive regions, so zero-imputation would change the meaning of the data. The reference archive includes hg38-related resources and GENCODE v45 material in the inspected prefix.

The lab-reported archive includes lentiMPRA source tables from the same research lineage as folder 02. Keep that relationship explicit. Additional K562 assays can provide different measurements; reuse of the original lentiMPRA measurements cannot supply independent confirmation. Zhang and colleagues already study processing and assay disagreement, so a later project needs a more specific question and a demonstrated shared tested population. [Zhang et al., 2025](https://link.springer.com/article/10.1186/s13059-025-03828-8)

### VISTA requires experiment-level joins

The experiment table contains **5,090 rows** with 4,163 distinct `vista_id` values: 2,400 positive, 2,075 negative, and 615 allelic records. Experiment identifiers are unique. The locus table has 4,142 unique IDs, all represented among the experiments.

Exactly **21 experiment-side IDs are absent from the locus table**, accounting for 23 rows: 18 allelic and five negative. A forced inner join would drop them. Most experiment sequences are human or mouse, but 40 rows come from other source organisms. Preserve the source organism, assembly, embryo stage, reporter backbone, and allelic relationships. A negative developmental reporter result has a narrower interpretation than “not an enhancer anywhere.”

### Hematopoiesis remains a strong alternative project

The collection includes the processed R archive, published article, four supplementary tables, and three author code snapshots. Figure scripts reveal the expected hierarchy `mpra.data`, including library-specific `DATA` and `CONTROLS.GENERAL` objects, and fields such as `mean.norm.adj` and `mean.scaled.final`. These are code-derived schema clues; the R object’s actual row counts and contents remain unverified.

The figure scripts download the Figshare object at execution time even though the file is already local. A reproducible local adaptation should load the checked local copy. Some prediction scripts contain author-specific paths. An R runtime or compatible reader was unavailable for this audit, so internal-object QC and figure reproduction remain next steps if this branch is chosen.

### DNABERT and AlphaGenome are later tools

The archived DNABERT `src/prediction/Predict.sh` calls `src/training/run_finetune_WANDB_rekha.py`, which is absent from the ZIP. The archive instead contains `run_finetune_WANDB.py`. The launcher also has unquoted variables whose default values contain spaces, and its relative-path assumptions need checking. These are concrete barriers to running the documented command unchanged. Dependencies are pinned in the snapshot, but no compatible environment or inference run has been verified.

The model TAR begins with a 201-bp model checkpoint directory containing configuration and optimizer state. The full TAR checksum matches the manifest, but that does not establish which checkpoint should be used, model compatibility, or independence from a proposed evaluation set.

AlphaGenome’s local snapshot is a research implementation with its own dependencies and model-access instructions. The Atlas publication materials are not the Atlas data themselves. Neither model is required to resolve the lentiMPRA ingestion and normalization questions.

## Reproducibility and documentation need follow-up

All 109 mapped resource paths in the current manifests agree with the previous audit’s resource universe, and all are present. Fresh hashing confirms 55 reference-checksum matches and five matches to the reviewed-publication receipts. For the remaining 49, recorded sizes match but no reference checksum was supplied; new local SHA-256 hashes now identify the inspected bytes. No `.part` files were found.

The five receipt-backed exceptions are the VISTA HTML, Cell hematopoiesis HTML, hematopoiesis preprint, DNABERT preprint, and AlphaGenome Atlas preprint. They match the saved accepted copies, not the old companion-manifest hashes. Calling the downloader’s read-only `verify()` function reproduces five failures: four hash mismatches and one six-byte size discrepancy. `run_papers()` does not consult the receipts, so a rerun attempts to fetch those files again against historical expectations. Downloads that fail verification do not replace the existing originals.

The downloader should eventually distinguish historical references from accepted local publication versions. Retain both provenance records rather than replacing old hashes without explanation. Several code snapshots are fetched through mutable branch URLs, and VISTA exports use `main`; immutable revision URLs would make exact future recovery more reliable.

The older `download_public_resources.py` is a collection script, not a safe replacement for the manifest-driven downloader. It rewrites the manifest from its current discovery run, returns success even after recorded resource failures, and derives `.bed` names without preserving the gzip extension used by the corrected local files. Running it again could reverse documented filename corrections and change the curated inventory. Keep using the project downloader for retrieval while treating the original script as provenance.

At the start of this audit, the root README, lentiMPRA guide, and data manifest already had uncommitted changes, and the reports and download logs were untracked. A fresh clone therefore cannot be assumed to reproduce the local documentation state. No commit, push, or upstream code repair was made during this review.

`Links.docx` contains a BERT-enhancer repository link and an Oxford link ending in `bbad360`. The latter identifies GLMSite, a study of nucleic-acid-binding sites on proteins, rather than an enhancer-prediction paper. Retain it as background only if that was intended; it should not be used as a citation for the linked BERT enhancer method. [Primary bibliographic record](https://pubmed.ncbi.nlm.nih.gov/37824738/)

At the time of this audit, the older papers were represented by `legacy_references.tsv`, but their listed PDFs were absent from this checkout. The `bioinformatics_32_3_362_s1` directory contained only a placeholder.

**Follow-up, 12 October 2026:** the four original article PDFs, the iEnhancer-2L supplement ZIP, and both extracted supplement PDFs have now been added to the repository. All seven files match the supplied originals by SHA-256; the ZIP passes its integrity check, and both extracted PDFs match the corresponding archive members. This resolves the original-file gap and does not change the dated audit results or the separate 109-resource manifest inventory.

## Recommended next work

1. **Finish one reproducible lentiMPRA import.** Select one representation per experiment, retain original IDs, apply a reviewed two-name crosswalk, separate `no_BC`, and account for every design and measurement row. Preserve the 149 reverse-complement pairs as relationships.
2. **Resolve the numerical specificity calculation.** Match published membership first, then locate the precise normalization and aggregation steps. Agree on a numerical tolerance and reproduce one named figure or table before describing a new biological pattern.
3. **Define reliable activity and selectivity.** Use the stated control baseline and distinguish adequately measured inactive, insufficiently measured, and untested observations. The joint library was deliberately selected using earlier activity measurements, so proportions should be reported for this selected library.
4. **Assess a bounded K562 extension.** Count genuinely shared tested loci, trace reused measurements, and test overlap/coverage/orientation sensitivity before asking whether cell selectivity is associated with cross-assay stability. Novelty remains unestablished.
5. **Repair reproducibility when implementing the pipeline.** Make publication receipts usable by the downloader, pin recoverable source revisions, specify a small analysis environment, and preserve scripts and evidence in version control. Defer model execution until it serves a defined comparison.

The main analysis can begin with the existing files. More downloads or a new architecture are not prerequisites. The practical bottleneck is trustworthy joins and normalization, with the legacy benchmark overlap addressed separately before any future predictive evaluation.

## Rebuilding the computed evidence

The audit uses Python, NumPy, pandas, and openpyxl; exact versions are stored in the JSON metadata. From the project root:

```bash
python3 reports/assets/audit_workspace.py --output /tmp/enhancers_workspace_audit.json
```

The command hashes approximately 51 GB, reads the selected tables, streams archive listings, and writes one JSON file. It uses temporary storage for intermediate dataframes and does not download resources, expand the large archives onto disk, execute external analysis code, or modify the source datasets. The initial evidence was generated by executing the same section functions individually and combining their outputs. Paper interpretation and the recommendations above are human-readable synthesis, not automatically generated by that script.
