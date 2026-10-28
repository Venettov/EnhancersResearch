#!/usr/bin/env python3
"""Verify a local evaluation design and its inputs; never score or train a model."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def audit(protocol, root=ROOT):
    if protocol['protocol_id'] != 'ienhancer-2l-independent-vista-v1':
        raise ValueError('Unexpected protocol identity')
    verified = {}
    for name, expected in protocol['input_sha256'].items():
        path = root / name
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f'Missing or changed pinned input: {name}')
        verified[name] = expected
    training = json.loads((root / protocol['primary_model']['training_audit']).read_text())
    for layer, model in protocol['primary_model']['artifacts'].items():
        if model['sha256'] != training['artifact_sha256'][f'models/{layer}_final.npz']:
            raise ValueError(f'Model pin differs from historical training audit: {layer}')
        if digest(root / model['path']) != model['sha256']:
            raise ValueError(f'Historical model changed: {layer}')
    gates = {name: 'pending' for name in protocol['gates_before_external_scoring']}
    gates['source_integrity'] = 'passed_pinned_files_only'
    gates['frozen_primary_model'] = 'passed_both_saved_models_match_training_audit'
    return {
        'protocol_id': protocol['protocol_id'],
        'audit_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'design_defined_external_cohort_not_verified_evaluation_not_run',
        'verified_input_sha256': verified,
        'model_hashes_verified_against_training_audit': {
            k: v['sha256'] for k, v in protocol['primary_model']['artifacts'].items()},
        'gates': gates,
        'independence_verified': False,
        'scoring_allowed': False,
        'final_fragments': None,
        'independent_components': None,
        'external_predictions': 0,
        'model_fits': 0,
        'external_metrics': None,
        'new_assay_outcomes_read': False,
        'prior_vista_audit': {
            'status': 'historical_metadata_and_exact_match_screen_only_not_recertified',
            'record': protocol['prior_information']['archived_vista_audit'],
            'counts': protocol['prior_information']['archived_vista_counts'],
        },
        'next_action': 'Complete reference, exclusion, family, lineage and reserve gates; freeze a new iEnhancer-2L cohort before predictions.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=HERE / 'protocol.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output directory to preserve earlier audits')
    raw = args.protocol.read_bytes()
    protocol = json.loads(raw)
    result = audit(protocol)
    result['protocol_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'protocol.json').write_bytes(raw)
    readiness = args.output / 'readiness.json'
    readiness.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    manifest = {'protocol_id': protocol['protocol_id'], 'files_sha256': {
        'protocol.json': digest(args.output / 'protocol.json'),
        'readiness.json': digest(readiness),
    }}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Verified source/model pins. External cohort is NOT verified; no predictions or fits performed.')


if __name__ == '__main__':
    main()
