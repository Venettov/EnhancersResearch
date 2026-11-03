#!/usr/bin/env python3
"""Join only the 200 previously exposed probes to published S10/S11 data.

Standard-library only. Run from any directory; the original supplementary ZIP
must be present locally. No downloads, fitting, fresh cohort selection or ESS
reconstruction. Writes deterministic public JSON/CSV with source hashes.
"""
import csv
import hashlib
import io
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "website/data"
SOURCE = ROOT / "NEW_2026_DATA/02_LENTIMPRA_ENCODE_2025/SUPPLEMENTARY/lentiMPRA_supplementary_tables_1-13.zip"
CELLS = ("HepG2", "K562", "WTC11")
ENCODE = {"HepG2": "ENCSR405QCT/ENCFF009HVM.tsv", "K562": "ENCSR203UFY/ENCFF068BWG.tsv", "WTC11": "ENCSR336MKI/ENCFF357GSY.tsv"}
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def selected_rows(book, sheet, names, name_column):
    """Read sparse XLSX cells without shifting blank cells; retain sheet rows."""
    with zipfile.ZipFile(io.BytesIO(book)) as z:
        strings = ["".join(t.text or "" for t in s.iter(f"{{{NS['x']}}}t"))
                   for s in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        for _, row in ET.iterparse(z.open(f"xl/worksheets/sheet{sheet}.xml"), events=("end",)):
            if row.tag != f"{{{NS['x']}}}row":
                continue
            values = {}
            for cell in row:
                value = cell.find("x:v", NS)
                if value is None:
                    continue
                values[re.sub(r"\d", "", cell.get("r"))] = strings[int(value.text)] if cell.get("t") == "s" else value.text
            if values.get(name_column) in names:
                yield int(row.get("r")), values
            row.clear()


def ranks(values):
    ordered = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and values[ordered[j]] == values[ordered[i]]:
            j += 1
        for k in ordered[i:j]:
            result[k] = (i + 1 + j) / 2
        i = j
    return result


def spearman(x, y):
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return statistics.correlation(ranks(x), ranks(y))


def main():
    screening_path = DATA / "ienhancer_2l_server_200_screening.csv"
    reference_path = DATA / "predictor_reference_200.json"
    fasta_path = DATA / "ienhancer_2l_server_200_queries.fasta"
    probes = list(csv.DictReader(io.StringIO(screening_path.read_text())))
    reference = {r["probe_id"]: r for r in json.loads(reference_path.read_text())}
    fasta = {r.splitlines()[0]: "".join(r.splitlines()[1:]) for r in fasta_path.read_text().split(">")[1:]}
    names = {r["construct"] for r in probes}
    assert len(probes) == len(names) == len(reference) == len(fasta) == 200
    with zipfile.ZipFile(SOURCE) as z:
        members = {n: next(p for p in z.namelist() if f"Table S{n} " in p) for n in (10, 11)}
        books = {n: z.read(p) for n, p in members.items()}
    design = {}
    for row, v in selected_rows(books[10], 1, names, "A"):
        assert v["A"] not in design
        design[v["A"]] = (row, v)
    summary = {}
    for row, v in selected_rows(books[11], 1, names, "A"):
        assert v["A"] not in summary
        summary[v["A"]] = (row, v)
    replicate_data = {c: {} for c in CELLS}
    per_cell = {c: {} for c in CELLS}
    for cell, sheet in zip(CELLS, (3, 5, 7)):
        for row, v in selected_rows(books[11], sheet, names, "B"):
            rep = int(v["A"])
            records = replicate_data[cell].setdefault(v["B"], {})
            assert rep not in records and rep in (1, 2, 3)
            records[rep] = {"replicate": rep, "log2_rna_dna": float(v["F"]), "barcodes": int(v["G"]), "s11_row": row}
        for row, v in selected_rows(books[11], sheet + 1, names, "A"):
            assert v["A"] not in per_cell[cell]
            per_cell[cell][v["A"]] = (row, float(v["E"]))
    encode_paths = []
    checked_replicates = {}
    for cell, relative in ENCODE.items():
        path = SOURCE.parent.parent / relative
        encode_paths.append(path)
        seen = set()
        with path.open() as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r["name"] not in names:
                    continue
                key = (r["name"], int(r["replicate"]))
                assert r["condition"] == cell and key not in seen
                seen.add(key)
                original = replicate_data[cell][key[0]][key[1]]
                assert int(r["n_obs_bc"]) == original["barcodes"]
                assert abs(float(r["log2"]) - original["log2_rna_dna"]) < 1e-12
        expected = {(name, rep) for name, reps in replicate_data[cell].items() for rep in reps}
        assert seen == expected
        checked_replicates[cell] = len(seen)
    records = []
    for p in probes:
        name, probe = p["construct"], p["probe_id"]
        row, d = design[name]
        seq = d["K"]
        assert row == int(p["sheet_row"]) and d["B"] == p["category"]
        assert len(seq) == 230 and seq.startswith("AGGACCGGATCAACT") and seq.endswith("CATTGCGTGAACCGA")
        insert = seq[15:-15]
        assert insert == p["sequence"] == fasta[probe]
        digest = sha(insert.encode())
        assert digest == p["sequence_sha256"] == reference[probe]["sequence_sha256"]
        srow, values = summary.get(name, (None, {}))
        activities = {}
        for cell, column in zip(CELLS, "BCD"):
            value = values.get(column)
            mean = None if value in (None, "NA", "NaN", "") else float(value)
            reps = sorted(replicate_data[cell].get(name, {}).values(), key=lambda r: r["replicate"])
            if mean is not None:
                assert math.isfinite(mean) and mean == per_cell[cell][name][1]
                assert reps and abs(mean - statistics.mean(r["log2_rna_dna"] for r in reps)) <= 0.000500001
            activities[cell] = {"mean_log2_rna_dna": mean, "replicates": reps,
                                "coverage_pass": any(r["barcodes"] >= 10 for r in reps)}
        eligible = all(a["mean_log2_rna_dna"] is not None and a["coverage_pass"] for a in activities.values())
        ref = reference[probe]
        records.append({"probe_id": probe, "construct": name, "category": p["category"],
                        "sequence_sha256": digest, "s10_row": row, "s11_summary_row": srow,
                        "layer1_score": float(ref["local_enhancer_score"]), "predicted_class": ref["local_class"],
                        "eligible": eligible, "activity": activities})
    eligible = [r for r in records if r["eligible"]]
    manifest = json.loads((DATA / "predictor_manifest.json").read_text())
    payload = {
        "schema_version": 1, "date": "2026-11-02", "status": "exploratory_previously_exposed_200",
        "doi": "10.1038/s41586-024-08430-9", "cells": list(CELLS),
        "model_version": manifest["version"], "model_sha256": manifest["sha256"],
        "activity_source": "Table S11, all_cell_types_summary; published mean log2(RNA/DNA), retained at published precision",
        "join_rule": "Exact construct name; S10 positions 16–215 verified against original FASTA, screening CSV and saved prediction SHA-256. No name aliases or reverse-complement pooling.",
        "coverage_rule": "At least one replicate with >=10 observed barcodes in each cell, plus finite published means in all three cells. All 200 records remain in the download; only eligible records enter plots and correlations.",
        "correlation_rule": "Descriptive Spearman correlation of saved Layer-I decision score versus published mean in each cell, using the same eligible records; average ranks for ties. No p-values, tuning, significance claim or independent performance estimate.",
        "limitations": ["Previously exposed server-comparison probes, selected from the joint library with hg19 and historical screening constraints; not representative or independent validation.",
                       "Historical strong/weak/non-enhancer classes are not measured lentiMPRA activity labels. No active/inactive cutoff is applied to log2(RNA/DNA).",
                       "One fixed sequence score across cells; no cell-specific predictor, native target-gene inference or ESS reproduction.",
                       "Fresh cohort verification and the separate independent evaluation remain pending."],
        "counts": {"selected": len(records), "matched_design": len(design), "matched_summary": len(summary),
                   "eligible": len(eligible), "excluded_from_plots": len(records) - len(eligible),
                   "categories": dict(Counter(r["category"] for r in records))},
        "replicate_crosscheck": {"representation": "One combined ENCODE file per cell, never appended to its component replicate files", "matched_rows": checked_replicates, "log2_absolute_tolerance": 1e-12, "barcode_counts": "exact"},
        "summary": {c: {"n": len(eligible), "spearman_rho": spearman([r["layer1_score"] for r in eligible],
                     [r["activity"][c]["mean_log2_rna_dna"] for r in eligible])} for c in CELLS},
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes())} for p in (SOURCE, screening_path, reference_path, fasta_path, *encode_paths)],
        "workbooks": [{"member": members[n], "sha256": sha(books[n])} for n in (10, 11)],
        "records": records}
    (DATA / "lentimpra_demo_200.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    columns = ["probe_id", "construct", "category", "sequence_sha256", "s10_row", "s11_summary_row", "layer1_score", "predicted_class", "eligible"]
    columns += [f"{c}_{metric}" for c in CELLS for metric in ("mean_log2_rna_dna", "replicates_present", "replicates_ge10_barcodes")]
    with (DATA / "lentimpra_demo_200.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for r in records:
            flat = {k: r[k] for k in columns if k in r}
            for c in CELLS:
                a = r["activity"][c]
                flat.update({f"{c}_mean_log2_rna_dna": a["mean_log2_rna_dna"],
                             f"{c}_replicates_present": len(a["replicates"]),
                             f"{c}_replicates_ge10_barcodes": sum(x["barcodes"] >= 10 for x in a["replicates"])})
            writer.writerow(flat)
    print(json.dumps({"counts": payload["counts"], "summary": payload["summary"]}, indent=2))


if __name__ == "__main__":
    main()
