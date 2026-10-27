#!/usr/bin/env python3
"""Export the frozen primary SVMs for browser inference, without fitting models.

Run with the research environment: .venv/bin/python website/tools/export_predictor.py
The site build only copies the resulting files and needs no scientific packages.
"""
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse import csc_matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "replication/ienhancer_2l"))
from features import property_table
from predict_svm import DEFAULT_MODELS, validate_models

VERSION = "ienhancer-primary-2026-10-13-browser-v1"
DESTINATION = ROOT / "website/data"


def main():
    validate_models(DEFAULT_MODELS)
    data = {"version": VERSION, "properties": property_table().tolist(), "layers": []}
    sources = {}
    for layer, weight in (("layer1", 0.1), ("layer2", 0.4)):
        path = DEFAULT_MODELS / f"{layer}_final.npz"
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path, allow_pickle=False) as model:
            supports = model["support_vectors"]
            sparse = csc_matrix(supports[:, :4096])
            data["layers"].append({
                "name": layer, "weight": weight, "gamma": float(model["gamma"]),
                "intercept": float(model["intercept"]), "count": len(supports),
                "dual": model["dual_coef"].tolist(),
                "norms": np.einsum("ij,ij->i", supports, supports).tolist(),
                "columnOffsets": sparse.indptr.tolist(), "rowIndices": sparse.indices.tolist(),
                "values": sparse.data.tolist(), "structure": supports[:, 4096:].ravel().tolist(),
            })
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False).encode()
    compressed = gzip.compress(payload, mtime=0)
    name = f"{VERSION}.json.gz"
    (DESTINATION / name).write_bytes(compressed)
    manifest = {
        "version": VERSION, "file": name, "sha256": hashlib.sha256(compressed).hexdigest(),
        "bytes": len(compressed), "source_models": sources,
        "feature_settings": {"bases": 200, "k": 6, "lag": 9, "counting": "overlapping",
                             "property_normalization": "sample standard deviation (ddof=1)",
                             "weights": [0.1, 0.4], "features": 4105},
        "decision_rule": "score > 0; evaluate strength only for a positive layer-I score",
        "score_kind": "Uncalibrated SVM decision value, not probability or measured activity",
        "model_training_date": "2026-10-13", "exporter": "website/tools/export_predictor.py",
    }
    (DESTINATION / "predictor_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Exported {len(compressed):,} bytes; support vectors: {[x['count'] for x in data['layers']]}")


if __name__ == "__main__":
    main()
