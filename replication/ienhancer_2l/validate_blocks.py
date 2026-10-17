#!/usr/bin/env python3
"""Read-only independent audit of train-only block-balanced models."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances, rbf_kernel
from threadpoolctl import threadpool_limits
from common import ROOT, load_benchmark, sha256
from features import components, combine
from compare_components import ARMS, component_matrices, component_names, contrasts_with_intervals, verify_manifest
from compare_blocks import NEW_ARMS, block_scores
from train_svm import array_hash, load_inputs, metrics, portable_scores, splits_for_outer, summarize_oof


def verify_scale(X,train,scale,split):
    # Different route from the runner: q=2*sum of SAMPLE column variances.
    q=np.array([2*np.var(b[train],axis=0,ddof=1).sum() for b in (X[:,:split],X[:,split:])])
    np.testing.assert_allclose(q,scale['block_mean_squared_distances'],rtol=1e-10,atol=1e-14)
    scaled=np.concatenate((X[train,:split]/np.sqrt(q[0]),X[train,split:]/np.sqrt(q[1])),axis=1)
    D=euclidean_distances(scaled,squared=True);np.fill_diagonal(D,0)
    np.testing.assert_allclose(float(np.median(D[np.triu_indices(len(train),1)])),scale['balanced_median_squared_distance'],rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose(scale['unbalanced_distance_shares'],q/q.sum(),rtol=1e-10,atol=1e-14)
    sums=[]
    for block in (scaled[:,:split],scaled[:,split:]):
        db=euclidean_distances(block,squared=True);sums.append(float(db[np.triu_indices(len(train),1)].sum()))
    np.testing.assert_allclose(np.array(sums)/sum(sums),[.5,.5],rtol=0,atol=1e-10)
    np.testing.assert_allclose(scale['balanced_distance_shares'],[.5,.5],rtol=0,atol=1e-12)


def validate(out):
    audit=json.loads((out/'block_audit.json').read_text());assert audit['status']=='complete' and not audit['full_data_model_fitted']
    verify_manifest(out,audit,'artifact_sha256')
    for name,h in audit['input_sha256'].items(): assert sha256(ROOT/name)==h,name
    for name,h in audit['source_sha256'].items(): assert sha256(out/'source_snapshot'/name)==h,name
    assert sha256(out/'protocol_snapshot.json')==audit['protocol_sha256']
    protocol=json.loads((out/'protocol_snapshot.json').read_text());assert protocol==audit['protocol'];split=protocol['block_boundary']
    seq={r['record_id']:r['sequence'] for r in load_benchmark()}
    counts={'model_files_checked':0,'new_outer_models':0,'new_svm_fits':0,'inner_searches':0,
            'train_only_scaler_fits_recomputed':0,'block_means_recomputed':0,'balanced_medians_recomputed':0,
            'prediction_rows':0,'raw_sequence_replay_rows':0,'max_score_replay_error':0.,'max_direct_kernel_replay_error':0.}
    with threadpool_limits(limits=4):
        for layer,data in load_inputs().items():
            part=[components(seq[r]) for r in data['ids']];F,theta=np.stack([p[0] for p in part]),np.stack([p[1] for p in part])
            matrices,Z=component_matrices(F,theta,protocol['weights'][layer])
            np.testing.assert_array_equal(matrices['full'],np.stack([combine(*p,protocol['weights'][layer]) for p in part]))
            np.testing.assert_array_equal(matrices['full'],data['X'])
            with np.load(out/f'{layer}_components.npz',allow_pickle=False) as saved:
                for key,val in [('F',F),('theta',theta),('Z',Z),('ids',data['ids']),('y',data['y'])]: np.testing.assert_array_equal(saved[key],val)
            predictions={}
            for arm in (*ARMS,*NEW_ARMS):
                raw=NEW_ARMS.get(arm,arm);X=matrices[raw];target=out/arm/layer;result=audit['layers'][layer]['methods'][arm]
                assert array_hash(X)==result['feature_array_sha256']
                assert json.loads((target/'summary.json').read_text())==result
                with (target/'held_out_predictions.csv').open(newline='') as f: rows=list(csv.DictReader(f))
                assert [r['record_id'] for r in rows]==list(data['ids']) and [r['group_id'] for r in rows]==list(data['groups'])
                for key,val in [('true_label',data['y']),('outer_fold',data['outer'])]: np.testing.assert_array_equal([int(r[key]) for r in rows],val)
                pred=np.array([int(r['predicted_label']) for r in rows]);score=np.array([float(r['decision_score']) for r in rows])
                assert summarize_oof(data['y'],pred,score,data['outer'])==result['metrics']
                predictions[arm]=(pred,score);counts['prediction_rows']+=len(rows)
                for fold in range(5):
                    train,test,splits=splits_for_outer(data,fold);path=target/f'outer_{fold}_model.npz'
                    with np.load(path,allow_pickle=False) as model:
                        ids=list(model['support_record_ids']);assert set(ids)<=set(data['ids'][train])
                        index={r:i for i,r in enumerate(data['ids'])};np.testing.assert_array_equal(model['support_vectors'],X[[index[r] for r in ids]])
                        assert list(model['feature_names'])==component_names(raw) and str(model['layer'])==layer
                        if arm in NEW_ARMS:
                            rec=json.loads((target/f'outer_{fold}_result.json').read_text());assert rec==result['folds'][fold]
                            assert rec['metrics']==metrics(data['y'][test],pred[test],score[test])
                            receipt=json.loads((target/f'outer_{fold}_scales.json').read_text())
                            expected_scales=[rec['outer_scale'],*rec['inner_scales']]
                            receipts=[receipt['outer'],*receipt['inner']]
                            for indices,s,r in zip([train,*[tr for tr,_ in splits]],expected_scales,receipts):
                                assert r['training_ids']==list(data['ids'][indices])
                                assert all(r[k]==v for k,v in s.items())
                                verify_scale(X,indices,s,split)
                                counts['train_only_scaler_fits_recomputed']+=1;counts['block_means_recomputed']+=2;counts['balanced_medians_recomputed']+=1
                            search=json.loads((target/f'outer_{fold}_search.json').read_text())
                            assert len(search)==90 and {(c['C'],c['alpha']) for c in search}=={(2.**c,2.**g) for c in protocol['C_exponents_base2'] for g in protocol['alpha_exponents_base2']}
                            for c in search:
                                assert len(c['iterations'])==len(c['fold_balanced_accuracy'])==3 and min(c['iterations'])>0
                                assert all(0<=v<=1 for v in c['fold_balanced_accuracy'])
                                assert c['mean_balanced_accuracy']==float(np.mean(c['fold_balanced_accuracy']))
                                assert c['inner_block_gammas']==[[c['alpha']/(s['balanced_median_squared_distance']*q) for q in s['block_mean_squared_distances']] for s in rec['inner_scales']]
                            best=sorted(search,key=lambda c:(-c['mean_balanced_accuracy'],c['C'],c['alpha']))[0];assert best==rec['best']
                            assert float(model['C'])==best['C'] and float(model['alpha'])==best['alpha']
                            assert str(model['feature_variant'])==arm and str(model['protocol_sha256'])==audit['protocol_sha256'] and str(model['kernel_format'])=='block_rbf_v1'
                            assert int(model['block_boundary'])==split
                            q=model['block_mean_squared_distances'];m=float(model['balanced_median_squared_distance'])
                            np.testing.assert_array_equal(q,rec['outer_scale']['block_mean_squared_distances']);assert m==rec['outer_scale']['balanced_median_squared_distance']
                            assert float(model['gamma'])==best['alpha']/m
                            np.testing.assert_array_equal(model['block_gammas'],best['alpha']/(m*q));np.testing.assert_array_equal(model['block_gammas'],rec['block_gammas'])
                            expected={k:best[k] in (2.**min(protocol[e]),2.**max(protocol[e])) for k,e in [('C','C_exponents_base2'),('alpha','alpha_exponents_base2')]};assert expected==rec['grid_boundary']
                            multiplier=np.concatenate((np.full(split,1/np.sqrt(q[0])),np.full(X.shape[1]-split,1/np.sqrt(q[1]))))
                            # Independent feature-space kernel, compared with block-distance replay.
                            direct=rbf_kernel(X[test]*multiplier,model['support_vectors']*multiplier,gamma=best['alpha']/m)@model['dual_coef']+float(model['intercept'])
                            error=float(abs(direct-score[test]).max());assert error<=1e-6
                            np.testing.assert_array_equal((direct>0).astype(int),pred[test])
                            counts['max_direct_kernel_replay_error']=max(counts['max_direct_kernel_replay_error'],error)
                            counts['new_outer_models']+=1;counts['inner_searches']+=1;counts['new_svm_fits']+=271
                        else:
                            ref=result['model_references'][fold];assert sha256(path)==ref['sha256']==sha256(ROOT/ref['path'])
                    replay=(block_scores if arm in NEW_ARMS else portable_scores)(path,X[test]);error=float(abs(replay-score[test]).max());assert error<=1e-6
                    np.testing.assert_array_equal((replay>0).astype(int),pred[test])
                    counts['max_score_replay_error']=max(counts['max_score_replay_error'],error);counts['model_files_checked']+=1;counts['raw_sequence_replay_rows']+=len(test)
                if arm in NEW_ARMS: assert result['boundary_folds']==[r['outer_fold'] for r in result['folds'] if any(r['grid_boundary'].values())]
            assert contrasts_with_intervals(data,predictions,protocol['paired_bootstrap'],protocol['contrasts'])==audit['layers'][layer]['inference']
    assert counts['new_svm_fits']==audit['new_svm_fits']==5420 and counts['new_outer_models']==audit['new_outer_models']==20
    assert counts['model_files_checked']==60 and counts['inner_searches']==20
    assert counts['train_only_scaler_fits_recomputed']==counts['balanced_medians_recomputed']==80 and counts['block_means_recomputed']==160
    assert counts['prediction_rows']==counts['raw_sequence_replay_rows']==26712
    return {'status':'passed','artifact_hashes_checked':len(audit['artifact_sha256']),'input_hashes_checked':len(audit['input_sha256']),
            'source_snapshots_checked':len(audit['source_sha256']),**counts,'independent_variance_scale_check':True,
            'aggregate_training_block_balance_verified':True,'paired_bootstrap_recomputed':True,
            'historical_test_used':False,'lentiMPRA_used':False,'full_data_model_fitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    print(json.dumps(validate(parser.parse_args().output.resolve()),indent=2))
