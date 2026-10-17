# Independent evaluation design for the repaired MCSE-Enhancer model

**Protocol and screening: 15 October 2026 · review release: 17 October 2026 · evaluation not run**

The next question is whether the repaired model carries useful information to **different sequences with experimental labels**, beyond the historical data used to reconstruct it. This plan fixes the model, candidate source, exclusions, scoring rule and reporting procedure before any external predictions are produced. It does not establish that an independent test set is already ready.

The proposed first external evaluation uses human reference fragments tested in the **VISTA developmental reporter assay**. The model was trained on historical chromatin-state annotations; VISTA measures reporter activity in mouse embryos. This is an **external generalization test across biological settings**, not a repeat of the old benchmark, a claim of exact MCSE reproduction, or the later lentiMPRA analysis.

- [Machine-readable protocol](protocol.json): fixed choices, limits and required gates.
- [Readiness audit](checkpoints/2026-10-15-design/readiness.json): current counts and what remains pending.
- [Preliminary candidate manifest](checkpoints/2026-10-15-design/preliminary_candidates.csv): IDs, coordinates, lengths, source labels and sequence hashes; **not a certified independent cohort**.
- [Exclusion log](checkpoints/2026-10-15-design/excluded_records.csv): every exclusion in the preliminary audit, with matching legacy IDs where applicable.

## What was checked today

The frozen VISTA export has 5,090 experiment rows. Applying the declared metadata filters selects 1,888 experiments: human reference allele 0, hg38, embryonic stage e11.5, hZR backbone, and an explicit positive or negative curation. The official backbone dictionary identifies hZR as Hsp68 promoter, lacZ reporter and random transgenesis. Other species, variant alleles, embryonic stages and assay backbones are excluded.

| Preliminary step | Fragments / experiments |
| --- | ---: |
| Metadata-eligible experiments | 1,888 |
| Excluded: tested sequence differs from the reference sequence in both orientations | 27 |
| Excluded: full fragment contains an exact legacy 200-base sequence, in either orientation | 14 |
| Remaining preliminary fragments | **1,847** |
| Positive / negative curator labels among those fragments | **953 / 894** |

No agreeing duplicate experiments required collapsing in this selection. The 14 exclusions contain matches to development records and historical test records; one fragment can match several legacy records. The audit scans **every** possible 200-base position, not just the future prediction-window grid. It also checks that the tested sequence matches the supplied reference sequence, and that inclusive coordinates agree with the pinned zero-based BED intervals and sequence lengths.

The remaining fragments span **304–7,786 bases** and would yield **66,555 overlapping prediction windows** under the declared tiling rule. These are input-size counts, not prediction results. There were **zero model fits, zero predictions and no performance estimates**. Ten focused tests cover coordinate conversion, sequence validation, terminal windows, forward/reverse matches, non-grid matches and the distinction between exact and near matches.

**1,847 is not the final sample size.** Genomic proximity, near-sequence similarity, connected families and reservation of the later lentiMPRA designs remain unresolved. The number of independent groups is not yet known. This audit does not certify independence, validate the exported reference against a newly downloaded genome, or repeat the full 109-resource inventory check.

## The model stays fixed

The primary model is **`notebook_k2_full`**, the first variant selected before observing MCSE benchmark performance: 15,169 features, the six recovered base classifiers, and the repaired CatBoost combining model. The 3-mer and alternative-normalization comparisons remain useful diagnostics; the slightly higher observed legacy accuracy does not promote one of them to the primary model here.

All 2,968 legacy development records, their 2,451 sequence/locus groups, the reported S1 parameters, seed 20261014, one CPU thread, training-only MLP scaling and the 2,000-iteration cap remain fixed. No VISTA labels enter training, preprocessing, early stopping, calibration, parameter choice or feature selection. No VISTA retraining is part of this evaluation.

The eventual full-training fit needs **25 fits**: six base models across three group-disjoint out-of-fold partitions, six base fits on all legacy development rows, and one combining-model fit on the out-of-fold predictions. Existing code returns predictions but does not supply a validated serialized final MCSE model. A fit/save/load implementation, synthetic leakage checks, source/environment pins and a round-trip prediction check are required first. No final model has been trained in this planning step.

## What makes this an independent evaluation

All **3,368 legacy records** form the exclusion universe: 2,968 development records plus all 400 historical test records, including duplicates. Removing only the 100 known exact duplicates from the old test does not make the remainder fresh or independent. Repartitioning previously examined development records also cannot erase the information already used in our decisions.

Before external scoring, the following checks must pass:

1. **Reconcile assemblies.** The development coordinates were verified in hg19; VISTA coordinates are hg38. Verify the historical test coordinates too. Use pinned forward and reciprocal assembly mappings, with complete, unique and reciprocal candidate intervals. Exclude candidate intervals that cannot be reconciled. Never compare coordinates across assemblies as if they were the same reference.
2. **Exclude shared loci.** Remove candidate families whose verified intervals overlap or lie within 1,000 bases of any legacy interval.
3. **Exclude similar sequences.** Screen both orientations of every legacy 200-base sequence against every contiguous 200-base candidate substring, using unit-cost global edit distance ≤40, consistent with the earlier grouping rule. This is an edit-distance criterion, not a claim of a particular percent identity. Exact matching completed today is only part of this requirement. Any accelerated search must be checked against an exhaustive oracle; a heuristic search with unknown misses cannot certify the gate.
4. **Group related candidates.** Connect fragments sharing a source locus, genomic proximity, exact/reverse-complement sequences or qualifying near-sequence matches. Remove entire components linked to excluded legacy examples. Keep all windows and related fragments together. Confidence intervals will resample these connected components, not individual windows.
5. **Reserve the later lentiMPRA study.** Screen against all 60,000 S10 design inserts after checking their adapter convention, plus verified design loci, using the same sequence/family rules. Exclude linked VISTA families so the later study remains separate. This step uses design sequences and coordinates, not activity outcomes. Unresolved design provenance leaves this gate pending.
6. **Check label provenance and freeze membership.** Document experimental label lineage and any uncertainty about historical author selection. Freeze source hashes, included IDs, exclusions, components, label mapping and the separate label file before producing scores. Public labels are accessible: this is procedural separation, not technically blinded or third-party validation.

The protocol requires at least 100 distinct components containing positives and 100 containing negatives before scoring; mixed-label components must be reported. This is a pragmatic minimum, not a formal power guarantee. Insufficient independent support is a reason to stop and report the limitation, not to relax exclusions after seeing performance.

## How a 200-base model will score a longer tested fragment

The VISTA experimental label belongs to the **whole tested fragment**. It must not be copied onto every 200-base window as though each window had been experimentally tested.

The fixed transfer rule is to take 200-base windows every 50 bases in genomic-forward orientation, add the last complete window ending at the fragment boundary, and retain the **maximum model score as one score per fragment**. Short sequences are excluded; none are padded. The arithmetic mean of those same scores is a prespecified secondary sensitivity check, not a replacement chosen after observing results.

This aggregation is a new, explicit transfer rule. The resulting maximum is **not a calibrated probability** that the full fragment is active. Longer fragments provide more opportunities for a high score. Report sequence lengths and window counts by class, simple length and GC-content score baselines, and results in the fixed 200–499, 500–999, 1,000–1,999 and ≥2,000-base strata. Do not alter window size, stride, orientation, aggregation or length limits to improve results. The assay's orientation and genomic-forward orientation are retained separately because a sequence model need not be orientation invariant.

## What will be reported

The primary endpoint is **fragment-level AUROC**, with a 95% whole-component bootstrap interval. In simple terms, this asks how often the model places a positive fragment above a negative one when comparing their scores. It evaluates ranking without selecting a new decision threshold on this cohort.

Secondary summaries include average precision with class prevalence; MCC, balanced accuracy, sensitivity, specificity, ordinary accuracy and the confusion matrix at the unchanged 0.5 threshold; mean-window-score sensitivity; length-stratified AUROC; and length-only/GC-only score baselines. These results all remain descriptive. The 0.5 threshold has not been calibrated for this assay.

Use 2,000 whole-component bootstrap draws with seed 20261015. A draw includes every fragment in each sampled component, including multiplicities. Single-class draws cannot give AUROC; report their count and require at least 1,900 valid draws for an interval. Report a non-estimable interval rather than changing the procedure. The interval is conditional on the fitted model and selected cohort, and does not capture training randomness, original S1 parameter selection, curation or all design uncertainty.

An interval above 0.5 would support discrimination **in this selected assay cohort**. It would not establish exact reproduction, universal enhancer detection, cell-specific activity prediction or superiority to the paper's 81.5% accuracy. A poor or inconclusive result is also a valid outcome. The different labels and fragment-scoring rule prevent a direct comparison with our earlier 75.74%/76.82% benchmark accuracies.

## Why these data, and why not the other available files?

| Resource | Role in this plan |
| --- | --- |
| VISTA | Preferred candidate because both positive and negative labels come from a defined experimental assay. Its different biological setting and fragment lengths are explicit limits. Independence still needs certification. |
| Historical test / its deduplicated remainder | Historical diagnostic only; reuse, original parameter exposure, altered positive composition and broader overlap concerns remain. |
| Previously examined grouped folds | Reconstruction diagnostics, not fresh confirmation. |
| Local ENCODE4 enhancer-like BED | Candidate annotations, not experimental positives plus verified negatives. Absence from the BED is not evidence of inactivity. |
| DNABERT-Enhancer resources | The local article describes ENCODE-based 201/350-base sets with sampled negatives. A source archive or model weights do not establish a compatible, untouched evaluation set. |
| Cross-assay MPRA/STARR collection | Some lentiMPRA measurements share source lineage with the intended later study. Provenance must be traced before claiming separate evidence. |
| Matched lentiMPRA library | Reserved for the later cell-by-cell transfer study; its specificity-score normalization and overlap checks remain unresolved. |

VISTA source: [updated database paper](https://doi.org/10.1093/nar/gkae940), [official data repository](https://gitlab.com/egsb-mfgl/vista-data), and the pinned local field/backbone dictionaries. Source definitions were inspected in the already downloaded full-text article; live PMC access returned a browser-verification page. The candidate choice, tiling rule, exclusions and endpoint are **our proposed evaluation design**, not a protocol attributed to that article.

## Next concrete step

Complete the cross-assembly, near-sequence and family screens, including the lentiMPRA design reservation, and produce a final cohort manifest. Then implement and verify full-training model serialization. Only after those gates pass should the model be trained, external predictions sealed without labels, and the labels joined once for reporting.

The local readiness audit is reproducible with Python's standard library:

```sh
python3 -m unittest discover -s replication/mcse_enhancer/independent_evaluation -p 'test_*.py' -v
python3 replication/mcse_enhancer/independent_evaluation/audit_readiness.py \
  --output /tmp/mcse-independent-readiness-new
```

The output directory must not already exist. The audit rejects changed pinned inputs and never imports or trains a classifier. A source refresh or design amendment needs a new version and its own receipt; it must not silently overwrite the frozen protocol or earlier results.
