#!/usr/bin/env python3
"""Rebuild report 03's sequence/provenance checks; never train or execute notebooks.

Requires Python 3.10+, pypdf, pandas, openpyxl. Optional publisher S4 and
MCSE source downloads are supplied explicitly, not fetched by this script.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
MCSE_COMMIT = "d76c48946de9c46e0845df12c119a27b7e455444"
LOCAL_FILES = ["enhancer.cv.txt", "non.cv.txt", "enhancer.ind.txt", "non.ind.txt"]


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def fasta(path):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            rows.append({"header": line[1:], "sequence": ""})
        elif line.strip():
            if not rows:
                raise ValueError(f"Sequence before FASTA header: {path}")
            rows[-1]["sequence"] += "".join(line.split()).upper()
    assert rows and all(re.fullmatch("[ACGT]{200}", r["sequence"]) for r in rows), path
    return rows


def supplement(path, expected):
    rows, current, label = [], None, None
    for page_number, page in enumerate(PdfReader(path).pages, 1):
        for line in page.extract_text(extraction_mode="layout").splitlines():
            line = line.strip()
            if re.match(r"^\([123]\)", line):
                label = {"1": "strong", "2": "weak", "3": "non_enhancer"}[line[1]]
            if line.startswith(">"):
                current = {"header": line[1:], "label": label,
                           "page": page_number, "sequence": ""}
                rows.append(current)
            elif current is not None:
                compact = "".join(line.split())
                if re.fullmatch("[ACGTacgt]+", compact):
                    current["sequence"] += compact.upper()
    assert Counter(r["label"] for r in rows) == expected, path
    assert all(re.fullmatch("[ACGT]{200}", r["sequence"]) for r in rows), path
    assert len({r["sequence"] for r in rows}) == len(rows), path
    return rows


def canonical(sequence):
    reverse_complement = sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]
    return min(sequence, reverse_complement)


def inspect_mcse(folder, local):
    train = fasta(folder / "Dataset/train.txt")
    test = fasta(folder / "Dataset/ind.txt")
    seqs = lambda rows: [r["sequence"] for r in rows]
    result = {
        "commit": MCSE_COMMIT,
        "repository": "https://github.com/MirBilalAhmad/DNA-Enhancers",
        "snapshot_note": "Provided snapshot; file hashes identify inspected bytes. Not executed.",
        "train_records": len(train), "test_records": len(test),
        "train_sequence_order_identical_to_local": seqs(train) == seqs(local["enhancer.cv.txt"] + local["non.cv.txt"]),
        "test_sequence_order_identical_to_local": seqs(test) == seqs(local["enhancer.ind.txt"] + local["non.ind.txt"]),
        "exact_test_train_overlaps": len(set(seqs(train)) & set(seqs(test))),
        "files": {}, "notebook_syntax": {},
        "manual_code_observations": [
            {"file": "Models _Testing.ipynb", "cell_index_zero_based": 77,
             "finding": "Optuna objective returns accuracy on y_test_ind; ensemble search uses independent-test labels."},
            {"file": "Models_Training.ipynb", "cell_index_zero_based": 14,
             "finding": "RF objective creates splits in a loop but fits/scores after the loop, using its final split."},
        ],
    }
    source_paths = [".gitignore", "README.md", "Dataset/train.txt", "Dataset/ind.txt",
                    "Dataset/train_label.txt", "Dataset/ind_label.txt",
                    "Create_Feature_Descriptors.ipynb", "Models_Training.ipynb", "Models _Testing.ipynb"]
    for relative in source_paths:
        path = folder / relative
        result["files"][relative] = fingerprint(path)
        if path.suffix != ".ipynb":
            continue
        bad, skipped, checked = [], [], 0
        for index, cell in enumerate(json.loads(path.read_text())["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            if source.startswith("%%"):
                source = "\n".join(source.splitlines()[1:])
            if any(line.lstrip().startswith(("!", "%")) for line in source.splitlines()):
                skipped.append(index)
                continue
            checked += 1
            try:
                ast.parse(source)
            except SyntaxError as error:
                bad.append({"cell_index_zero_based": index, "line": error.lineno,
                            "message": error.msg})
        result["notebook_syntax"][relative] = {
            "checked_code_cells": checked, "skipped_magic_or_shell_cells": skipped,
            "errors": bad,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--el-s4", type=Path)
    parser.add_argument("--mcse-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    s1path = root / "bioinformatics_32_3_362_s1/Supp-S1.pdf"
    s1 = supplement(s1path, {"strong": 742, "weak": 742, "non_enhancer": 1484})
    by_sequence = {r["sequence"]: r for r in s1}
    local = {name: fasta(root / name) for name in LOCAL_FILES}
    evidence = {
        "review_date": "2026-10-12",
        "scope": "Original-paper data reconstruction, published S4 comparison, exact lentiMPRA insert overlap, static MCSE code review. No model fitting.",
        "inputs": {},
        "supplement_S1": {"labels": dict(Counter(r["label"] for r in s1)),
                          "unique_sequences": len(by_sequence), "length": 200},
        "local_sequence_comparisons": {},
    }
    sources = LOCAL_FILES + ["1-s2.0-S0022283623004254-main.pdf", "bioinformatics_32_3_362.pdf",
                            "bioinformatics_34_22_3835.pdf", "srep38741.pdf",
                            "bioinformatics_32_3_362_s1/Supp-S1.pdf", "bioinformatics_32_3_362_s1/Supp-S2.pdf"]
    for name in sources:
        evidence["inputs"][name] = fingerprint(root / name)
    s4_by_sequence = {}
    if args.el_s4:
        s4 = supplement(args.el_s4, {"strong": 100, "weak": 100, "non_enhancer": 200})
        s4_by_sequence = {r["sequence"]: r for r in s4}
        independent = local["enhancer.ind.txt"] + local["non.ind.txt"]
        evidence["publisher_EL_S4"] = {
            **fingerprint(args.el_s4), "doi": "https://doi.org/10.1093/bioinformatics/bty458",
            "publisher_asset": "bioinformatics_34_22_3835_s7.pdf", "records": len(s4),
            "labels": dict(Counter(r["label"] for r in s4)),
            "sequence_order_identical_to_local": [r["sequence"] for r in s4] == [r["sequence"] for r in independent],
            "overlap_with_S1": dict(Counter(r["label"] for r in s4 if r["sequence"] in by_sequence)),
        }
    mapping = []
    for filename, records in local.items():
        matches = Counter()
        for index, record in enumerate(records, 1):
            source = by_sequence.get(record["sequence"])
            test_source = s4_by_sequence.get(record["sequence"])
            matches[source["label"] if source else "not_in_S1"] += 1
            mapping.append({
                "file": filename, "row_1_based": index, "header": record["header"],
                "sequence_sha256": hashlib.sha256(record["sequence"].encode()).hexdigest(),
                "S1_label": source["label"] if source else "",
                "S1_header": source["header"] if source else "",
                "S1_page": source["page"] if source else "",
                "S4_label": test_source["label"] if test_source else "",
                "S4_page": test_source["page"] if test_source else "",
            })
        evidence["local_sequence_comparisons"][filename] = {"records": len(records), "matches": dict(matches)}
    archive = root / "NEW_2026_DATA/02_LENTIMPRA_ENCODE_2025/SUPPLEMENTARY/lentiMPRA_supplementary_tables_1-13.zip"
    with zipfile.ZipFile(archive) as z:
        member = next(n for n in z.namelist() if "Table S10 " in n)
        design = pd.read_excel(io.BytesIO(z.read(member)), header=1, keep_default_na=False)
    sequences = design.iloc[:, -1].str.upper()
    assert sequences.str.len().eq(230).all()
    inserts = sequences.str[15:-15]
    assert inserts.str.fullmatch("[ACGT]{200}").all()
    exact, canon = set(inserts), set(inserts.map(canonical))
    lenti = {"input": str(archive.relative_to(root)), **fingerprint(archive), "member": member,
             "design_records": len(design), "insert_length": 200, "comparisons": {}}
    for filename, records in local.items():
        matches = []
        for i, r in enumerate(records, 1):
            if canonical(r["sequence"]) not in canon:
                continue
            mask = inserts.map(canonical).eq(canonical(r["sequence"]))
            matches.append({"row_1_based": i, "header": r["header"], "exact": r["sequence"] in exact,
                            "S1_label": by_sequence.get(r["sequence"], {}).get("label"),
                            "constructs": design.loc[mask, ["name", "category"]].to_dict("records")})
        lenti["comparisons"][filename] = {
            "records": len(records), "exact_matches": sum(r["sequence"] in exact for r in records),
            "exact_or_reverse_complement_matches": len(matches), "matches": matches,
        }
    evidence["legacy_lentiMPRA_overlap"] = lenti
    evidence["overlap_limit"] = "Exact 200-nt sequences and reverse complements only; no near-identity or overlapping-locus analysis. S10 design overlap does not establish measurement coverage."
    if args.mcse_dir:
        evidence["MCSE_public_snapshot"] = inspect_mcse(args.mcse_dir, local)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    mapping_path = args.output.with_name(args.output.stem + "_sequence_labels.tsv")
    with mapping_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(mapping[0]), delimiter="\t",
                                lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(mapping)
    print(json.dumps({"evidence": str(args.output), "label_map": str(mapping_path),
                      "mapped_records": len(mapping), "S1_counts": evidence["supplement_S1"]["labels"],
                      "S4": evidence.get("publisher_EL_S4"), "lentiMPRA_matches": lenti["comparisons"]}, indent=2))


if __name__ == "__main__":
    main()
