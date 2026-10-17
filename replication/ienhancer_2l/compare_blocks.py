#!/usr/bin/env python3
"""Train-only equal-average-distance balance of DNA word and structural blocks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import numpy as np
from sklearn.metrics import balanced_accuracy_score
from sklearn.metrics.pairwise import euclidean_distances
from threadpoolctl import threadpool_limits
from common import HERE, ROOT, PREPARED, load_benchmark, sha256, write_csv, write_json
from features import components
from compare_components import ARMS, LABELS, component_matrices, component_names, contrasts_with_intervals, verify_manifest
from compare_features import save_predictions
from compare_scale import choose_scaled, boundary
from train_svm import DEFAULT_FEATURES, FEATURE_CHECKPOINT, array_hash, assert_split, checked_fit, load_inputs, metrics, portable_scores, splits_for_outer, summarize_oof, svc

PROTOCOL=HERE/'block_protocol.json'
NEW_ARMS={'balanced_words_structure':'words_structure','balanced_full':'full'}
NAMES={**LABELS,'balanced_words_structure':'Words + summaries, balanced blocks','balanced_full':'Full PseKNC, balanced blocks'}


def fit_block_scales(distances,train):
    """Fit q per block and m after balancing using only the supplied train rows."""
    train=np.asarray(train)
    if (not distances or train.ndim!=1 or train.dtype.kind not in 'iu' or len(train)<2 or
            len(np.unique(train))!=len(train) or (train<0).any()):
        raise ValueError('Invalid blocks or training indices')
    values=[];means=[]
    for D in distances:
        if D.ndim!=2 or D.shape[0]!=D.shape[1] or D.shape!=distances[0].shape or (train>=len(D)).any():
            raise ValueError('Invalid block distance matrix')
        v=D[np.ix_(train,train)][np.triu_indices(len(train),1)]
        if not np.isfinite(v).all() or (v<0).any(): raise ValueError('Invalid training distances')
        q=float(np.mean(v))
        if not np.isfinite(q) or q<=0: raise ValueError('Nonpositive block scale')
        values.append(v);means.append(q)
    total=sum(v/q for v,q in zip(values,means));median=float(np.median(total))
    if not np.isfinite(median) or median<=0: raise ValueError('Nonpositive balanced median')
    shares=[float(np.sum(v/q)/np.sum(total)) for v,q in zip(values,means)]
    if not np.allclose(shares,1/len(distances),rtol=0,atol=1e-12): raise ValueError('Block balance failed')
    return {'block_mean_squared_distances':means,'balanced_median_squared_distance':median,
            'unbalanced_distance_shares':(np.array(means)/sum(means)).tolist(),
            'balanced_distance_shares':shares}


def normalized_distances(distances,rows,cols,scales):
    return sum(D[np.ix_(rows,cols)]/q for D,q in zip(distances,scales['block_mean_squared_distances']))/scales['balanced_median_squared_distance']


def search_blocks(distances,y,groups,splits,protocol,solver,workers):
    for train,test in splits: assert_split(train,test,groups,y)
    scales=[fit_block_scales(distances,tr) for tr,_ in splits]
    blocks=[(normalized_distances(distances,tr,tr,s),normalized_distances(distances,va,tr,s)) for (tr,va),s in zip(splits,scales)]
    def one_alpha(alpha):
        kernels=[(np.exp(-alpha*tt),np.exp(-alpha*vt)) for tt,vt in blocks];candidates=[]
        for C in sorted(2.**v for v in protocol['C_exponents_base2']):
            scores=[];iterations=[]
            for (tr,va),(tt,vt),s in zip(splits,kernels,scales):
                model=checked_fit(svc(solver,C,alpha/s['balanced_median_squared_distance']),tt,y[tr])
                scores.append(float(balanced_accuracy_score(y[va],model.predict(vt))))
                iterations.append(int(model.n_iter_[0]))
            candidates.append({'C':C,'alpha':alpha,'mean_balanced_accuracy':float(np.mean(scores)),
                               'fold_balanced_accuracy':scores,'iterations':iterations,
                               'inner_block_gammas':[[alpha/(s['balanced_median_squared_distance']*q) for q in s['block_mean_squared_distances']] for s in scales]})
        return candidates
    with ThreadPoolExecutor(max_workers=workers) as pool:
        grid=[c for block in pool.map(one_alpha,sorted(2.**v for v in protocol['alpha_exponents_base2'])) for c in block]
    grid.sort(key=lambda c:(c['C'],c['alpha']))
    return choose_scaled(grid),grid,scales


def block_scores(path,X):
    """Replay a block-RBF model from RAW features; incompatible with plain-RBF replay."""
    with np.load(path,allow_pickle=False) as saved:
        if str(saved['kernel_format'])!='block_rbf_v1': raise ValueError('Unexpected model format')
        support=saved['support_vectors'];split=int(saved['block_boundary']);gammas=saved['block_gammas']
        if X.ndim!=2 or X.shape[1]!=support.shape[1] or not np.isfinite(X).all() or not 0<split<X.shape[1]:
            raise ValueError('Invalid raw feature matrix')
        exponent=gammas[0]*euclidean_distances(X[:,:split],support[:,:split],squared=True)
        exponent+=gammas[1]*euclidean_distances(X[:,split:],support[:,split:],squared=True)
        return np.exp(-exponent)@saved['dual_coef']+float(saved['intercept'])


def evaluate_blocks(data,distances,arm,layer,protocol,solver,output,workers,protocol_hash,names=None):
    target=output/arm/layer;target.mkdir(parents=True)
    raw_arm=protocol['new_arms'][arm];names=component_names(raw_arm) if names is None else names
    pred=np.full(len(data['y']),-1,dtype=int);scores=np.full(len(data['y']),np.nan);seen=np.zeros(len(pred),int);folds=[]
    for fold in range(5):
        train,test,splits=splits_for_outer(data,fold)
        best,grid,inner=search_blocks(distances,data['y'],data['groups'],splits,protocol,solver,workers)
        write_json(target/f'outer_{fold}_search.json',grid)
        scale=fit_block_scales(distances,train)
        tt=np.exp(-best['alpha']*normalized_distances(distances,train,train,scale))
        vt=np.exp(-best['alpha']*normalized_distances(distances,test,train,scale))
        gamma=best['alpha']/scale['balanced_median_squared_distance']
        model=checked_fit(svc(solver,best['C'],gamma),tt,data['y'][train])
        pred[test]=model.predict(vt);scores[test]=model.decision_function(vt);seen[test]+=1
        path=target/f'outer_{fold}_model.npz'
        block_gammas=[best['alpha']/(scale['balanced_median_squared_distance']*q) for q in scale['block_mean_squared_distances']]
        np.savez_compressed(path,kernel_format=np.asarray('block_rbf_v1'),support_vectors=data['X'][train][model.support_],
                            dual_coef=model.dual_coef_[0],intercept=model.intercept_[0],classes=model.classes_,
                            C=np.asarray(best['C']),alpha=np.asarray(best['alpha']),gamma=np.asarray(gamma),block_gammas=np.asarray(block_gammas),
                            block_mean_squared_distances=np.asarray(scale['block_mean_squared_distances']),
                            balanced_median_squared_distance=np.asarray(scale['balanced_median_squared_distance']),
                            block_boundary=np.asarray(protocol['block_boundary']),support_record_ids=data['ids'][train][model.support_],
                            layer=np.asarray(layer),feature_variant=np.asarray(arm),feature_names=np.asarray(names),protocol_sha256=np.asarray(protocol_hash))
        replay=block_scores(path,data['X'][test]);error=float(abs(replay-scores[test]).max())
        if error>1e-6 or not np.array_equal((replay>0).astype(int),pred[test]): raise ValueError(f'Block export replay failed: {error}')
        receipt={'outer':{'training_ids':data['ids'][train].tolist(),**scale},
                 'inner':[{'fold':i,'training_ids':data['ids'][tr].tolist(),**s} for i,((tr,_),s) in enumerate(zip(splits,inner))]}
        write_json(target/f'outer_{fold}_scales.json',receipt)
        record={'outer_fold':fold,'best':best,'outer_scale':scale,'inner_scales':inner,'block_gammas':block_gammas,
                'grid_boundary':boundary(best,protocol),'train_n':len(train),'test_n':len(test),
                'metrics':metrics(data['y'][test],pred[test],scores[test]),'support_vectors':len(model.support_),
                'iterations':int(model.n_iter_[0]),'export_max_score_error':error}
        folds.append(record);write_json(target/f'outer_{fold}_result.json',record)
        print(f'{arm}/{layer}: outer fold {fold+1}/5 saved',flush=True)
    if not np.all(seen==1) or not np.isfinite(scores).all() or (pred<0).any(): raise ValueError('Invalid held-out coverage')
    return pred,scores,folds


def reuse_scale(data,arm,layer,previous,output):
    source=previous/arm/layer;target=output/arm/layer;target.mkdir(parents=True)
    with (source/'held_out_predictions.csv').open(newline='') as f: rows=list(csv.DictReader(f))
    if [r['record_id'] for r in rows]!=list(data['ids']) or [r['group_id'] for r in rows]!=list(data['groups']): raise ValueError('Reference identity mismatch')
    for key,expected in [('true_label',data['y']),('outer_fold',data['outer'])]: np.testing.assert_array_equal([int(r[key]) for r in rows],expected)
    pred=np.array([int(r['predicted_label']) for r in rows]);score=np.array([float(r['decision_score']) for r in rows])
    old=json.loads((source/'summary.json').read_text())
    if old['feature_array_sha256']!=array_hash(data['X']) or old['metrics']!=summarize_oof(data['y'],pred,score,data['outer']): raise ValueError('Reference matrix/metric mismatch')
    refs=[]
    for fold in range(5):
        train,test,_=splits_for_outer(data,fold);path=source/f'outer_{fold}_model.npz'
        with np.load(path,allow_pickle=False) as model:
            ids=list(model['support_record_ids']);index={r:i for i,r in enumerate(data['ids'])}
            if not set(ids)<=set(data['ids'][train]) or list(model['feature_names'])!=component_names(arm): raise ValueError('Reference membership/names mismatch')
            np.testing.assert_array_equal(model['support_vectors'],data['X'][[index[r] for r in ids]])
        replay=portable_scores(path,data['X'][test]);error=float(abs(replay-score[test]).max())
        if error>1e-6 or not np.array_equal((replay>0).astype(int),pred[test]): raise ValueError('Reference replay mismatch')
        shutil.copy2(path,target/path.name);refs.append({'path':str(path.relative_to(ROOT)),'sha256':sha256(path),'replay_max_error':error})
    return pred,score,{'origin':'verified saved scale-aware reference','metrics':old['metrics'],'feature_array_sha256':array_hash(data['X']),
                       'boundary_folds':old['boundary_folds'],'model_references':refs}


def render_report(audit,out):
    tables=[];summary=[];contrasts=[]
    for layer,content in audit['layers'].items():
        tables.append('<h2>'+('Enhancer identification' if layer=='layer1' else 'Strong versus weak · known enhancers only')+'</h2>')
        rows=[]
        for arm,result in content['methods'].items():
            m=result['metrics']['macro_mean'];summary.append({'layer':layer,'method':arm,'origin':result['origin'],**m,'boundary_folds':len(result['boundary_folds'])})
            rows.append(f'<tr><th>{NAMES[arm]}</th><td>{100*m["accuracy"]:.2f}%</td><td>{100*m["balanced_accuracy"]:.2f}%</td><td>{m["roc_auc"]:.4f}</td><td>{m["mcc"]:.3f}</td><td>{len(result["boundary_folds"])}/5</td></tr>')
        tables.append('<div class="scroll"><table><thead><tr><th>Features</th><th>Accuracy</th><th>Balanced accuracy</th><th>AUC</th><th>MCC</th><th>Grid edge</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')
        rows=[]
        for name,c in content['inference']['contrasts'].items():
            x=c['metrics']['accuracy'];y=c['metrics']['roc_auc']
            rows.append(f'<tr><th>{name.replace("_"," ")}</th><td>{100*x["estimate"]:+.2f} [{100*x["ci95"][0]:+.2f}, {100*x["ci95"][1]:+.2f}]</td><td>{y["estimate"]:+.4f} [{y["ci95"][0]:+.4f}, {y["ci95"][1]:+.4f}]</td></tr>')
            for metric,v in c['metrics'].items(): contrasts.append({'layer':layer,'contrast':name,'metric':metric,'estimate':v['estimate'],'ci95_low':v['ci95'][0],'ci95_high':v['ci95'][1]})
        tables.append('<div class="scroll"><table><thead><tr><th>Contrast (first − second)</th><th>Accuracy difference, pp [95% interval]</th><th>AUC difference [95% interval]</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')
    write_csv(out/'block_summary.csv',summary);write_csv(out/'block_contrasts.csv',contrasts)
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Training-only block balance · local results</title><style>body{background:#f6f5ef;color:#183c45;font:16px/1.7 system-ui;margin:0}main{max-width:1150px;margin:auto;padding:40px 24px}h1{font:500 2.8rem/1.15 Georgia,serif}h2{margin-top:2.4rem}table{border-collapse:collapse;background:white;width:100%;font-size:14px}th,td{padding:12px;text-align:right;border-bottom:1px solid #dce5df}th:first-child{text-align:left}thead{background:#e4eeea}.scroll{overflow:auto}a{color:#006f6d}code{overflow-wrap:anywhere}.badge{padding:5px 10px;background:#e8d8b4;border-radius:5px}</style><main><span class="badge">Local research draft · not published</span><h1>Do structural summaries help when their distance contribution is balanced?</h1><p>Each training split divides the word and structural blocks by their own root mean squared pair distance. Both then contribute 50% of the aggregate training-pair squared distance. This does not imply equal influence for every pair, on test records, or on biological information.</p><p>The combined balanced distance is median-normalized before the same 90-setting C/alpha search. Both block statistics and the median are fitted afresh using only each inner-training subset and then only each outer-training subset. Frozen groups, feature definitions, solver and parameter grid remain unchanged. The four saved unbalanced models are verified controls, not new independent evidence. Single-block balancing cancels algebraically under median normalization.</p><p><a href="interpretation.html">Plain-language explanation</a> · <a href="block_summary.csv">Summary CSV</a> · <a href="block_contrasts.csv">Paired contrasts CSV</a> · <a href="protocol_snapshot.json">Frozen protocol</a> · <a href="block_audit.json">Audit</a> · <a href="validation.json">Validation</a></p>'''+''.join(tables)+'''<h2>Interpretation limits</h2><p>Scores are equal-weight means across five held-out folds; AUC/AP are ranked within folds. Strength uses known enhancers only. Intervals are 1,000 paired whole-group resamples, conditional on saved models/folds, without retraining, analysis-selection uncertainty or multiplicity correction. This analysis follows earlier results on the same benchmark and remains exploratory.</p><p>The fixed equal-distance balance was not tuned. It can amplify noise as well as signal, and it is not established as optimal. C/alpha endpoint choices are reported without expanding the grid after results. No replacement or full-data model is selected. Original author-code and historical numerical reproduction remain unresolved. No contaminated historical-test data or new lentiMPRA measurements enter fitting; historical labels and measured reporter activity remain different targets.</p>'''
    html+=f'<p>{audit["new_svm_fits"]:,} new fits; {audit["new_outer_models"]} new outer models. Protocol hash: <code>{audit["protocol_sha256"]}</code>.</p></main></html>'
    (out/'report.html').write_text(html)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();out=args.output.resolve()
    if not 1<=args.workers<=8 or (out.exists() and any(out.iterdir())): parser.error('Use 1–8 workers and a new/empty output directory')
    protocol=json.loads(PROTOCOL.read_text());solver_path=HERE/'training_protocol.json';solver=json.loads(solver_path.read_text())
    previous=HERE/protocol['previous_run'];checkpoint_path=HERE/protocol['previous_checkpoint'];cp=json.loads(checkpoint_path.read_text())
    if sha256(previous/'delivery_manifest.json')!=cp['delivery_manifest_sha256'] or sha256(previous/'scale_audit.json')!=cp['audit_sha256']: raise ValueError('Changed prior checkpoint')
    verify_manifest(previous,json.loads((previous/'delivery_manifest.json').read_text()),'files_sha256')
    for key in ('C_exponents_base2','alpha_exponents_base2','weights'): assert protocol[key]==cp['protocol'][key]
    assert protocol['new_arms']==NEW_ARMS and protocol['reference_arms']==list(ARMS)
    layers=load_inputs();seq={r['record_id']:r['sequence'] for r in load_benchmark()}
    out.mkdir(parents=True,exist_ok=True);snapshot=out/'source_snapshot';snapshot.mkdir()
    for p in [*sorted(HERE.glob('*.py')),PROTOCOL,solver_path,HERE/'scale_protocol.json',HERE/'component_protocol.json',HERE/'properties_s2.json']: shutil.copy2(p,snapshot/p.name)
    shutil.copy2(PROTOCOL,out/'protocol_snapshot.json')
    paths=[checkpoint_path,PREPARED/'benchmark.csv',DEFAULT_FEATURES,FEATURE_CHECKPOINT/'evaluation_assignments.csv',FEATURE_CHECKPOINT/'features_audit.json',previous/'scale_audit.json',previous/'delivery_manifest.json']
    for arm in ARMS: paths+=list((previous/arm).rglob('*'))
    inputs={str(p.relative_to(ROOT)):sha256(p) for p in paths if p.is_file()}
    audit={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'protocol':protocol,'protocol_sha256':sha256(PROTOCOL),
           'source_sha256':{p.name:sha256(p) for p in snapshot.iterdir()},'input_sha256':inputs,
           'environment':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','threadpoolctl')}},
           'git_head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'git_status_at_start':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'workers':args.workers,
           'layers':{},'new_svm_fits':0,'new_outer_models':0,'full_data_model_fitted':False,'publication_status':'Local only; no commit, push or deployment'}
    (out/'environment-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    write_json(out/'block_audit.json',audit);start=time.monotonic();print(f'Protocol frozen before fits: {audit["protocol_sha256"]}',flush=True)
    with threadpool_limits(limits=1):
        for layer,data in layers.items():
            parts=[components(seq[r]) for r in data['ids']];F=np.stack([p[0] for p in parts]);theta=np.stack([p[1] for p in parts])
            matrices,Z=component_matrices(F,theta,protocol['weights'][layer]);np.testing.assert_array_equal(matrices['full'],data['X'])
            np.savez_compressed(out/f'{layer}_components.npz',F=F,theta=theta,Z=Z,ids=data['ids'],y=data['y'])
            methods={};predictions={}
            for arm in ARMS:
                pred,score,result=reuse_scale({**data,'X':matrices[arm]},arm,layer,previous,out)
                methods[arm]=result;predictions[arm]=(pred,score)
                save_predictions(out,arm,layer,data,pred,score);write_json(out/arm/layer/'summary.json',result)
            for arm,raw in NEW_ARMS.items():
                X=matrices[raw];split=protocol['block_boundary'];distances=[]
                with threadpool_limits(limits=4):
                    for block in (X[:,:split],X[:,split:]):
                        D=euclidean_distances(block,squared=True);np.maximum(D,0,out=D);np.fill_diagonal(D,0);distances.append(D)
                pred,score,folds=evaluate_blocks({**data,'X':X},distances,arm,layer,protocol,solver,out,args.workers,audit['protocol_sha256'])
                result={'origin':'new train-only block-balanced fits','raw_feature_arm':raw,'feature_array_sha256':array_hash(X),
                        'metrics':summarize_oof(data['y'],pred,score,data['outer']),'folds':folds,
                        'boundary_folds':[f['outer_fold'] for f in folds if any(f['grid_boundary'].values())]}
                methods[arm]=result;predictions[arm]=(pred,score)
                save_predictions(out,arm,layer,data,pred,score);write_json(out/arm/layer/'summary.json',result)
                audit['new_svm_fits']+=5*(len(protocol['C_exponents_base2'])*len(protocol['alpha_exponents_base2'])*3+1);audit['new_outer_models']+=5
                del distances,D
            audit['layers'][layer]={'n':len(data['y']),'methods':methods,'inference':contrasts_with_intervals(data,predictions,protocol['paired_bootstrap'],protocol['contrasts'])}
            write_json(out/'block_audit.json',audit);print(f'{layer}: paired contrasts saved',flush=True)
    assert audit['new_svm_fits']==protocol['expected_new_svm_fits'] and audit['new_outer_models']==protocol['expected_new_outer_models']
    if any(sha256(ROOT/p)!=h for p,h in inputs.items()) or any(sha256(HERE/p)!=h for p,h in audit['source_sha256'].items()): raise ValueError('Inputs/source changed during fits')
    audit.update(status='complete',completed_utc=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start)
    render_report(audit,out)
    audit['artifact_sha256']={str(p.relative_to(out)):sha256(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='block_audit.json'}
    write_json(out/'block_audit.json',audit);print(f'Complete: {audit["new_svm_fits"]} fits in {audit["seconds"]:.1f}s; {out/"report.html"}',flush=True)


if __name__=='__main__': main()
