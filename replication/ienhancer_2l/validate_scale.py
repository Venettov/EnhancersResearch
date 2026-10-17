#!/usr/bin/env python3
"""Read-only scale-aware audit, including independent train-only scale checks."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist
from sklearn.metrics.pairwise import euclidean_distances
from threadpoolctl import threadpool_limits
from common import ROOT, load_benchmark, sha256
from features import components, combine
from compare_components import ARMS, component_matrices, component_names, contrasts_with_intervals, verify_manifest
from train_svm import array_hash, load_inputs, metrics, portable_scores, splits_for_outer, summarize_oof


def independent_median(X,indices):
    # Fresh training-only matrix, separate from the runner's whole-data cache.
    D=euclidean_distances(X[indices],squared=True)
    values=D[np.triu_indices(len(indices),1)]
    median=float(np.quantile(values,.5))
    assert median>0 and np.isfinite(median)
    # Independent direct-coordinate distance implementation on a deterministic subset.
    n=min(20,len(indices)); expected=pdist(X[indices[:n]],'sqeuclidean')
    np.testing.assert_allclose(D[:n,:n][np.triu_indices(n,1)],expected,atol=1e-12,rtol=1e-10)
    return median


def validate(output):
    audit=json.loads((output/'scale_audit.json').read_text())
    assert audit['status']=='complete' and not audit['full_data_model_fitted']
    verify_manifest(output,audit,'artifact_sha256')
    for path,h in audit['input_sha256'].items(): assert sha256(ROOT/path)==h,path
    for name,h in audit['source_sha256'].items(): assert sha256(output/'source_snapshot'/name)==h,name
    assert sha256(output/'protocol_snapshot.json')==audit['protocol_sha256']
    protocol=json.loads((output/'protocol_snapshot.json').read_text());assert protocol==audit['protocol']
    seq={r['record_id']:r['sequence'] for r in load_benchmark()}
    counts={'model_files_checked':0,'new_outer_models':0,'inner_searches':0,'new_svm_fits':0,
            'training_medians_recomputed':0,'prediction_rows':0,'raw_sequence_replay_rows':0,'max_score_replay_error':0.}
    with threadpool_limits(limits=4):
        for layer,data in load_inputs().items():
            part=[components(seq[r]) for r in data['ids']]
            F,theta=np.stack([p[0] for p in part]),np.stack([p[1] for p in part])
            matrices,Z=component_matrices(F,theta,protocol['weights'][layer])
            np.testing.assert_array_equal(matrices['full'],np.stack([combine(*p,protocol['weights'][layer]) for p in part]))
            np.testing.assert_array_equal(matrices['full'],data['X'])
            with np.load(output/f'{layer}_components.npz',allow_pickle=False) as saved:
                for key,value in [('F',F),('theta',theta),('Z',Z),('ids',data['ids']),('y',data['y'])]:
                    np.testing.assert_array_equal(saved[key],value)
            predictions={}
            for arm in ARMS:
                X=matrices[arm]
                for prefix in ('','previous_'):
                    method=prefix+arm;target=output/method/layer
                    result=audit['layers'][layer]['methods'][method]
                    assert array_hash(X)==result['feature_array_sha256']
                    assert json.loads((target/'summary.json').read_text())==result
                    with (target/'held_out_predictions.csv').open(newline='') as stream: rows=list(csv.DictReader(stream))
                    assert [r['record_id'] for r in rows]==list(data['ids'])
                    assert [r['group_id'] for r in rows]==list(data['groups'])
                    for key,value in [('true_label',data['y']),('outer_fold',data['outer'])]:
                        np.testing.assert_array_equal([int(r[key]) for r in rows],value)
                    pred=np.array([int(r['predicted_label']) for r in rows]);score=np.array([float(r['decision_score']) for r in rows])
                    assert summarize_oof(data['y'],pred,score,data['outer'])==result['metrics']
                    predictions[method]=(pred,score);counts['prediction_rows']+=len(rows)
                    for fold in range(5):
                        train,test,splits=splits_for_outer(data,fold)
                        path=target/f'outer_{fold}_model.npz'
                        with np.load(path,allow_pickle=False) as model:
                            support=list(model['support_record_ids']);assert set(support)<=set(data['ids'][train])
                            index={r:i for i,r in enumerate(data['ids'])}
                            np.testing.assert_array_equal(model['support_vectors'],X[[index[r] for r in support]])
                            assert list(model['feature_names'])==component_names(arm)
                            assert str(model['layer'])==layer
                            if not prefix:
                                record=json.loads((target/f'outer_{fold}_result.json').read_text())
                                assert record==result['folds'][fold]
                                assert record['metrics']==metrics(data['y'][test],pred[test],score[test])
                                scales=json.loads((target/f'outer_{fold}_scale.json').read_text())
                                assert scales['outer_training_ids']==list(data['ids'][train])
                                median=independent_median(X,train)
                                np.testing.assert_allclose(median,scales['outer_median_squared_distance'],rtol=1e-10,atol=1e-14)
                                assert scales['outer_median_squared_distance']==record['outer_median_squared_distance']==float(model['training_median_squared_distance'])
                                counts['training_medians_recomputed']+=1
                                inner=[]
                                for i,(tr,_) in enumerate(splits):
                                    s=scales['inner'][i];assert s['fold']==i and s['training_ids']==list(data['ids'][tr])
                                    np.testing.assert_allclose(independent_median(X,tr),s['median_squared_distance'],rtol=1e-10,atol=1e-14)
                                    inner.append(s['median_squared_distance']);counts['training_medians_recomputed']+=1
                                assert inner==record['inner_median_squared_distances']
                                search=json.loads((target/f'outer_{fold}_search.json').read_text())
                                assert len(search)==90 and {(c['C'],c['alpha']) for c in search}=={(2.**c,2.**a) for c in protocol['C_exponents_base2'] for a in protocol['alpha_exponents_base2']}
                                for c in search:
                                    assert len(c['iterations'])==len(c['fold_balanced_accuracy'])==3 and min(c['iterations'])>0
                                    assert all(0<=s<=1 for s in c['fold_balanced_accuracy'])
                                    assert c['mean_balanced_accuracy']==float(np.mean(c['fold_balanced_accuracy']))
                                    assert c['inner_effective_gamma']==[c['alpha']/s for s in inner]
                                best=sorted(search,key=lambda c:(-c['mean_balanced_accuracy'],c['C'],c['alpha']))[0]
                                assert best==record['best']
                                assert float(model['C'])==best['C'] and float(model['alpha'])==best['alpha']
                                assert float(model['gamma'])==record['outer_effective_gamma']==best['alpha']/scales['outer_median_squared_distance']
                                assert str(model['feature_variant'])==arm and str(model['protocol_sha256'])==audit['protocol_sha256']
                                expected={k:best[k] in (2.**min(protocol[e]),2.**max(protocol[e])) for k,e in [('C','C_exponents_base2'),('alpha','alpha_exponents_base2')]}
                                assert expected==record['grid_boundary']
                                counts['inner_searches']+=1;counts['new_svm_fits']+=271;counts['new_outer_models']+=1
                            else:
                                ref=result['model_references'][fold]
                                assert sha256(path)==ref['sha256']==sha256(ROOT/ref['path'])
                        replay=portable_scores(path,X[test]);error=float(abs(replay-score[test]).max())
                        assert error<=1e-6
                        np.testing.assert_array_equal((replay>0).astype(int),pred[test])
                        counts['max_score_replay_error']=max(counts['max_score_replay_error'],error)
                        counts['model_files_checked']+=1;counts['raw_sequence_replay_rows']+=len(test)
                    if not prefix:
                        assert result['boundary_folds']==[r['outer_fold'] for r in result['folds'] if any(r['grid_boundary'].values())]
            assert contrasts_with_intervals(data,predictions,protocol['paired_bootstrap'],protocol['contrasts'])==audit['layers'][layer]['inference']
    assert counts['new_svm_fits']==audit['new_svm_fits']==10840
    assert counts['new_outer_models']==audit['new_outer_models']==40
    assert counts['model_files_checked']==80 and counts['inner_searches']==40 and counts['training_medians_recomputed']==160
    assert counts['prediction_rows']==counts['raw_sequence_replay_rows']==35616
    return {'status':'passed','artifact_hashes_checked':len(audit['artifact_sha256']),
            'input_hashes_checked':len(audit['input_sha256']),'source_snapshots_checked':len(audit['source_sha256']),**counts,
            'paired_bootstrap_recomputed':True,'training_only_distance_medians_recomputed':True,
            'historical_test_used':False,'lentiMPRA_used':False,'full_data_model_fitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    print(json.dumps(validate(parser.parse_args().output.resolve()),indent=2))
