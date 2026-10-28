# Research decision log

## 2026-10-10 · Initial strategy

**User direction:** explore what the papers and data make possible; do not assume the objective is another enhancer predictor.

**Proposed first project:** describe measured enhancer activity across HepG2, K562, and WTC11 using the matched lentiMPRA library. Consider a later K562 cross-assay reliability analysis if comparable observations exist.

**Why:** the collection contains direct measurements and controlled biological comparisons, as well as prediction methods. Understanding context and measurement reliability can be valuable without a new architecture.

**Expected first deliverable:** a data dictionary, provenance ledger, join/QC diagnostics, and a reproduced cross-cell summary from Agarwal et al. These are planned, not yet computed.

**Novelty status:** cell specificity and cross-assay disagreement have already been studied in the collected papers. A specific extension requires a closer comparison to those analyses and a feasibility check; no new discovery is claimed.

**Open decisions:** exact reproduction panel; source-table joins and normalization; sufficient independently measured K562 overlap; whether synthetic motif interactions are a more compelling second project.

**Deferred:** new model training, whole-genome prediction, full AlphaGenome Atlas download, and clinical interpretation.

## 2026-10-12 · Carry the audit findings into the public project status

**Evidence:** [report 02](02_workspace_audit_and_qc.md) and its computed audit; the experiment accessions and membership rule are recorded there.

**Current status:** collection and initial QC are complete. The 55,977-name specificity population is recovered; numerical scores remain unresolved. The proposed two-control-name crosswalk still requires original FASTA confirmation before sequence assignment.

**Consequences:** use one ENCODE representation per experiment, retain provenance and replicate identity, and trace normalization before new selectivity claims. Do not use the contaminated local legacy test set for sequence-independent evaluation. Repair receipt-aware downloader verification and the archived DNABERT launcher before claiming those workflows work unchanged.

**Still deferred:** a new model, validated biological conclusions, and a cross-assay extension without demonstrated independent overlapping measurements. Updating documentation does not resolve the code or normalization blockers.

## 2026-10-12 · Reproduce the original methods and connect to new measurements

**User direction:** make reproduction followed by connection to the newer study the explicit website goal, and include the original papers and their corresponding data.

**Current plan:** reconstruct iEnhancer-2L first; use EnhancerPred as a second baseline and defer the ensembles until their additional work is justified. Prepare and reproduce the lentiMPRA processing alongside reconstruction, then freeze the historical model for transfer evaluation in HepG2, K562, and WTC11. Any retraining on experimental activity is a separate analysis.

**Evidence:** [report 03](03_original_publications_replication_plan.md) recovered all training labels, traced the 100 strong test overlaps to the publisher's current S4 and inspected MCSE snapshot, identified two exact legacy-training matches in the new design, and documented code limitations. The review and labels are complete; model fitting and reproduction of published accuracy are not.

**Evaluation boundary:** do not certify performance with the contaminated test or equate historical strong/weak annotations with reporter activity. Define independent sequence/locus groups and keep tuning separate from final testing. No new model architecture or biological discovery is assumed.

## 2026-10-20 · Define independent evaluation of iEnhancer-2L

**User direction:** define an independent evaluation before comparing predictions with HepG2, K562 and WTC11 activity; keep all work local without pushing.

**Design:** [report 04](04_ienhancer_2l_independent_evaluation.md) and its [protocol](../replication/ienhancer_2l/independent_evaluation/protocol.json) fix the original saved primary layer-I SVM for an external VISTA e11.5 hZR assay evaluation. Layer II stays preserved but is not evaluated against active/inactive labels. The candidate source was previously inspected for the archived MCSE plan; this is disclosed, and its preliminary manifest is not certified or silently adopted for iEnhancer-2L.

**Separation:** exclude all legacy data, prior author-example/server probes and their related families. Verify reference assemblies, exact/near similarity, connected components and label lineage. Reserve the full later S10 design library from the earlier assay cohort. The 1,000-base and 40-edit rules reduce specified leakage risks without proving complete biological independence.

**Reporting:** one maximum layer-I score per experimental fragment from fixed 200-base windows at stride 50, ROC AUC as primary, family bootstrap uncertainty, unchanged zero cutoff, and descriptive length/GC controls. Freeze membership and predictions before joining experimental answers. No result-driven model or aggregation changes.

**Current state:** source/model integrity checked in a separate readiness audit; cohort screening and external-runner validation remain pending. No fitting, external predictions, website edits or pushes in this planning step. The later lentiMPRA processing and exact association protocol remain separate prerequisites.

## Template for the next entry

- Date and question:
- Evidence reviewed:
- Decision or provisional choice:
- Reason and alternatives considered:
- Consequences for the analysis:
- Remaining uncertainty and the check that would resolve it:
