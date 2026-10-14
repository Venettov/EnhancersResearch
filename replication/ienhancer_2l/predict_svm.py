#!/usr/bin/env python3
"""Apply the saved two-layer reconstruction to 200-base A/C/G/T FASTA records.

Scores are uncalibrated SVM decision values, not probabilities or experimental
enhancer activity. Layer II is used only for layer-I-positive sequences.
"""
import argparse
from pathlib import Path
import numpy as np
from common import HERE, digest, write_csv
from features import components, combine, feature_names
from prepare_data import fasta
from train_svm import portable_scores

DEFAULT_MODELS = HERE / 'checkpoints/2026-10-13-svm-training/models'


def validate_models(models):
    hashes = []
    for layer in ('layer1', 'layer2'):
        path = models / f'{layer}_final.npz'
        with np.load(path, allow_pickle=False) as model:
            if (str(model['layer']) != layer or str(model['feature_variant']) != 'primary'
                    or list(model['feature_names']) != feature_names()
                    or not np.array_equal(model['classes'], [0, 1])
                    or model['support_vectors'].shape[1] != 4105):
                raise ValueError('Model metadata does not match the primary two-layer reconstruction')
            hashes.append(str(model['protocol_sha256']))
    if len(set(hashes)) != 1:
        raise ValueError('The two models were built under different protocols')


def predict_records(records, models=DEFAULT_MODELS):
    validate_models(Path(models))
    if not records:
        raise ValueError('FASTA contains no records')
    for _, sequence in records:
        if len(sequence) != 200 or set(sequence) - set('ACGT'):
            raise ValueError('Every input must contain exactly 200 A/C/G/T bases')
    output = []
    for start in range(0, len(records), 128):
        batch = records[start:start+128]
        pieces = [components(sequence) for _, sequence in batch]
        X1 = np.asarray([combine(f, theta, 0.1) for f, theta in pieces])
        scores1 = portable_scores(Path(models) / 'layer1_final.npz', X1)
        positive = np.flatnonzero(scores1 > 0)
        scores2 = {}
        if len(positive):
            X2 = np.asarray([combine(*pieces[i], 0.4) for i in positive])
            values = portable_scores(Path(models) / 'layer2_final.npz', X2)
            scores2 = dict(zip(positive, values))
        for i, (header, sequence) in enumerate(batch):
            output.append({'row_1_based':start+i+1, 'header':header, 'sequence_sha256':digest(sequence),
                           'predicted_class': ('strong' if scores2[i] > 0 else 'weak') if i in scores2 else 'non-enhancer',
                           'enhancer_decision_score':float(scores1[i]),
                           'strength_decision_score':float(scores2[i]) if i in scores2 else ''})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fasta', type=Path, required=True)
    parser.add_argument('--models', type=Path, default=DEFAULT_MODELS)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output filename to preserve prior predictions')
    results = predict_records(fasta(args.fasta), args.models)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, results)
    print(f'Saved {len(results)} sequence predictions; these are not experimental activity measurements.')


if __name__ == '__main__':
    main()
