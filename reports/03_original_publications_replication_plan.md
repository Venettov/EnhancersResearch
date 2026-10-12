# Original enhancer publications and replication plan

**Research report 03 · 12 October 2026**\
**Question:** Which publications supplied by Prof. Dehzangi can we replicate, and how can their methods inform the resources in `NEW_2026_DATA`?\
**Status:** paper review, sequence comparisons, label recovery, and static code inspection completed. No models were trained and no published prediction metrics were reproduced.\
**Data versions:** original files at repository commit `9ba24dc0595d1cb39793c6fec9d80d779c36c33e`; new-resource inventory rechecked on 12 October; MCSE author-code snapshot `d76c48946de9c46e0845df12c119a27b7e455444`. Input hashes accompany the [computed evidence](assets/2026-10-12_original_publications_review.json).

**iEnhancer-2L is the best first method to reconstruct.** Its benchmark sequences, strong/weak labels, feature equations, and DNA structural-property tables are available. EnhancerPred is a useful second, simpler feature comparison. iEnhancer-EL requires more ensemble reconstruction, while MCSE-Enhancer has public code that needs substantive repair before use. None currently qualifies as a verified reproduction of its published performance.

These four papers largely reuse one historical benchmark. They offer methods and baselines, rather than four independent sets of biological evidence. The most useful connection to the weekend's downloads is to test how their sequence features relate to experimentally measured enhancer activity. The immediate experimental priority remains the lentiMPRA import and normalization work identified in [report 02](02_workspace_audit_and_qc.md); this review does not replace that plan with a new-model project.

## Scope and meaning of replication

The original collection contains four research articles and two supplementary PDFs. The ZIP is another container for the two supplements, not a fifth study.

| Original file | Publication or role |
|---|---|
| [bioinformatics_32_3_362.pdf](../bioinformatics_32_3_362.pdf) | Liu et al., **iEnhancer-2L**, Bioinformatics 2016; online 2015. [DOI](https://doi.org/10.1093/bioinformatics/btv604) |
| [srep38741.pdf](../srep38741.pdf) | Jia and He, **EnhancerPred**, Scientific Reports 2016. [DOI](https://doi.org/10.1038/srep38741) |
| [bioinformatics_34_22_3835.pdf](../bioinformatics_34_22_3835.pdf) | Liu et al., **iEnhancer-EL**, Bioinformatics 2018. [DOI](https://doi.org/10.1093/bioinformatics/bty458) |
| [1-s2.0-S0022283623004254-main.pdf](../1-s2.0-S0022283623004254-main.pdf) | Mir et al., **MCSE-Enhancer**, Journal of Molecular Biology 2023. [DOI](https://doi.org/10.1016/j.jmb.2023.168314) |
| [Supp-S1.pdf](../bioinformatics_32_3_362_s1/Supp-S1.pdf) | iEnhancer-2L's 2,968 benchmark sequences with class labels; 338 pages. |
| [Supp-S2.pdf](../bioinformatics_32_3_362_s1/Supp-S2.pdf) | Six dinucleotide structural-property tables, original and normalized values; two pages. |

There are three distinct deliverables. **Method reconstruction** implements a paper's features and learning procedure. **Numerical reproduction** also recovers its data splits, preprocessing, parameter choices, and reported results within a stated tolerance. **A new evaluation** changes the split or target to answer a better-defined question. A model retrained on lentiMPRA activity is a new evaluation or adaptation, even when its features come from an older paper.

The comparison below assesses computational reproducibility. Repeating the original wet-lab experiments would require laboratory resources beyond these files.

## What the original benchmark actually measures

iEnhancer-2L constructed its labels from ChromHMM annotations based on histone marks in nine cell types: H1ES, K562, GM12878, HepG2, HUVEC, HSMM, NHLF, NHEK, and HMEC. Its methods say strong enhancers and non-enhancers were annotated across the nine tissues, while weak enhancers were selected using human embryonic stem-cell annotations because their states varied between tissues. The final balanced benchmark contains 742 strong enhancers, 742 weak enhancers, and 1,484 non-enhancers, each 200 bases long. [Original paper, section 2.1, PDF pp. 2–3](../bioinformatics_32_3_362.pdf).

These are **chromatin-state labels**, not direct RNA/DNA reporter measurements. A historical “strong enhancer” is therefore not automatically a highly active lentiMPRA construct. Likewise, a historical “non-enhancer” is not established to be inactive in every cell or experiment. The old benchmark includes HepG2 and K562 among its annotation sources, but it does not provide matched measurements of each sequence in those cells. H1ES and WTC11 are also different cell models: an embryonic stem-cell line and an induced pluripotent stem-cell line, respectively.

The original labels remain useful for reconstructing the methods and studying annotation-based prediction. They should not be merged with modern activity values as though both were the same ground truth.

## New findings from the original materials

### The complete training labels are recoverable

Parsing Supplement S1 recovered exactly **2,968 unique sequences of 200 bases**, with its published 742/742/1,484 class counts. Sequence matching, independent of header spelling or record order, gives the following result:

| Local file | Records | Match to Supplement S1 |
|---|---:|---|
| `enhancer.cv.txt` | 1,484 | All match: 742 strong and 742 weak. |
| `non.cv.txt` | 1,484 | All match the non-enhancer class. |
| `enhancer.ind.txt` | 200 | Its first 100 match S1 strong enhancers; the remaining 100 are absent from S1. |
| `non.ind.txt` | 200 | All are absent from S1. |

This resolves a practical prerequisite for reproducing the older strength classifiers. The [sequence-label crosswalk](assets/2026-10-12_original_publications_review_sequence_labels.tsv) records local filenames and row numbers, sequence hashes, source headers, labels, and PDF pages. It preserves the original input files.

### The test overlap is present in published and public copies

The publisher's current **iEnhancer-EL Supplement S4**, linked from the [2018 article](https://doi.org/10.1093/bioinformatics/bty458), contains 100 strong enhancers, 100 weak enhancers, and 200 non-enhancers. All 400 sequences, in order, match our local independent files. **All 100 strong test enhancers exactly match sequences in Supplement S1.** This conflicts with the article's section 3.2 statement that none of the independent examples occurs in training.

The current [MCSE author repository at the inspected commit](https://github.com/MirBilalAhmad/DNA-Enhancers/tree/d76c48946de9c46e0845df12c119a27b7e455444) likewise contains the same training and test sequences in the same order. The 100 overlaps therefore occur in three inspected copies: our files, the publisher's current S4, and the current MCSE code snapshot. These checks trace present-day artifacts; they do not establish which exact bytes were used in every historical experiment or quantify the effect on a trained model's accuracy.

The consequences differ by task. For enhancer/non-enhancer classification, removing the exact duplicates leaves 100 positives and 200 negatives, changes the class balance, and still requires similarity and genomic-overlap checks. For **strong/weak classification, removal leaves zero strong examples**, so the remaining test cannot evaluate that task. Simply deduplicating the 400 records does not produce a satisfactory replacement benchmark. Use a newly defined, grouped evaluation with adequate classes, and retain the original split only as a clearly labeled historical diagnostic.

### Two old training sequences occur in the new lentiMPRA design

Table S10 contains 60,000 sequences of 230 bases. Removing its documented 15-base adapter at each end yields 200-base inserts, matching the old benchmark's sequence length. Comparing every old training/test sequence with those inserts found two exact matches, both among the old strong training enhancers:

| Local enhancer training row | Original header | S10 construct |
|---:|---|---|
| 385 | `CHR5_133839101_133839301` | `K562_peak65192` |
| 1,263 | `CHR22_35773000_35773200` | `HepG2_DNasePeakNoPromoter39999` |

No additional matches appeared when reverse complements were included. This is a comparison of the **design** sequences, not confirmation that both constructs pass every activity/coverage filter. It does not rule out similar sequences or overlapping genomic regions. Exclude the two training matches from any independent transfer test and screen for those broader relationships before claiming independence.

## Replication assessment for each publication

The percentages here are the papers' own reported accuracies. “Jackknife” means leave-one-out cross-validation. The first three papers evaluate enhancer identification and, separately, strength classification among enhancers; the second number is not the accuracy of the entire two-stage pipeline. Different validation procedures and unresolved data overlap prevent a fair ranking from these numbers alone.

| Paper | Method and target | Paper-reported result | Feasibility judgment |
|---|---|---|---|
| **iEnhancer-2L** | Two support vector machines (SVMs), using short sequence-pattern counts and structural descriptors. Enhancer identification, then strong/weak classification. | Jackknife: **76.89% / 61.93%**; Table 1. | **Best first reconstruction.** Local labels, equations, and property tables are available; exact numerical reproduction needs implementation and parameter details. |
| **EnhancerPred** | Two SVMs combining position-specific class profiles, nucleotide composition, and three-base pattern counts. | Jackknife: **77.39% / 68.19%**; Table 1. | **Feasible second baseline.** Compact method, but label-dependent feature fitting and selection must be reproduced carefully. |
| **iEnhancer-EL** | Selects and combines SVMs built from several sequence representations. | Jackknife: **78.03% / 65.03%**; independent test: **74.75% / 61.00%**; Tables 3–4. | **Partial reconstruction feasible; full reproduction more involved.** Ensemble selection, weights, and contaminated independent data are material obstacles. |
| **MCSE-Enhancer** | Multiple sequence descriptors and a stacked ensemble of machine-learning classifiers. Enhancer identification only. | Reported independent accuracy **81.5%**, MCC **0.59**; Table 1. | **Public code is a starting point, not a working replication.** Repair code, identify the intended pipeline, and redesign evaluation before interpreting results. |

### iEnhancer-2L

The feature representation is pseudo k-tuple nucleotide composition, or PseKNC: normalized counts of short DNA words plus terms derived from dinucleotide structural properties. Equation 13 selects **k = 6 and λ = 9** for both layers, with **w = 0.1** for enhancer identification and **w = 0.4** for strength classification. The resulting representation has **4⁶ + 9 = 4,105 components**. Supplement S2 supplies the six property tables needed by the equations. [PDF pp. 3–6, equations 4–13 and Table 1](../bioinformatics_32_3_362.pdf).

A reconstruction can recover the labeled examples, implement the features, and fit the two radial-basis-function SVMs. To match the published numbers closely, we still need to settle the numerical implementation, scaling, and SVM settings. The paper describes a search for C and gamma, but the supplied materials do not identify the final values and fold assignments needed for an exact replay. Small implementation choices should be recorded, rather than adjusted repeatedly against the final test set.

For a new performance estimate, feature choices and SVM tuning belong inside training folds. A separate report can compare this stricter estimate with an attempted historical reproduction. Changing validation silently and calling the result an exact replication would be misleading.

**Connection to new data:** use its features as an interpretable baseline for measured activity. The structural terms are sequence-derived descriptors of local DNA properties; they are not measured chromatin accessibility or evidence of enhancer–promoter looping. They can test whether these descriptors add value beyond ordinary sequence composition.

### EnhancerPred

EnhancerPred combines bi-profile Bayes (BPB) features, nucleotide composition (NC), and what this paper calls pseudo-nucleotide composition (PseNC). Its PseNC equation is normalized overlapping **three-base word frequency**; it is not the same formulation as iEnhancer-2L's PseKNC. BPB records nucleotide frequencies at each position in positive and negative training examples. [PDF methods, pp. 4–5](../srep38741.pdf).

The final feature sets contain **114 features** for enhancer identification (104 BPB, one NC, nine PseNC) and **99** for strength (89 BPB, ten PseNC). The paper gives C = 0.35355 for both SVMs, with gamma = 0.03125 and 1.4142, respectively. Its own supplementary feature-selection tables are distinct from our iEnhancer-2L supplements; those feature lists and selection details need to be retrieved or reconstructed for a faithful replay. The article describes selection and parameter searches, but no runnable local training package accompanies the supplied PDF.

**Critical evaluation rule:** BPB uses class labels to construct its features. Compute these profiles from the training fold only, then apply them to held-out examples. Feature ranking and selection must also stay within training. This is a requirement for our implementation, not evidence that we have reproduced or diagnosed every step of the original authors' execution.

**Connection to new data:** it is especially useful for separating simple sequence-composition signal from more complicated prediction. The paper highlights C composition; our earlier audit found an approximately 11–12 percentage-point GC difference between the old positive and negative classes. Include a GC-only baseline and examine composition-matched comparisons. If using BPB on MPRA, define activity classes from appropriate controls and training data first; do not calculate profiles from test activity labels.

### iEnhancer-EL

iEnhancer-EL extends the same problem using **171 candidate SVMs**: six k-mer, 15 subsequence-profile, and 150 PseKNC predictors. Affinity propagation selects six models for the first layer and ten for the second, followed by genetic-algorithm weight optimization. The main paper lists the selected feature/SVM parameters, making reconstruction of those selected members plausible. Replaying the entire selection and fusion procedure additionally needs Supplement S3, the final weights or a reproducible route to them, and stochastic settings. [PDF pp. 3–6, Tables 1–4](../bioinformatics_34_22_3835.pdf); [author downloads](https://bliulab.net/iEnhancer-EL/data/).

The publisher's S4 overlap is particularly consequential because it removes the strong class if duplicates are excluded from the strength test. Its quoted independent accuracy cannot be treated as a sequence-independent reference for our work. Table 3 also reports different EnhancerPred results from EnhancerPred's own Table 1, another reason to rerun methods under one common protocol rather than assemble a leaderboard from quoted numbers.

**Connection to new data:** its individual feature families can be compared before reproducing the full ensemble. An ensemble is worthwhile only if it improves a predefined held-out endpoint beyond simpler baselines. Retraining those members on MPRA activity would evaluate an adapted method, not reproduce the old strong/weak experiment.

### MCSE-Enhancer

MCSE-Enhancer combines six descriptor families—DCC, PseKNC, SCPseDNC, PCPseDNC, k-mer, and nucleotide physicochemical properties—with classifiers including random forests, extra trees, LightGBM, XGBoost, CatBoost, and a multilayer perceptron. Stacking combines predictions from several classifiers. It uses the 2,968-example training benchmark and 400-example independent set for binary enhancer identification. [Original PDF, methods and results](../1-s2.0-S0022283623004254-main.pdf).

The [public repository](https://github.com/MirBilalAhmad/DNA-Enhancers/tree/d76c48946de9c46e0845df12c119a27b7e455444) contains three notebooks and the sequence/label files. Static inspection found concrete obstacles:

- **Incomplete executable cells.** Training and testing notebooks contain placeholder paths and invalid Python placeholders. Four inspected code cells in each fail Python syntax parsing. Feature generation refers to additional tooling that must be supplied and versioned.
- **Test labels enter optimization.** In `Models _Testing.ipynb`, zero-based cell 77 optimizes an ensemble objective against `y_test_ind` over 50 trials. If used as written, the named independent set is involved in model selection. That prevents treating it as a final untouched test.
- **A cross-validation loop does not aggregate folds as its structure suggests.** In `Models_Training.ipynb`, cell 14 generates RF splits in a loop but fits and scores after the loop, using the last split. It does not return a ten-fold mean.
- **The supplied datasets contain the same 100 train/test duplicates.** Fixing code alone does not fix the evaluation data.

These are observations about the pinned public snapshot, not proof of the exact code path used to produce the 2023 paper. Its notebooks were inspected but not executed. A faithful reproduction needs a versioned environment, complete feature settings, the intended final ensemble, and per-example predictions. A repaired workflow should use training-only tuning and out-of-fold predictions to train its stacking stage, with final testing performed once.

There is also a reporting check to resolve: Table 1 lists sensitivity 83%, specificity 79%, accuracy 81.5%, and MCC 0.59. For one pooled confusion matrix with 200 positives and 200 negatives, the listed sensitivity/specificity imply 81.0% accuracy and approximately 0.6205 MCC. Different aggregation or a reporting error could explain the mismatch; the confusion matrix and prediction file are needed to settle it.

**Connection to new data:** compare the descriptor families and simple base classifiers before investing in the full stack. The method does not itself model cellular context or establish experimental enhancer activity. Its reported accuracy should not make it our default starting point.

## How the seven new resource folders connect

| Resource folder | Useful link to the original papers | Conditions for a valid analysis |
|---|---|---|
| **01_ENCODE4_SCREEN** | Provides modern candidate enhancer annotations. Compare old positive/negative regions with enhancer-like cCREs; annotate where legacy model predictions occur. [ENCODE4 paper](https://doi.org/10.1038/s41586-025-09909-9). | Confirm the original coordinate assembly before comparing with GRCh38. A candidate annotation is not direct proof of activity; absence from SCREEN is not a universal negative. |
| **02_LENTIMPRA_ENCODE_2025** | **Primary experimental bridge.** Its joint library supplies the same 200-base inserts measured in HepG2, K562, and WTC11. Test whether legacy scores/features predict measured reporter activity. [Agarwal, Inoue et al.](https://doi.org/10.1038/s41586-024-08430-9). | Reconcile IDs, controls, measurement coverage, and normalization. Exclude training matches; group reverse complements and related loci. Reporter activity does not by itself identify native target genes. |
| **03_MPRA_STARR_CROSS_ASSAY_2025** | Tests whether associations with legacy scores survive a change in assay design, particularly in K562. [Cross-assay study](https://doi.org/10.1186/s13059-025-03828-8). | Establish shared tested regions and measurement provenance. Some lentiMPRA data reuse folder 02's lineage; those records are not an independent replication. Assay-specific negatives and processing must remain distinguishable. |
| **04_VISTA** | Tests whether a model trained on the old benchmark has relevance to developmental reporter activity in mouse embryos. [VISTA paper](https://doi.org/10.1093/nar/gkae940). | Retain source species, assembly, tissue, developmental stage, and assay backbone. Sequences may exceed 200 bases: predefine windowing and aggregation, and account for length. A negative is conditional on the experiment. |
| **05_HEMATOPOIESIS_MPRA** | Offers a later test of whether sequence patterns capture synthetic motif combinations and cell-state differences. [Frömel et al.](https://doi.org/10.1016/j.cell.2025.04.017). | The `.rda` still needs ingestion. Group related synthetic designs/backbones together during splitting. This designed-sequence distribution differs from natural genomic fragments. |
| **06_DNABERT_ENHANCER_2026** | Supplies a contemporary pretrained prediction comparator against the older handcrafted features. [DNABERT-Enhancer paper](https://doi.org/10.1093/bioinformatics/btag456). | Its weights are present, but the archived prediction launcher points to a missing Python file. Repair and smoke-test inference, verify preprocessing, and audit its training overlap. Model outputs are predictions, not new experimental labels. |
| **07_ALPHAGENOME_2026** | Offers a later way to examine longer genomic context or predicted regulatory effects beyond the 200-base benchmark. [AlphaGenome paper](https://doi.org/10.1038/s41586-025-10014-0). | The folder holds papers, supplements, and research code; it is not a verified local inference installation or a full Atlas. A contextual model requires correctly mapped genomic input. Its predictions do not replace experimental validation. |

Folder size is not a criterion for choosing the first analysis. The strongest initial link is the matched design and direct measurements in folder 02, even though other resources occupy substantially more disk space. The prior full check found all **109 new resources, totaling 51.07 GB**, present. That establishes availability, not readiness of every upstream workflow; this review did not repeat the full 51-GB hash audit.

## A practical sequence of work

### Establish the data and reproduce the experimental summaries

Keep the original FASTA files and historical test split intact as provenance. Use the recovered labels for development, but define an evaluation with sequence-similarity and genomic-region groups before selecting models. First verify the original assembly; nearby or overlapping windows can leak information even when their strings are not identical.

For lentiMPRA, use the joint-library experiments **ENCSR405QCT (HepG2), ENCSR203UFY (K562), and ENCSR336MKI (WTC11)**. Import either the three replicate TSVs or their combined TSV for each experiment. Combining both representations duplicates measurements: the earlier audit found 3,850,212 rows versus 1,925,106 distinct rows across all eight experiments.

The 60,000-design population includes 56,904 potential enhancers, 2,396 promoters, and 700 controls. Keep these categories separate. Review the two control-name aliases against the original FASTA before assigning sequences. Retain barcode coverage and replicate measurements. The criterion “at least one replicate with at least ten barcodes in each cell” recovers the **55,977 specificity-table names**, but **not the numerical specificity scores**. Normalization and aggregation remain a prerequisite for new selectivity conclusions. A positive log2 RNA/DNA value alone is not an established activity threshold.

**Deliverable:** a documented sequence-to-measurement table, explicit exclusions, and reproduced published summaries with a declared numerical tolerance. The label map from this review is already available; the normalized lentiMPRA research table remains to be completed.

### Reconstruct one historical method and simple controls

Start with iEnhancer-2L and compare it with GC-only and ordinary k-mer baselines under common splits. Validate feature lengths, counts, property normalization, and invariance assumptions before fitting. Record the distinction between an attempted historical protocol and a stricter grouped/nested evaluation. Save fold assignments, tuning ranges, software versions, model parameters, and per-example predictions.

A two-layer reconstruction can study both old tasks using the recovered S1 labels. It should not reuse the contaminated S4 strong examples to select or certify a model. Evaluate identification and strength separately, and evaluate the complete pipeline separately if claiming end-to-end performance.

**Deliverable:** a reproducible baseline with uncertainty estimates and a clear account of any difference from the paper's numbers. EnhancerPred is the next useful feature comparison; the two ensembles can wait until they address a demonstrated gap.

### Test transfer before building another model

First freeze a model trained only on the old labels and examine its score against lentiMPRA activity in each cell. This tests **transfer from annotation labels to an experimental measurement**. Exclude the two exact training matches and any broader overlaps discovered during screening. Report correlation with continuous activity, along with coverage and uncertainty; if evaluating active/inactive classification, derive the labels from the assay's controls and criteria. Include PR-AUC, ROC-AUC, and a thresholded metric such as MCC as appropriate to the task, rather than accuracy alone.

Then, if useful, retrain the same feature representation on modern data. Continuous activity favors regression; cell-specific classification requires explicit cell-specific labels. Those are separate experiments from the frozen-model transfer test. A single sequence-only score gives the same prediction for a sequence in all three cells. Modeling a difference between cells therefore requires separate cell models, cell/context inputs, or a model that predicts multiple cell outputs.

Split related sequences once and carry that assignment across **all cell and replicate records**. Keep the 149 known reverse-complement pairs grouped. Otherwise, training on one cell's record and testing on another cell's record of the same sequence could make an unseen-sequence claim invalid. Use grouped confidence intervals rather than treating repeated measurements as independent sequences.

**Deliverable:** a cell-by-cell assessment of which old sequence features transfer, where they fail, and how much of their association is explained by simple composition or measurement reliability. This can be valuable without inventing a new architecture.

### Add one external comparison after the main analysis works

Choose either an independently measured K562 cross-assay comparison or a carefully scoped VISTA transfer analysis. Hematopoietic motif design is a distinct, promising later question. DNABERT and AlphaGenome can be comparators once their inference and training provenance are established; neither needs to be a prerequisite for the first reproducible result.

A candidate research question is: **How well do sequence features learned from historical chromatin annotations predict measured enhancer activity across cells, and what explains their failures?** Its novelty is not established by this review. The collected experimental papers already investigate cell specificity and assay effects, so a proposed contribution must be compared with their analyses before claiming a new finding.

## Evidence and how to rebuild the checks

- [Computed review evidence](assets/2026-10-12_original_publications_review.json) contains input hashes, S1 counts, S4 comparison, the two lentiMPRA matches, and the MCSE snapshot checks.
- [Sequence-label crosswalk](assets/2026-10-12_original_publications_review_sequence_labels.tsv) maps all 3,368 local records to S1/S4 labels where a sequence match exists. A training sequence appearing in S4 remains a training sequence; the crosswalk does not authorize a new split.
- [Review script](assets/review_original_publications.py) parses the supplements, checks exact sequences and reverse complements, and statically inspects notebooks. It does not execute upstream code, tune models, or download resources.
- [Prior audit and normalization limitations](02_workspace_audit_and_qc.md) and [12 October full recheck](assets/2026-10-12_workspace_recheck.json) support the new-resource readiness statements.

The script requires Python 3.10+, pypdf, pandas, and openpyxl. With the tracked originals and local lentiMPRA table archive, the basic checks run as follows:

```bash
python3 reports/assets/review_original_publications.py \
  --output /tmp/original_publications_review.json
```

To rebuild the additional publisher/code comparisons, obtain Supplement S4 from the iEnhancer-EL article and a read-only copy of the MCSE repository at the commit recorded above, then provide `--el-s4 /path/to/Supp-S4.pdf --mcse-dir /path/to/DNA-Enhancers`. The inspected S4 publisher filename is `bioinformatics_34_22_3835_s7.pdf`; its SHA-256 is `d802977a50fadf71be82b955ced1decfbcd907dcd0f8fcbd446ab2c6e374101e`. The JSON records hashes of the inspected MCSE files so a different download can be detected. The basic run intentionally omits those optional checks when their inputs are absent.

PDF equations and result tables were checked against rendered pages. Sequence extraction was accepted only after verifying record counts, labels, 200-base lengths, uniqueness, and agreement with the local FASTA files. The exact-overlap checks do not establish independence at the level of sequence similarity, genomic locus, or upstream model pretraining.
