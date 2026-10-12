# Enhancer biology and research strategy

**EnhancersResearch · Research report 01 · 10 October 2026**  
**Status:** literature synthesis and proposed analysis strategy. Biological results below are attributed to their source papers; our own work so far is a download audit and limited inspection of file contents. No new model has been trained and no biological hypothesis has yet been tested.

## 1 Our starting point

**The best first outcome is an understandable, reproducible analysis of when enhancer activity changes across cellular contexts—and how reliably different assays support that activity.** We do not need to build another enhancer prediction model to do useful work with this collection.

We now have 109 manifest-listed resources, approximately 51.1 GB, organized into seven study folders. They include experimental measurements, genomic annotations, developmental reporter results, synthetic enhancer experiments, papers, supplements, code snapshots, and model checkpoints. They are different kinds of evidence, not 109 interchangeable datasets.

The recommended first project asks:

> Among the same DNA sequences tested in HepG2, K562, and WTC11 cells, which show broadly shared reporter activity and which show selective activity? For the subset also adequately tested by other K562 assays, how stable is the evidence for activity?

The concrete outcome would be a documented activity table, a small set of clear figures, and an evidence table for individual regions. Every conclusion would identify its cell context, assay, measurement quality, and limitations. We would first reproduce selected published observations, then decide whether a focused extension is justified.

**This is not yet a claim of novelty.** Agarwal and colleagues already analyzed cell specificity; Zhang and colleagues already analyzed assay disagreement. A useful extension would need to go beyond those analyses—for example, testing whether apparent cell selectivity is associated with stable versus fragile K562 activity calls after accounting for coverage and promoter proximity. The overlap and metadata needed for that extension have not yet been established.

### Read this report in three passes

| Your purpose | Start here |
|---|---|
| Understand the biology | Sections 2–3 |
| Understand the collection and the papers | Sections 4–6 |
| Decide what we should do next | Sections 7–10 |
| Look up terminology or sources | Sections 11–12 |

## 2 What enhancers are

### From DNA to regulated gene expression

Cells use DNA as a template to produce RNA through transcription. For protein-coding genes, that RNA can subsequently be translated into protein. Different cell types can carry essentially the same genome yet express different sets and amounts of genes.

An **enhancer** is a DNA regulatory element that can increase transcription from a compatible promoter in a particular biological context. A **promoter** is the region associated with transcription initiation. Enhancers help determine where, when, and how strongly genes are expressed. The label describes a regulatory function, not a universal sequence pattern present in every enhancer. The ENCODE, lentiMPRA, and hematopoiesis studies illustrate this context dependence. [P01](https://doi.org/10.1038/s41586-025-09909-9), [P02](https://doi.org/10.1038/s41586-024-08430-9), [P05](https://doi.org/10.1016/j.cell.2025.04.017)

Three ingredients are especially useful for understanding enhancer behavior:

1. **Sequence:** short DNA patterns can recruit transcription factors. Their arrangement and combinations can affect regulatory activity.
2. **Cell state:** a sequence encounters different transcription factors and cofactors in different cells. Having a binding motif does not ensure the corresponding protein is present or bound.
3. **Genomic context:** chromatin accessibility, neighboring regulatory elements, promoter compatibility, and three-dimensional contacts can influence the outcome.

An enhancer is therefore more like a context-dependent control element than a permanent on/off switch. A sequence active in a blood-derived cell line may behave differently in a liver-derived line or a developing embryo.

### A conceptual path from sequence to activity

**DNA motifs → transcription-factor binding and interactions → regulatory activity in a cell context → effects on transcription.**

Chromatin and promoter context influence this entire path. An experimental assay observes only part of it. A reporter experiment tests the candidate with an engineered reporter; an endogenous perturbation changes the original genomic region and measures consequences there.

The distinction matters for target genes. Showing that a sequence activates a reporter does not identify the gene it regulates in its original chromosome. Enhancer–gene assignment is a separate problem requiring additional evidence. For example, the activity-by-contact study combined endogenous CRISPR perturbations with regulatory activity and chromatin-contact information to investigate enhancer–promoter connections. We should treat the nearest gene as an annotation, not an established target. [Fulco et al., 2019](https://doi.org/10.1038/s41588-019-0538-0)

### The signals used to find candidate enhancers

| Signal or term | What it tells us | What it does not establish alone |
|---|---|---|
| ATAC-seq or DNase-seq | A region is accessible to the assay in the measured biosample | That it enhances a particular gene |
| H3K27ac and other histone marks | A biochemical pattern associated with regulatory chromatin | A universal positive/negative enhancer label |
| Transcription-factor binding | A protein-associated genomic region in a specific experiment | That its binding causes increased transcription |
| A sequence motif | A DNA pattern compatible with a binding preference | Which factor is actually bound or whether the region is active |
| cCRE | A candidate cis-regulatory element annotated from evidence | That every candidate is an experimentally confirmed enhancer |
| pELS / dELS | Proximal / distal enhancer-like signatures in the ENCODE classification | Reporter activity in every cell type |

The expanded ENCODE registry includes additional classes and functional behaviors beyond enhancers. Our local `GRCh38-cCREs.ELS.bed` contains only the pELS/dELS subset. Regions outside that file cannot automatically be labeled non-enhancers. [P01](https://doi.org/10.1038/s41586-025-09909-9)

### Why sequence alone does not settle the question

Sequence can be informative, but enhancer function is conditional. In the hematopoiesis paper, the same binding sites can participate in activating or repressive behavior depending on cell state and site combinations. Two individually activating sites do not necessarily produce stronger activation together. [P05](https://doi.org/10.1016/j.cell.2025.04.017)

Likewise, orientation independence is a useful experimental property, not an absolute law that every measured sequence must satisfy. Reporter design and sensitivity influence what is observed. Zhang and colleagues explicitly discuss the tradeoff between requiring activity in both orientations and retaining candidates supported in only one. [P03](https://doi.org/10.1186/s13059-025-03828-8)

## 3 What each type of experiment actually measures

These evidence types complement one another. They do not form a single ranking in which one assay answers every question better than the others.

| Evidence | Basic design | Strongest use here | Main interpretation limit |
|---|---|---|---|
| ENCODE/SCREEN annotation | Integrates biochemical evidence into genomic candidate regions | Locate and annotate candidate regulatory elements | Candidate status is not a cell-specific functional assay |
| MPRA | Tests many sequences with reporters, often linked to identifying barcodes | Quantify regulatory potential across many constructs | Insert length, promoter, construct, and cell affect the readout |
| lentiMPRA | Uses lentiviral integration of reporter constructs | Compare activity and cell specificity in an integrated reporter setting | Integration is not at each sequence's native locus |
| STARR-seq | Candidate sequence participates in the reporter transcript; output is related to input abundance | Broad screens of sequence-dependent reporter activity | Coverage, orientation, transcript effects, and processing matter |
| VISTA developmental assay | Tests regulatory sequences with reporters in mouse embryos | Tissue patterns and developmental activity | Sequence origin, embryo stage, and reporter backbone must be retained |
| Synthetic MPRA | Designs motif combinations and measures their activity | Examine regulatory interactions with controlled sequence changes | Synthetic grammar may not transfer directly to native enhancers |
| Endogenous CRISPR perturbation | Alters or represses a region at its genomic location | Investigate effects on native gene expression | Requires appropriate perturbation and gene-expression measurements; a dedicated dataset is not our starting point |
| Model prediction | Computes a score or predicted assay signal from sequence | Generate hypotheses or compare existing tools | Predictions are not independent experimental confirmation |

Sources: [P01](https://doi.org/10.1038/s41586-025-09909-9), [P02](https://doi.org/10.1038/s41586-024-08430-9), [P03](https://doi.org/10.1186/s13059-025-03828-8), [P04](https://doi.org/10.1093/nar/gkae940), [P05](https://doi.org/10.1016/j.cell.2025.04.017), [Fulco et al.](https://doi.org/10.1038/s41588-019-0538-0)

**Four states must stay separate:** active under the stated criterion; adequately measured without detected activity; measured too poorly to decide; not tested. A fifth state—repressive activity—requires its own evidence relative to an appropriate baseline. “Not detected,” “not tested,” and “silencer” are not synonyms.

## 4 What is actually in our repository

### Audited resource inventory

Counts below come from the completed download audit, not from folder size estimates. A resource can be a table, article, ZIP, or large archive. Sizes are decimal GB of downloaded files, including compressed archives; extraction would use additional space.

| Study folder | Resources | Size | Main material | Role in our project |
|---|---:|---:|---|---|
| `01_ENCODE4_SCREEN` | 7 | 0.729 GB | Human ELS BED; article and supplements | Common genomic annotation |
| `02_LENTIMPRA_ENCODE_2025` | 54 | 0.804 GB | 48 ENCODE files from eight experiments; article and supplements | First activity and cell-context analysis |
| `03_MPRA_STARR_CROSS_ASSAY_2025` | 11 | 38.358 GB | Reported calls, uniformly processed results, references, QC, raw-data bundle, code and article | K562 assay comparison and sensitivity analysis |
| `04_VISTA` | 12 | 0.008 GB | Eleven data/dictionary tables and database article | Later developmental evidence case studies |
| `05_HEMATOPOIESIS_MPRA` | 10 | 0.354 GB | R data object, two article versions, supplements and code | Alternative mechanistic project on motif interactions |
| `06_DNABERT_ENHANCER_2026` | 5 | 10.703 GB | Two article versions, supplement, code and model archive | Optional existing-model comparison |
| `07_ALPHAGENOME_2026` | 10 | 0.114 GB | Two distinct papers, supplements and research code | Later focused interpretation of selected variants |
| **Total** | **109** | **51.069 GB** | **10 publication files; 99 other resources** | A collection to curate before combining |

The 10 publication files represent **eight distinct works**: two pairs are preprint/published versions of the same study. AlphaGenome and AlphaGenome Atlas are separate works. The repository also references four older prediction papers; those references are discussed in Section 6, but their full PDFs are not part of the local collection inspected here.

### Concrete observations from our initial inspection

These are observations of the downloaded files, not new biological findings.

- **SCREEN:** the ELS BED has 1,718,669 rows: 1,469,205 dELS and 249,464 pELS. This is a subset of the expanded registry, not its entire approximately 2.37 million human cCREs.
- **lentiMPRA:** the 32 TSVs include eight with headers and 24 without headers. They contain fields corresponding to condition, replicate, sequence name, DNA/RNA quantities, ratio, log2 activity, and barcode count. A parser that assumes every file has a header will lose records in the headerless files.
- **lentiMPRA design:** the supplementary ZIP contains Table S10, the joint-library design, and Table S11, its measurements. These are promising entry points for matching exact constructs across the three cells. Their presence has been verified; the complete join and quality filtering remain to be done.
- **VISTA:** `experiments.tsv.gz` has 5,090 rows: 2,400 labeled positive, 2,075 negative, and 615 allelic. The file includes 4,163 distinct `vista_id` values. `locus.tsv.gz` has 4,142 rows; the differing universes must be reconciled rather than silently forced into a one-to-one join. The `allelic` category is not a negative label.
- **VISTA context:** the experiment table spans multiple embryo stages and reporter backbones. Its `organism` field identifies the source sequence; it does not convert the mouse reporter experiment into a human in-vivo experiment.
- **Cross-assay archives:** a small internal data dictionary describes genomic intervals, activity calls, GRO-cap signals, cCRE overlaps, and promoter proximity. One archive also contains a lentiMPRA source table from the study used in folder 02. Those two copies cannot count as independent confirmation.
- **Hematopoiesis:** the core resource is `data_updated2.rda`, with author code and supplements. Its internal R objects have not yet been inspected, so the exact analysis-ready tables and joins remain an ingestion task.
- **Legacy sequence files:** the four original enhancer/non-enhancer files contain 1,484 + 1,484 development sequences and 200 + 200 independent-test sequences, each 200 nt in the inspection. Unigram versions are alternate representations, not additional biological observations. Some coordinate headers explicitly refer to hg19; assembly must be checked before combining them with GRCh38 data.

The eight compressed ENCODE BED files correctly retain `.bed.gz` extensions. Archives remain compressed. A bundle named `raw_data.tar.gz` has been downloaded, but its name alone does not establish that every original sequencing read is locally available. Likewise, the full AlphaGenome Atlas and a turnkey local AlphaGenome model installation are not included merely because we have the papers and code snapshot.

### Provenance and download integrity

The audit records 55 resources verified against supplied checksums, 49 verified by size where a reference checksum was absent, and five reviewed current publication copies. No downloads are missing or partial, and all downloaded assets are ignored by Git.

The five publication copies differ from historical manifest bytes: VISTA HTML, hematopoiesis Cell HTML, its bioRxiv preprint, the DNABERT bioRxiv preprint, and the AlphaGenome Atlas preprint. Their identities/readability and actual SHA256 values are documented. This establishes the reviewed copies we possess, not byte-for-byte equivalence with the historical copies. Original source hashes were preserved.

See [download audit](../website/data/download_audit.json), [publication receipts](../website/data/publication_receipts.json), and [inspection inventory](assets/2026-10-10_inspection_inventory.json). The latter records limited file-level checks; it is not a full quality-control analysis of every dataset.

## 5 Summaries of the collected papers

### P01 The expanded ENCODE registry

**Moore, Pratt, Fan et al. · Nature, 2026**  
*An expanded registry of candidate cis-regulatory elements.* [Article / DOI](https://doi.org/10.1038/s41586-025-09909-9)

**Question.** How can biochemical and functional evidence be combined into a broader reference map of regulatory DNA?

**Approach and findings.** The authors expand the human registry to approximately 2.37 million candidate regulatory elements, incorporate additional categories, and integrate large-scale functional evidence. They show that some elements can have enhancer or silencer roles in different contexts. The paper also illustrates how regulatory annotations can support investigation of trait-associated loci.

**Why it matters to us.** SCREEN provides a coordinate-based framework for annotating our experimental regions. It helps ask whether a reporter-active region has an enhancer-like signature, lies near a promoter, or belongs to another regulatory class.

**Limits and use.** Candidate status and functional profiling are not equivalent to a positive enhancer result in every cell. Our downloaded ELS subset does not contain every registry class. Start with it for pELS/dELS annotation; obtain or identify the appropriate additional annotation only if a later question requires it. Do not use “absent from ELS” as a negative class.

### P02 lentiMPRA across three cell types

**Agarwal, Inoue et al. · Nature, 2025**  
*Massively parallel characterization of transcriptional regulatory elements.* [Article / DOI](https://doi.org/10.1038/s41586-024-08430-9)

**Question.** Which candidate sequences drive reporter transcription, and what determines activity and cell specificity?

**Approach and findings.** The study assays more than 680,000 sequences across HepG2, K562, and WTC11 cells, and reports 41.7% as active under its experimental criteria. A joint library of approximately 60,000 elements is tested across all three contexts. The authors find stronger cell specificity among potential enhancers than promoters and relate specificity to transcription-factor motifs. They also train quantitative sequence models.

**Why it matters to us.** This is the clearest starting dataset because the joint library allows comparison of the same constructs with the same broad assay design across cells. The paper's Figure 5 and Tables S10–S11 directly inform the first analysis.

**Limits and use.** These are reporter measurements averaged over integration contexts, not native-locus gene effects. The joint library was selected partly using earlier activity measurements, so its distribution is not representative of all genomic DNA. Preserve controls, promoter/enhancer categories, construct identities, and biological replicates. Reproduce a cross-cell comparison before adding a new analysis. The article's first authors are Agarwal and Inoue; the earlier local guide citation to Klein was incorrect.

### P03 Why reporter assays disagree

**Zhang et al. · Genome Biology, 2025**  
*Comprehensive evaluation of diverse massively parallel reporter assays to functionally characterize human enhancers genome-wide.* [Article / DOI](https://doi.org/10.1186/s13059-025-03828-8)

**Question.** Do different high-throughput reporter assays identify the same active regulatory regions?

**Approach and findings.** The authors compare six K562 datasets spanning tiling MPRA, lentiMPRA, ATAC-STARR-seq, and whole-genome STARR-seq. They investigate library coverage, reproducibility, processing, orientation, and overlap definitions. Uniform processing improves agreement, but differences remain. Transcriptional signals provide information alongside chromatin features.

**Why it matters to us.** This study supplies both reusable processed material and a warning against simplistic data merging. A sequence missing from an active-call list may never have been adequately measured. The denominator should be the jointly tested set, not the entire genome or the union of positive calls.

**Limits and use.** Requiring activity in both orientations increases stringency but can exclude genuine candidates with insufficient or asymmetric evidence. LentiMPRA and STARR-seq have different assay properties. Reproduce one comparison using the authors' definitions before testing alternatives. Comparisons to reused lentiMPRA data are provenance checks, not independent validation. A generic “assays disagree” project would largely repeat this paper.

### P04 VISTA developmental enhancer evidence

**Kosicki et al. · Nucleic Acids Research, 2025 issue; online 2024**  
*VISTA Enhancer browser: an updated database of tissue-specific developmental enhancers.* [Article / DOI](https://doi.org/10.1093/nar/gkae940)

**Question.** How can in-vivo developmental reporter results, images, and allelic comparisons be organized for reuse?

**Approach and findings.** The updated resource organizes loci, sequence alleles, experiments, and individual embryos. It includes tissue annotations, reporter backbones, developmental stages, and images. The paper reports more than 4,500 experiments at publication; our downloaded snapshot contains a different, later number of experiment records.

**Why it matters to us.** VISTA can support focused examples showing how a sequence's developmental tissue activity differs from its activity in cultured cells. It also offers a distinct future project on developmental specificity or allele-associated changes.

**Limits and use.** Candidates were selected for testing, not sampled uniformly from the genome. A negative result is conditional on the assay and tested stage. Related alleles and repeated experiments must be grouped by locus when evaluating a model or uncertainty. Human source DNA tested in mouse embryos remains evidence from a mouse reporter context. An image table is metadata, not proof that the image files themselves are downloaded.

### P05 Synthetic enhancer grammar in hematopoiesis

**Frömel et al. · Cell, 2025**  
*Design principles of cell-state-specific enhancers in hematopoiesis.* [Article / DOI](https://doi.org/10.1016/j.cell.2025.04.017)

**Question.** How can combinations of transcription-factor binding sites generate selective activity during blood-cell differentiation?

**Approach and findings.** The published paper describes 64,400 fully synthetic sequences designed around binding sites for 38 transcription factors and their interactions. It assays multiple hematopoietic progenitor states and also uses K562 experiments. Identical sites can activate or repress depending on context. Combinations of activating sites can neutralize one another or become repressive, helping create cell-state-specific patterns.

**Why it matters to us.** This is our strongest alternative to a prediction-centered project: analyze controlled sequence designs to understand interactions, rather than merely assign binary labels. Author figure code and the R dataset may make a focused reproduction feasible.

**Limits and use.** Designed sequences, experimental backgrounds, and mouse progenitor contexts should remain separate from human genomic enhancer annotations. Pairwise interactions require a defined response scale and matched controls. Reproducing negative synergy would reproduce an existing finding; a new contribution would need a narrower, demonstrably unaddressed question.

### P06 Earlier version of the hematopoiesis study

**Frömel et al. · bioRxiv, 2024; preprint**  
*Synthetic enhancers reveal design principles of cell state specific regulatory elements in hematopoiesis.* [Preprint / DOI](https://doi.org/10.1101/2024.08.26.609645)

The preprint presents the same central motif-combination and cell-state logic, but its abstract describes 62,126 synthetic sequences, compared with 64,400 in the published article. Treat it as the earlier version of P05, not an independent replication or an extra dataset to concatenate. Use the published paper for the principal summary and retain the preprint for version-specific methods or historical comparisons. A complete reconciliation of their supplementary datasets has not been performed.

### P07 Earlier DNABERT-Enhancer study

**Sathian, Dutta, Ay and Davuluri · bioRxiv, 2025; preprint**  
*Genomic language model for predicting enhancers and their allele-specific activity in the human genome.* [Preprint / DOI](https://doi.org/10.1101/2025.03.18.644040)

The authors fine-tune a pretrained DNA language model using enhancer annotations and apply it to genomic sequences and candidate variants. The preprint reports 88.05% accuracy on held-out data. It is the earlier version of P08, not a separate experimental confirmation. Retain it to understand the project's evolution, but use the journal article and the exact checkpoint provenance when interpreting current results.

### P08 Published DNABERT-Enhancer

**Sathian, Dutta, Ay and Davuluri · Bioinformatics, 2026**  
*Genomic language model for predicting enhancers and their allele-specific activity in the human genome.* [Article / DOI](https://doi.org/10.1093/bioinformatics/btag456)

**Question.** Can sequence representations learned by a genomic language model discriminate annotated enhancers and help prioritize variant effects?

**Approach and findings.** The models use 201-bp or 350-bp sequences, with ENCODE-derived positives and sampled genomic negatives. The main benchmark balances the two classes and holds out 20% of sequences. The paper reports 82.04% accuracy for the 201-bp model and 88.05% for the 350-bp model; the latter has MCC 0.7622. It also reports cell-specific models, genome-wide predicted regions, and candidate allele effects.

**Why it matters to us.** We already have the model archive and code, so an existing predictor can be investigated later without inventing a replacement. A useful question is whether its score tracks our experimental measurements or only the kind of annotation used to train it.

**Limits and use.** Negative-set design, sequence length, and training/test relatedness influence the task. A sequence's predicted enhancer probability is not its expected reporter activity. Predicted variant effects are hypotheses. Before using a checkpoint, identify its training data and evaluate overlap with our proposed test regions. Do not crop a 200-nt reporter insert to fit a different input length and assume the biological construct is unchanged.

### P09 AlphaGenome

**Avsec et al. · Nature, 2026**  
*Advancing regulatory variant effect prediction with AlphaGenome.* [Article / DOI](https://doi.org/10.1038/s41586-025-10014-0)

**Question.** Can one sequence model combine long genomic context with detailed predictions across many regulatory measurements?

**Approach and findings.** AlphaGenome takes approximately 1 Mb of DNA and predicts thousands of tracks across modalities including expression, accessibility, binding, histone marks, contacts, and splicing. The authors report matching or exceeding the strongest compared models in 25 of 26 variant-effect evaluations. Reference and alternative sequences can be compared to predict molecular consequences.

**Why it matters to us.** It broadens the project beyond a single enhancer/non-enhancer score. Later, a small set of well-supported regions or variants could be examined for predicted changes in relevant molecular readouts.

**Limits and use.** “25 of 26 evaluations” is a count of benchmark comparisons, not 96% enhancer accuracy. Predictions remain modality- and context-dependent. Our code snapshot does not establish that all model weights, runtime requirements, or external access are ready. We should not make running or retraining this model a prerequisite for our initial data analysis.

### P10 AlphaGenome Atlas

**AlphaGenome Atlas team, led by Cheng, Taylor and colleagues · medRxiv, 2026; preprint**  
*AlphaGenome Atlas: in silico mutagenesis of the entire human genome improves prioritization and interpretation of non-coding variants.* [Preprint / DOI](https://doi.org/10.64898/2026.09.16.26363192)

**Question.** Can precomputed sequence perturbations make genome-wide variant prioritization and mechanistic interpretation easier?

**Approach and findings.** The authors apply AlphaGenome to possible single-nucleotide changes and many observed indels. They derive an AlphaGenome Variant Impact (AVI) score that integrates predicted effects with additional information, and produce motif maps and feature attributions. Their analyses illustrate applications to genetic interpretation.

**Why it matters to us.** Selected precomputed annotations could eventually help interpret a small candidate set, avoiding a requirement to generate predictions genome-wide ourselves.

**Limits and use.** This is a preprint, not an independent experimental atlas of enhancer activity. AVI is not simply an enhancer score and is trained using variant-frequency-based proxy labels. We have the paper and companion materials, not the full Atlas. Any future use must identify the exact data version, tissue/readout, and score meaning. Our project can use it for research hypotheses; it would not establish clinical consequences.

## 6 The older prediction literature and reported accuracy

The four studies below are named in `legacy_references.tsv`. This is a brief orientation based on publisher/PubMed material; it is not a claim that their absent local PDFs or all supplements were comprehensively reviewed.

| Older work | Main idea | Why retain it |
|---|---|---|
| **iEnhancer-2L**, Liu et al., 2016 | Two-stage prediction: enhancer identification, then strength classification, using pseudo k-tuple nucleotide composition | Explains the older sequence-feature benchmark tradition. [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/26476782/) |
| **EnhancerPred**, Jia and He, 2016 | Combines selected sequence features to classify enhancers and their strength; the abstract reports 77.39% identification accuracy | Shows how feature selection and label definitions shaped early benchmarks. [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/27941893/) |
| **iEnhancer-EL**, Liu et al., 2018 | Uses ensembles of sequence-feature classifiers for identification and strength | Useful historical comparator, with evaluation tied to its benchmark. [Article](https://doi.org/10.1093/bioinformatics/bty458) |
| **MCSE-Enhancer**, Mir et al., 2023 | Stacks multiple classifiers built from sequence-derived features; the abstract reports 81.5% independent-set accuracy | Illustrates incremental benchmark improvement without changing the biological question. [Publisher abstract](https://www.sciencedirect.com/science/article/abs/pii/S0022283623004254) |

### Why the scores are not a league table

Your impression that many enhancer models report figures around 70–80% fits parts of this older literature. But these numbers are not a general ceiling on our understanding of enhancers, and the collected work does not all measure the same prediction task.

| Reported result | What it means | What it does not mean |
|---|---|---|
| EnhancerPred: 77.39% accuracy | Fraction of correct classifications in the reported benchmark setting | 77.39% reliable enhancer function across arbitrary tissues |
| DNABERT-Enhancer-350: 88.05% accuracy | Classification on its held-out, balanced annotation-derived dataset | 88.05% accuracy for reporter activity or variant effects |
| lentiMPRA cell-specific modeling: Pearson correlation around 0.81 for EnformerMPRA | Agreement between predicted and measured quantitative specificity in the paper's evaluation | 81% classification accuracy |
| AlphaGenome: strongest-comparator performance in 25 of 26 variant-effect evaluations | A result across a suite of tasks and metrics | A single percent accuracy for enhancer identification |

Sources: [EnhancerPred](https://pubmed.ncbi.nlm.nih.gov/27941893/), [P08, §3.2](https://doi.org/10.1093/bioinformatics/btag456), [P02, Fig. 5](https://doi.org/10.1038/s41586-024-08430-9), [P09](https://doi.org/10.1038/s41586-025-10014-0).

Accuracy depends on labels and class balance. As an illustrative calculation—not a result from our data—if only 10 of 100 sequences are positive, predicting every sequence as negative achieves 90% accuracy while finding none of the positives. Likewise, easy background negatives may produce a different score from carefully matched, experimentally inactive candidates.

Before comparing models, specify **the biological target, source of labels, cell context, negative class, evaluation split, and metric**. For our first project, measured activity, reproducibility, and uncertainty are more useful primary outcomes than beating a published accuracy number.

## 7 Research directions available to us

| Direction | A concrete question | Potential deliverable | Main constraint | Recommendation |
|---|---|---|---|---|
| **Cell-context activity** | Which jointly tested constructs are broadly active or selective across three cells? | Activity matrix, specificity figures, annotated examples | Paper already examines specificity; exact joins and normalization must be reproduced | **Start here** |
| **Reliability across assays** | Which K562 conclusions survive coverage, orientation, and processing choices? | Agreement/discordance table with sensitivity plots | Shared tested regions and non-independent source data | Extend the first project if overlap supports it |
| **Synthetic regulatory interactions** | Under which matched designs do motif combinations show non-additive effects? | Motif-pair interaction analysis with uncertainty | R-object inspection and careful control/scale definitions | Strong alternative if mechanism becomes the priority |
| **Developmental case studies** | How do selected sequences behave across VISTA tissues and stages? | Locus-level evidence dossiers | Different biological contexts and selection bias | Later, focused examples |
| **Existing-model evaluation** | Does an available model score agree with independent experimental activity? | Transparent evaluation and failure analysis | Training overlap, construct length, domain mismatch | Optional tool, not the project's purpose |
| **New prediction architecture** | Does a new model address an identified failure on an appropriate held-out task? | Model and reproducible benchmark | Requires a clear unmet need and credible baselines | Defer until evidence supports it |

### Our recommended outcome

Working project title: **“Context and confidence in enhancer activity.”**

The final research package should contain:

1. A reproducible, documented table connecting constructs, cells, replicates, activity, quality, and genomic annotations.
2. A clear description of broadly active, selective, weakly supported, and unresolved observations, restricted to the tested contexts.
3. A K562 comparison across assays where comparable tested regions exist, with explicit uncertainty and provenance.
4. A small set of well-explained examples showing why annotation, reporter measurements, and model predictions can differ.
5. An honest conclusion about which patterns are reproduced, which are robust to analysis choices, and which require further data.

This could support a substantial learning project, an internal research report, or eventually a manuscript if a specific new result emerges. Publication readiness cannot be inferred from the amount of downloaded data.

## 8 Analysis design

### Begin with a matched comparison

Use the lentiMPRA joint library, not the union of all eight experiments, as the initial unit of comparison. Proposed entry points are Supplementary Tables S10–S11 and these ENCODE experiment folders:

| Cell | Biological context | Joint-library accession to reconcile with the paper |
|---|---|---|
| HepG2 | Liver-derived cell line | `ENCSR405QCT` |
| K562 | Blood-derived leukemia cell line | `ENCSR203UFY` |
| WTC11 | Induced pluripotent stem-cell line | `ENCSR336MKI` |

Do not interpret these as comprehensive representations of liver, blood, or stem-cell biology. Their value is a controlled comparison among the measured cellular systems. Confirm construct matching against the design table before calculating cross-cell differences.

### Build two linked tables

| Table | One row represents | Essential information |
|---|---|---|
| **Construct/region table** | One exact assayed DNA construct or explicitly defined genomic region | Stable ID, source study/library, sequence if available, sequence hash, orientation, genomic coordinates and assembly, native/synthetic/control category, relationships to overlapping constructs |
| **Measurement table** | One construct in one cell, assay, and replicate | Accession, processing version, activity scale, DNA/RNA quantities, barcode count, QC status, tested status, activity call and criterion |

Keep normalized quantities separate from raw counts. The inspected lentiMPRA TSVs contain fractional DNA/RNA values, and the paper defines normalized RNA/DNA activity; do not silently treat these as integer sequencing counts. Do not append a combined-replicate file to its own component replicate files as if they were independent experiments.

Every derived table should record its source paths/checksums, import script version, filtering decisions, and date. Keep imported values intact and add analysis columns rather than rewriting the sources.

### Check measurement quality before asking biology

The first figures should show replicate agreement, activity distributions, control behavior, barcode support, missingness, and retained construct counts. Reproduce the paper's filtering and normalization where possible, and document any departure.

For cross-cell comparisons, check control baselines and library differences. A higher numerical score in one cell need not represent a proportionally stronger biological enhancer unless the measurement scales are comparable. Start with the published specificity definition; analyze alternative centering or rank-based summaries only as clearly labeled sensitivity checks.

Do not promote a large difference driven by a poorly measured cell into “cell specificity.” Include support requirements in every classification and preserve an unresolved category. An inactive-call threshold is operational, not a permanent property of a DNA sequence.

### Describe patterns before fitting a predictor

Build a construct-by-cell activity matrix for the reliably matched set. Examine pairwise activity comparisons and a heatmap. Summarize distributions separately for potential enhancers, promoters, and controls; the candidate-selection scheme makes these categories essential.

Potential follow-up annotations include GC content, exact insert length, cCRE class, promoter proximity, and published motif annotations. Motif enrichment requires a justified background matched for relevant biases, such as GC and library selection. A motif match is not proof of the responsible factor, especially when several factors share a binding preference.

Use effect sizes and uncertainty, not only significance tests. Estimate uncertainty from the actual replicate structure; constructs, barcodes, genomic loci, and biological replicates are different sampling units. For related constructs or overlapping regions, cluster resampling at the appropriate shared unit. Correct multiple testing when many regions or motifs are assessed.

### Add a K562 assay comparison only when the denominator is valid

Construct a coverage-aware overlap table between the selected K562 regions and another assay. Preserve four states: active, measured without detected activity, insufficient evidence, and untested. Different fragment boundaries require explicit overlap rules; partial genomic overlap does not establish identical assayed DNA.

Compare continuous scores when their meanings support it, and compare thresholded calls separately. Repeat comparisons across justified overlap and orientation definitions, using the paper's original criterion as the first reproduction. Stratify by coverage, region length, cCRE class, and promoter proximity where supported by available metadata.

The possible extension is to ask whether cross-cell-selective and broadly active constructs have different stability of K562 activity evidence after accounting for these factors. This is an **association question**: cell context and assay design are not randomized against every other source of variation. We cannot attribute every discrepancy to a biological mechanism.

The lentiMPRA data reused in the cross-assay archive must be linked to the original source. Only additional assay measurements can contribute distinct experimental evidence. Even those may share candidate selection or genomic annotations.

### Define success without chasing a score

| Milestone | Evidence that it is complete |
|---|---|
| Reliable import | All source rows accounted for; header handling and data types verified; exclusions explained |
| Valid joint library | Join cardinalities and duplicate relationships documented; failed/unmatched joins retained in a diagnostic table |
| Reproduction | Selected published summaries reconstructed with stated tolerance, or differences traced to versions/filters |
| Descriptive result | Activity and specificity patterns include controls, sample counts, uncertainty, and tested-context limits |
| Cross-assay extension | Adequate jointly tested sample identified; estimates remain interpretable under sensitivity analyses |
| Scientific conclusion | Claims distinguish observed patterns, reproduced findings, proposed mechanisms, and unresolved questions |

Before testing an extension, estimate how many independent loci remain and whether uncertainty is small enough to answer it. No specific overlap count or detectable effect is promised yet. A well-documented inability to make a fair comparison is a useful result and a reason to narrow the project.

### If models become useful later

Begin with simple descriptive or statistical baselines. If prediction is justified, compare an appropriate baseline with an existing model before training a new architecture. Group duplicates, overlapping loci, reverse complements, replicates, and related alleles so closely related observations do not leak between evaluation partitions. Document what the pretrained model has already seen; a new split cannot erase pretraining exposure.

For continuous activity, consider rank correlation and an error metric on a defined scale. For classification, report precision–recall behavior, prevalence, MCC or balanced accuracy, and threshold choice alongside any accuracy/AUROC result. Tune thresholds and preprocessing using training/validation data, never the final held-out evaluation. Predicting an ENCODE label and predicting an experimentally measured RNA/DNA response should remain distinct tasks.

## 9 A practical path forward

This is an ordered plan, not a promise that every later phase is necessary. VS Code is a suitable editor and notebook interface; the scientific work comes from the import scripts, provenance, and analysis decisions.

| Phase | Work | Deliverable | Decision gate |
|---|---|---|---|
| **0 · Strategy** | Read the papers, map evidence, define possible questions | This report and a decision log | Completed as a proposed direction; refine after seeing the data |
| **1 · Data orientation** | Import joint-library design and measurements; check header conventions, controls, duplicates, and scales | `02_data_dictionary_and_qc.md`, source ledger, QC figures | Do construct identities and replicate structure reconcile? |
| **2 · Reproduce one result** | Recreate a selected cross-cell activity/specificity summary from P02 | A reproducible notebook/script and reproduction report | Can we explain differences from the publication? |
| **3 · Describe context dependence** | Summarize reliably measured broad/selective activity; inspect annotated examples | Activity matrix, uncertainty summaries, biological interpretation | Which focused question remains after known findings are reproduced? |
| **4 · Test a bounded extension** | Join suitable K562 measurements to other assays; analyze call stability | Evidence table and sensitivity figures | Is overlap sufficient, and does this go beyond P02/P03? |
| **5 · Choose the next branch** | Deepen a robust result, switch to synthetic grammar, or evaluate an existing model | Updated strategy and explicit scope decision | Does the next action answer a biological or measurement question? |

### The first analysis session

1. Open the repository in VS Code and create a project-specific Python environment; record dependency versions. This report does not install or assume a working analysis environment.
2. Read only the joint-library design and result tables, plus the corresponding metadata and controls. Extract these selected archive members into a clearly named derived-data location while preserving the downloaded ZIP.
3. Write a small import script that produces a source ledger, join diagnostics, and a tidy measurement table. Use notebooks for explanation and plots, keeping reusable parsing code in scripts.
4. Produce four initial outputs: row/construct counts, a missingness table, replicate comparisons, and control/activity distributions.
5. Write down what those checks permit us to compare. Only then calculate cross-cell selectivity.

Tabular exploration is a reasonable first local task, with chunked or selected reads if needed. Hardware feasibility for large archives and model inference has not been assessed. We can avoid expanding tens of gigabytes merely to begin. R or an appropriate reader may be needed for the hematopoiesis `.rda` branch; its setup can wait until that branch is chosen.

### Proposed future analysis layout

The `reports/` folder is being established now. The other analysis directories below are a proposed convention for subsequent work, not evidence that their pipelines already exist.

```text
EnhancersResearch/
  NEW_2026_DATA/                 downloaded sources; preserve originals
  reports/
    README.md                   reading index and reporting conventions
    01_enhancers_evidence_and_strategy.md
    01_enhancers_evidence_and_strategy.html
    decisions.md                dated decisions and unresolved choices
    assets/                     small report-specific evidence files
  scripts/                      reusable import and analysis code [future]
  notebooks/                    explanatory analyses [future]
  data/derived/                 rebuildable analysis tables [future]
  results/                      figures and computed outputs [future]
```

Version small reports, scripts, metadata, and environment specifications. Keep large downloads and derived tables out of ordinary Git history; set ignore rules before generating them. A report's methods should make its results reproducible without copying the large inputs into Git.

## 10 Decisions to carry into the next session

**Proposed working direction:** understand measured enhancer activity and its reliability across contexts. A new prediction model is optional and currently deferred.

**First unit of analysis:** an exact jointly assayed lentiMPRA construct, linked to separate cell/replicate measurements. Genomic intervals become the join unit for a later cross-assay comparison, with explicit boundary caveats.

**First biological distinction:** broadly active versus selective reporter behavior among the three tested cell contexts. Do not generalize “broad” to all tissues or call a weakly measured construct inactive.

**First result to reproduce:** a joint-library cross-cell activity or specificity summary from P02. Choose the exact panel and numerical tolerance after inspecting the relevant supplementary table structure.

**Possible extension:** association between cell selectivity and stability of K562 activity evidence across assays and analysis choices. Its feasibility and novelty remain open.

**Unresolved before that extension:** exact construct joins; authors' QC and normalization; overlap with independently measured K562 regions; sufficient locus counts; suitable promoter/cCRE annotations; and the availability of required sequence information.

**Alternative if the extension is uninformative:** use P05's designed motif combinations for a focused mechanistic reanalysis. This choice should follow evidence and interest, not the size of an archive.

## 11 Short glossary

| Term | Meaning in this project |
|---|---|
| Allele / variant | An alternative DNA sequence / a difference from a reference sequence |
| Barcode | A short identifying sequence used to associate reporter measurements with a construct |
| BED | A genomic interval format; standard BED coordinates are zero-based with an exclusive end, as also specified in the inspected cross-assay dictionary |
| Biological replicate | An independently repeated biological experiment; multiple barcodes are not automatically biological replicates |
| cCRE | Candidate cis-regulatory element |
| Chromatin | DNA with associated proteins; its state influences regulatory access and interactions |
| cis-regulatory | Acting through a DNA regulatory element on the same DNA molecule as its target |
| Construct | The particular DNA insert and reporter design tested experimentally |
| FDR | False discovery rate: an error criterion for a collection of statistical calls |
| GRCh38 / hg38; hg19 | Genome assembly labels; coordinates from different assemblies cannot be mixed directly |
| GRO-cap | An assay used to detect capped nascent transcription initiation; related annotations appear in the cross-assay archive |
| k-mer | A sequence substring of length k, used in some sequence representations |
| Motif | A recurring sequence pattern, often associated with a protein-binding preference |
| MPRA | Massively parallel reporter assay |
| Promoter / TSS | Transcription initiation region / transcription start site |
| Regulatory grammar | The contribution of motif identity, arrangement, and combinations to regulatory behavior |
| Reporter | An engineered readout used to measure activity of a tested sequence |
| Sequence-to-function model | A model predicting molecular measurements or functional labels from DNA |
| Specificity | Relative preference for activity in particular measured cell or tissue contexts |
| STARR-seq | Self-transcribing active regulatory region sequencing |
| Transcription factor | A protein that participates in regulation of transcription, often through sequence-dependent DNA binding |

## 12 Sources and scope

The ten collected publication files are individually summarized in Section 5. For the two preprint/journal pairs, the journal article is the principal source. The four legacy references in Section 6 are orientation summaries based on accessible primary abstracts or publisher text. The Fulco activity-by-contact paper is an additional background reference, not one of the 109 downloaded resources.

The inventory combines the final download audit with direct inspection of selected tables, archive member lists, data dictionaries, code READMEs, and publication text. It does not assert that every supplementary object has been analyzed, every archive fully extracted, or every result reproduced. Figures, numbers, or conclusions generated in future sessions should be recorded in separate dated reports rather than retroactively presented as findings of this strategy document.

### Local publication index

| ID | Local copy |
|---|---|
| P01 | [An_expanded_registry_of_candidate_cis-regulatory_elements_Nature_2026.pdf](https://www.nature.com/articles/s41586-025-09909-9.pdf) |
| P02 | [Massively_parallel_characterization_of_transcriptional_regulatory_elements_Nature_2025.pdf](https://www.nature.com/articles/s41586-024-08430-9.pdf) |
| P03 | [Comprehensive_evaluation_of_MPRA_and_STARR-seq_Genome_Biology_2025.pdf](https://genomebiology.biomedcentral.com/counter/pdf/10.1186/s13059-025-03828-8.pdf) |
| P04 | [VISTA_Enhancer_Browser_updated_database_NAR_2024.html](https://pmc.ncbi.nlm.nih.gov/articles/PMC11701537/) |
| P05 | [Design_principles_cell-state-specific_enhancers_in_hematopoiesis_Cell_2025.html](https://pmc.ncbi.nlm.nih.gov/articles/PMC12173716/) |
| P06 | [Synthetic_enhancers_in_hematopoiesis_bioRxiv_2024_preprint.pdf](https://www.biorxiv.org/content/10.1101/2024.08.26.609645v1.full.pdf) |
| P07 | [DNABERT_Enhancer_bioRxiv_2025_preprint.pdf](https://www.biorxiv.org/content/10.1101/2025.03.18.644040v1.full.pdf) |
| P08 | [DNABERT_Enhancer_Bioinformatics_2026_full_text.html](https://oup.silverchair-cdn.com/article-minimal/8790335) |
| P09 | [AlphaGenome_variant_effect_prediction_Nature_2026.pdf](https://www.nature.com/articles/s41586-025-10014-0.pdf) |
| P10 | [AlphaGenome_Atlas_medRxiv_2026_preprint.pdf](https://www.medrxiv.org/content/10.64898/2026.09.16.26363192v1.full.pdf) |

### Reading order for our first project

Start with **P02** for matched functional measurements and its Figure 5; then **P03** for assay comparability; then **P01** for annotation and regulatory context. Read **P05** to explore the mechanistic alternative. Use **P04** for developmental questions and **P08–P10** if model-based interpretation becomes useful. Read the earlier preprints alongside their journal versions only when version differences matter.
