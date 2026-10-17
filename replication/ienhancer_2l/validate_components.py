#!/usr/bin/env python3
"""Read-only post-run component audit; prints JSON without modifying artifacts."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from common import ROOT, load_benchmark, sha256
from features import components, combine
from compare_components import (ARMS, component_matrices, component_names,
                                contrasts_with_intervals, feature_geometry, verify_manifest)
from compare_features import REFERENCE
from train_svm import (array_hash, choose_candidate, load_inputs, portable_scores,
                       splits_for_outer, summarize_oof)


def validate(output):
    audit = json.loads((output/'component_audit.json').read_text())
    if audit['status'] != 'complete':
        raise ValueError('Run incomplete')
    verify_manifest(output,audit,'artifact_sha256')
    for name,expected in audit['input_sha256'].items():
        if sha256(ROOT/name) != expected:
            raise ValueError(f'Input changed: {name}')
    if sha256(output/'protocol_snapshot.json') != audit['protocol_sha256']:
        raise ValueError('Protocol hash mismatch')
    protocol = audit['protocol']
    seq = {r['record_id']:r['sequence'] for r in load_benchmark()}
    counts = {'model_files_checked':0,'new_outer_models':0,'inner_searches':0,
              'new_svm_fits':0,'prediction_rows':0,'raw_sequence_replay_rows':0,
              'max_score_replay_error':0.}
    with threadpool_limits(limits=1):
        for layer,data in load_inputs().items():
            part = [components(seq[r]) for r in data['ids']]
            F,theta = np.stack([p[0] for p in part]),np.stack([p[1] for p in part])
            weight = protocol['weights'][layer]
            matrices,Z = component_matrices(F,theta,weight)
            np.testing.assert_array_equal(matrices['full'], np.stack([combine(*p,weight) for p in part]))
            np.testing.assert_array_equal(matrices['full'],data['X'])
            with np.load(output/f'{layer}_components.npz',allow_pickle=False) as saved:
                for key,value in [('F',F),('theta',theta),('Z',Z),('ids',data['ids']),('y',data['y'])]:
                    np.testing.assert_array_equal(saved[key],value)
            inference = {}
            for mode in ('retuned','fixed'):
                predictions = {}
                for arm in ARMS:
                    method = arm+'__'+mode; target = output/method/layer
                    result = audit['layers'][layer]['methods'][method]
                    X = matrices[arm]
                    assert array_hash(X) == result['feature_array_sha256']
                    with (target/'held_out_predictions.csv').open(newline='') as stream:
                        rows = list(csv.DictReader(stream))
                    assert [r['record_id'] for r in rows] == list(data['ids'])
                    assert [r['group_id'] for r in rows] == list(data['groups'])
                    for key,value in [('true_label',data['y']),('outer_fold',data['outer'])]:
                        np.testing.assert_array_equal([int(r[key]) for r in rows],value)
                    pred = np.asarray([int(r['predicted_label']) for r in rows])
                    scores = np.asarray([float(r['decision_score']) for r in rows])
                    assert summarize_oof(data['y'],pred,scores,data['outer']) == result['metrics']
                    assert json.loads((target/'summary.json').read_text()) == result
                    predictions[arm] = (pred,scores)
                    counts['prediction_rows'] += len(rows)
                    for fold in range(5):
                        train,test,_ = splits_for_outer(data,fold)
                        modelpath = target/f'outer_{fold}_model.npz'
                        record = json.loads((target/f'outer_{fold}_result.json').read_text())
                        assert record == result['folds'][fold]
                        with np.load(modelpath,allow_pickle=False) as model:
                            support = list(model['support_record_ids'])
                            assert set(support) <= set(data['ids'][train])
                            index = {r:i for i,r in enumerate(data['ids'])}
                            np.testing.assert_array_equal(model['support_vectors'],X[[index[r] for r in support]])
                            assert list(model['feature_names']) == component_names(arm)
                            assert int(model['layer'].item()[-1]) == int(layer[-1])
                            for name in ('C','gamma'):
                                assert float(model[name]) == record['best'][name]
                            if result['origin'] == 'new fits':
                                assert str(model['feature_variant']) == method
                                assert str(model['protocol_sha256']) == audit['protocol_sha256']
                        replay = portable_scores(modelpath,X[test])
                        error = float(abs(replay-scores[test]).max())
                        assert error <= 1e-6
                        np.testing.assert_array_equal((replay>0).astype(int),pred[test])
                        counts['max_score_replay_error'] = max(error,counts['max_score_replay_error'])
                        counts['model_files_checked'] += 1
                        counts['raw_sequence_replay_rows'] += len(test)
                        if result['origin'] == 'new fits':
                            counts['new_outer_models'] += 1
                            counts['new_svm_fits'] += 1
                            if mode == 'retuned':
                                search = json.loads((target/f'outer_{fold}_search.json').read_text())
                                assert len(search) == 48
                                svm = json.loads((output/'source_snapshot/training_protocol.json').read_text())
                                assert {(c['C'],c['gamma']) for c in search} == {(2.**c,2.**g) for c in svm['C_exponents_base2'] for g in svm['gamma_exponents_base2']}
                                for c in search:
                                    assert len(c['iterations']) == len(c['fold_balanced_accuracy']) == 3
                                    assert min(c['iterations']) > 0
                                    assert c['mean_balanced_accuracy'] == float(np.mean(c['fold_balanced_accuracy']))
                                assert choose_candidate(search) == record['best']
                                counts['inner_searches'] += 1
                                counts['new_svm_fits'] += 48*3
                        else:
                            assert sha256(modelpath) == record['source_model_sha256'] == sha256(ROOT/record['reused_from'])
                        if mode == 'fixed':
                            best = json.loads((REFERENCE/f'{layer}_outer_{fold}_result.json').read_text())['best']
                            for name in ('C','gamma'):
                                assert record['best'][name] == best[name]
                inference[mode] = contrasts_with_intervals(data,predictions,protocol['paired_bootstrap'],protocol['contrasts'])
            assert inference == audit['layers'][layer]['inference']
            assert feature_geometry(matrices,Z,protocol['geometry']) == audit['layers'][layer]['geometry']
    assert counts['new_svm_fits'] == audit['new_svm_fits'] == 2930
    assert counts['new_outer_models'] == audit['new_outer_models'] == 50
    assert counts['model_files_checked'] == 80
    assert counts['inner_searches'] == 20
    assert counts['prediction_rows'] == counts['raw_sequence_replay_rows'] == 35616
    return {'status':'passed','artifact_hashes_checked':len(audit['artifact_sha256']),
            'input_hashes_checked':len(audit['input_sha256']),**counts,
            'paired_bootstrap_and_geometry_recomputed':True,
            'historical_test_used':False,'lentiMPRA_used':False,'full_data_model_fitted':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    print(json.dumps(validate(parser.parse_args().output.resolve()),indent=2))
