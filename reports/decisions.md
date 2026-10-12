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

## Template for the next entry

- Date and question:
- Evidence reviewed:
- Decision or provisional choice:
- Reason and alternatives considered:
- Consequences for the analysis:
- Remaining uncertainty and the check that would resolve it:
