# Independent evaluation of the iEnhancer-2L reconstruction

**20 October 2026 · Local protocol defined · Cohort not verified · Evaluation not run**

Use the unchanged saved layer-I model for a future external VISTA assay evaluation, before the separate HepG2/K562/WTC11 activity comparison. VISTA does not provide the historical strong/weak labels needed to evaluate layer II.

- [Readable report](../../../reports/04_ienhancer_2l_independent_evaluation.md) and [HTML copy](../../../reports/04_ienhancer_2l_independent_evaluation.html).
- [Protocol](protocol.json): model identities, prior exposure, candidate source, exclusions, window aggregation, endpoints, uncertainty, and stop rules.
- [Readiness record](checkpoints/2026-10-20-design/readiness.json): source/model integrity verified; all cohort and execution gates remain pending.

The previous MCSE VISTA candidates remain a historical feasibility audit. They are not silently reused as an independent iEnhancer-2L test set. All legacy records, prior author-server probes, and related families must be excluded. The full S10 design library is reserved from this earlier test for the later activity comparison.

Run the local integrity audit into a new directory:

```sh
python3 -m unittest discover -s replication/ienhancer_2l/independent_evaluation -p 'test_*.py' -v
python3 replication/ienhancer_2l/independent_evaluation/audit_readiness.py --output /tmp/ienhancer-independent-readiness-new
```

The audit requires only the Python standard library, rejects missing or changed pinned inputs, and refuses an existing output directory. It reads file bytes and the historical training-audit JSON; it does not load classifiers, read new assay outcomes, train, predict, or certify cohort independence. A passing audit cannot authorize external scoring while the remaining gates are unresolved. There is no external inference runner in this planning stage.
