# Independent evaluation of the iEnhancer-2L reconstruction

**20 October 2026 · Local design defined · Cohort independence not verified · Evaluation not run**

The next evaluation will ask whether our existing enhancer detector carries useful information to different DNA sequences with experimental activity labels. We will keep the saved model fixed, finish the separation checks, save predictions without their experimental answers, and then join the answers once to measure performance.

The proposed first test uses **human DNA fragments tested in the VISTA developmental reporter assay**. This gives us experimentally tested active and inactive fragments before the separate comparison with activity in HepG2, K562, and WTC11. It tests transfer to a different biological setting, not exact reproduction of the original paper.

The design is recorded in [the machine-readable protocol](../replication/ienhancer_2l/independent_evaluation/protocol.json). The [readiness audit](../replication/ienhancer_2l/independent_evaluation/checkpoints/2026-10-20-design/readiness.json) distinguishes verified files from unresolved cohort checks. Defining a test does not mean an independent test set is already ready.

## The question and the fixed model

The primary question is: **does the saved layer-I iEnhancer-2L score rank VISTA-active fragments above VISTA-negative fragments after excluding related training and previously examined sequences?**

We retain the original primary PseKNC reconstruction and its saved layer-I SVM, trained on all 2,968 historical benchmark records. It has 4,105 sequence features, weight 0.1, C=32768, gamma=0.0078125, and a zero decision cutoff. We will not replace it with a later DNA-word or balanced-feature model because that model looked better on an already examined benchmark. No external examples enter fitting, scaling, parameter selection, calibration, or threshold choice.

Both final model files are pinned to their original training-audit hashes. **Layer II remains preserved but is not evaluated against VISTA activity:** an active/inactive developmental assay does not provide the historical strong/weak labels it was trained to predict. This test therefore cannot establish the accuracy of the full three-label cascade.

## Why use VISTA first

VISTA records direct reporter experiments, including explicit negative curation. We will select human reference allele 0, stage e11.5, and the hZR backbone. That backbone uses an Hsp68 promoter and lacZ reporter with random integration into mouse embryos. Keeping one stage and assay avoids treating different experimental procedures as interchangeable. A VISTA negative means the positive curation criteria were not met in that assay, not that the fragment is inactive in every cell or tissue. [VISTA paper](https://doi.org/10.1093/nar/gkae940) · [Official browser](https://enhancer.lbl.gov/vista/) · [Official data](https://gitlab.com/egsb-mfgl/vista-data).

Our rule uses all eligible fragments, not a selection based on model scores or an artificially balanced subset. Tested DNA must match its reference sequence in either orientation, contain only A/C/G/T, and be at least 200 bases long. Agreeing repeats collapse to one fragment; conflicting sequences, coordinates, or labels exclude the locus. Fresh reference and coordinate checks are still required.

VISTA activity in mouse embryos is different from chromatin-state annotations and from the later human cell-line assay. Performance here will describe this selected assay cohort and our declared transfer rule, rather than universal enhancer function.

## What has already been seen

This is not a blinded study or a registration made before all data exposure. We already know the historical benchmark results, feature comparisons, author-server predictions, eight-case diagnosis, and aggregate lentiMPRA QC findings. Public VISTA labels were also inspected for the archived MCSE plan.

That earlier VISTA metadata and exact-match audit retained **1,847 preliminary fragments: 953 positive and 894 negative**. These are historical feasibility counts, not the sample size for this new evaluation. Near-sequence, genome-coordinate, family, and future-study reservation checks were not completed. No VISTA iEnhancer-2L score-versus-label analysis is present in the inspected records. We preserve the MCSE plan as an archive and define a separate iEnhancer-2L protocol.

A new random split of the historical benchmark cannot undo its use in training and repeated comparisons. The 400-record historical test, the 13 author-example windows, and the 200 server-comparison queries are also previously examined evidence, not a new confirmation set.

## Requirements for a separate cohort

Before producing external predictions, complete these checks without using score-versus-activity results to change them:

1. **Verify sequence and coordinate provenance.** Pin the reference genomes and mapping chains. Verify hg38 VISTA fragments and historical hg19 records. Candidate intervals must map completely and uniquely to hg19 and back to exactly the original interval. Exclude failed, partial, and ambiguous candidate mappings. Resolve previously examined query loci conservatively; an unresolved real-genome origin keeps the check pending.
2. **Exclude all earlier evidence.** Screen against all 3,368 legacy records, all 13 example windows, all 200 previous server queries, and any additional known prior queries. For every possible 200-base substring of a candidate, compare both orientations. Exclude any exact match or global edit distance of 40 or less. Do not restrict this exclusion screen to the later prediction grid.
3. **Exclude shared loci and related families.** Exclude overlap or a genomic gap of 1,000 bases or less with an earlier record. Form connected families using proximity, shared source loci, and qualifying sequence similarity. Build the connections before propagating exclusions, including connections through rejected eligible fragments. Remove entire linked families and never count their windows as independent samples.
4. **Reserve the later cell-line study.** Screen against all 60,000 S10 design inserts after verifying adapter removal and coordinates. Remove linked VISTA families so those designs are reserved for the later lentiMPRA comparison. This step uses design information, not measured activity. The VISTA cohort is not ready while this reservation is unresolved.
5. **Record label lineage and freeze membership.** Trace known source reuse and disclose remaining uncertainty about the authors’ original sampling. Save included IDs, excluded IDs and reasons, verified coordinates, family assignments, source hashes, and a separate label table before inference.

The 1,000-base and 40-edit rules are conservative project safeguards, not proven boundaries of biological independence. Approximate sequence matching cannot certify the similarity check unless its recall at the exclusion cutoff is guaranteed and tested against exhaustive fixtures. Genomic correlation, short motifs, source ascertainment, and curation effects can remain after these checks.

Before scoring, require at least **100 distinct families containing positives and 100 containing negatives**. Report mixed-label families, the largest family, and the final counts. This is a pragmatic minimum, not a statistical power guarantee. If it fails, report insufficient independent support rather than relaxing the filters after inspecting performance.

## Scoring a longer experimental fragment

The model accepts 200-base sequences; VISTA tests longer fragments. In verified genomic-forward orientation, take 200-base windows every 50 bases, include the final complete window ending at the fragment boundary, and deduplicate window starts. Do not pad short fragments or select an orientation based on its score.

The primary fragment score is the **maximum saved layer-I decision score** across these fixed windows. Each experimentally tested fragment contributes one observation. A score above zero predicts enhancer; zero or below predicts non-enhancer. The arithmetic mean of the same window scores is a secondary robustness check, never a replacement chosen after seeing results.

This is a specified transfer rule, not part of the original published benchmark. The experimental label belongs to the whole fragment; it must not be copied onto every window as though each were measured separately. A maximum score is not an activity measurement or calibrated probability.

Longer fragments offer more opportunities for a high maximum. Report lengths and window counts by class, results in fixed length bins of 200–499, 500–999, 1,000–1,999, and at least 2,000 bases, and simple length and GC-content controls. Those controls use larger raw values as positive scores, with no fitted calibration or outcome-driven reversal.

## Measurements and uncertainty

The primary endpoint is **fragment-level ROC AUC with a 95% interval**. It asks whether active fragments tend to receive higher scores than negative fragments; it is not the percentage classified correctly.

Secondary outcomes include average precision with positive prevalence; accuracy, balanced accuracy, MCC, sensitivity, specificity, and the confusion matrix at the unchanged zero cutoff; the mean-window-score analysis; the fixed length strata; and descriptive comparisons with length and GC controls. Undefined strata remain undefined rather than being merged after inspecting their results. Average precision uses its step-function definition, not trapezoidal area under a precision–recall curve.

Use 2,000 bootstrap samples of whole connected families with seed 20261020. Include every fragment in a sampled family, with its sampling multiplicity; use the same draws for paired contrasts. Skip and count single-class draws, requiring at least 1,900 valid draws for the percentile interval. Otherwise report the interval as not estimable. The intervals condition on the fixed model and selected cohort and omit retraining, source-curation, original S1 selection, and total design uncertainty. Secondary intervals are pointwise and are not adjusted for multiple comparisons.

A primary interval wholly above 0.5 would support discrimination in this cohort. It would not prove tissue-specific activity prediction, strong/weak classification, exact reproduction, or superiority to an accuracy quoted from a different assay. A poor or inconclusive result must be reported. It is not a reason to change the model using these answers.

## Order of execution

1. Verify this protocol, inputs, code, and the original saved models.
2. Complete the cohort checks and freeze its membership, families, exclusions, labels, reference receipts, and scoring environment.
3. Validate the external layer-I runner with synthetic cases and previously recorded prediction fixtures, without examining VISTA score–label associations.
4. Score windows and fragments with no assay labels supplied to the prediction API. Save and hash both prediction tables before joining answers.
5. Join the sealed predictions to curator labels once and report all declared outcomes and limitations. Later changes require a new version and are exploratory on this exposed cohort.

The local readiness audit verifies pinned inputs and model identities only. It does not inspect new assay outcomes, certify independence, fit models, or generate external predictions. See [the saved readiness record](../replication/ienhancer_2l/independent_evaluation/checkpoints/2026-10-20-design/readiness.json). All other gates remain pending.

## The later comparison in three cell types

[Agarwal, Inoue et al.](https://www.nature.com/articles/s41586-024-08430-9) tested the same designed DNA library in HepG2, K562, and WTC11. This allows a later matched comparison across cellular settings. The VISTA test is an earlier, separate assay evaluation; it does not substitute for that comparison.

Before any score–activity join, the later study needs its own exact protocol: validated 200-base inserts, reference and family exclusions, resolved IDs and control sequences, one consistent representation of ENCODE measurements, reproduced normalization and replicate aggregation, and predetermined measurement/coverage rules. The full S10 design is reserved here. Exclude families linked to the historical records, previously tested probes, and the completed VISTA evaluation from that later confirmation cohort.

The planned primary question concerns layer-I scores versus measured activity in each cell. Specify the activity scale, common measurement cohort, Spearman association endpoints, family-based uncertainty, and multiplicity across three cells before the join. Layer-II work is secondary; its historical strong/weak labels are not experimental high/low activity labels. These requirements define the handoff, not a completed lentiMPRA processing protocol or result.

A weak VISTA result would not prove the model cannot relate to activity in another setting. It must remain visible, and any subsequent model revision needs a new evaluation design and fresh confirmation data.

## Current state and next action

The local protocol is defined, 30 source and code files are pinned, and both saved model hashes match the historical training audit. **The independent cohort is not verified, and no external predictions or performance measurements have been produced.**

The next concrete step is to implement and verify the reference, similarity, family, prior-probe, and S10 reservation screens, then freeze a final iEnhancer-2L cohort manifest. Source refreshes or rule changes require a new recorded version; they must not silently replace this design or the archived MCSE record.

Original method: [Liu et al.](https://doi.org/10.1093/bioinformatics/btv604). The external-cohort filters, aggregation, and reporting rules above are this project’s design choices, not procedures attributed to that paper or the VISTA publication.
