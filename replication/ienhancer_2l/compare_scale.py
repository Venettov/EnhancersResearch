#!/usr/bin/env python3
"""Train-fold distance normalization for a comparable dimensionless RBF search."""
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
from compare_components import (ARMS, LABELS, component_matrices, component_names,
                                contrasts_with_intervals, verify_manifest)
from compare_features import save_predictions
from train_svm import (DEFAULT_FEATURES, FEATURE_CHECKPOINT, array_hash, assert_split,
                       checked_fit, load_inputs, metrics, portable_scores,
                       splits_for_outer, summarize_oof, svc)

PROTOCOL = HERE/'scale_protocol.json'


def training_scale(distances, train):
    """Fit one scalar on the requested training block only, never its diagonal."""
    train = np.asarray(train)
    if (train.ndim != 1 or train.dtype.kind not in 'iu' or len(train) < 2 or
            len(np.unique(train)) != len(train) or (train < 0).any() or
            distances.ndim != 2 or distances.shape[0] != distances.shape[1] or
            (train >= len(distances)).any()):
        raise ValueError('Invalid training indices or distance matrix')
    block = distances[np.ix_(train,train)]
    values = block[np.triu_indices(len(train),k=1)]
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Invalid training distances')
    median = float(np.median(values))
    if not np.isfinite(median) or median <= 0:
        raise ValueError('Training median distance must be positive and finite')
    return median


def choose_scaled(candidates):
    if not candidates or not all(np.isfinite(c['mean_balanced_accuracy']) for c in candidates):
        raise ValueError('Empty or invalid search')
    return min(candidates,key=lambda c:(-c['mean_balanced_accuracy'],c['C'],c['alpha']))


def boundary(best, protocol):
    return {name:best[name] in (2.**min(protocol[key]),2.**max(protocol[key]))
            for name,key in [('C','C_exponents_base2'),('alpha','alpha_exponents_base2')]}


def scale_search(distances, y, groups, splits, protocol, solver, workers):
    """Each inner split has its OWN scale, refitted before validation predictions."""
    for train,test in splits:
        assert_split(train,test,groups,y)
    scales = [training_scale(distances,train) for train,_ in splits]
    # Pairwise distances are fixed per pair. No statistic uses excluded rows.
    blocks = [(distances[np.ix_(train,train)],distances[np.ix_(test,train)]) for train,test in splits]
    Cs = sorted(2.**v for v in protocol['C_exponents_base2'])
    alphas = sorted(2.**v for v in protocol['alpha_exponents_base2'])

    def one_alpha(alpha):
        kernels = [(np.exp(-alpha*tt/m),np.exp(-alpha*vt/m)) for (tt,vt),m in zip(blocks,scales)]
        candidates = []
        for C in Cs:
            scores,iterations = [],[]
            for (train,test),(tt,vt),m in zip(splits,kernels,scales):
                model = checked_fit(svc(solver,C,alpha/m),tt,y[train])
                scores.append(float(balanced_accuracy_score(y[test],model.predict(vt))))
                iterations.append(int(model.n_iter_[0]))
            candidates.append({'C':C,'alpha':alpha,'mean_balanced_accuracy':float(np.mean(scores)),
                               'fold_balanced_accuracy':scores,'iterations':iterations,
                               'inner_effective_gamma':[alpha/m for m in scales]})
        return candidates
    with ThreadPoolExecutor(max_workers=workers) as pool:
        candidates = [c for block in pool.map(one_alpha,alphas) for c in block]
    candidates.sort(key=lambda c:(c['C'],c['alpha']))
    return choose_scaled(candidates),candidates,scales


def evaluate_scale(data, distances, arm, layer, protocol, solver, output, workers, protocol_hash, names=None):
    target = output/arm/layer; target.mkdir(parents=True)
    names = component_names(arm) if names is None else names
    prediction = np.full(len(data['y']),-1,dtype=int); scores = np.full(len(data['y']),np.nan)
    seen = np.zeros(len(data['y']),dtype=int); folds=[]
    for fold in range(5):
        train,test,splits = splits_for_outer(data,fold)
        best,candidates,inner_scales = scale_search(distances,data['y'],data['groups'],splits,protocol,solver,workers)
        write_json(target/f'outer_{fold}_search.json',candidates)
        median = training_scale(distances,train)
        gamma = best['alpha']/median
        tt = np.exp(-gamma*distances[np.ix_(train,train)])
        vt = np.exp(-gamma*distances[np.ix_(test,train)])
        model = checked_fit(svc(solver,best['C'],gamma),tt,data['y'][train])
        prediction[test] = model.predict(vt); scores[test] = model.decision_function(vt); seen[test] += 1
        path = target/f'outer_{fold}_model.npz'
        np.savez_compressed(path,support_vectors=data['X'][train][model.support_],dual_coef=model.dual_coef_[0],
                            intercept=model.intercept_[0],classes=model.classes_,C=np.asarray(best['C']),gamma=np.asarray(gamma),
                            alpha=np.asarray(best['alpha']),training_median_squared_distance=np.asarray(median),
                            support_record_ids=data['ids'][train][model.support_],layer=np.asarray(layer),
                            feature_variant=np.asarray(arm),feature_names=np.asarray(names),protocol_sha256=np.asarray(protocol_hash))
        replay = portable_scores(path,data['X'][test]); error=float(abs(replay-scores[test]).max())
        if error > 1e-6 or not np.array_equal((replay>0).astype(int),prediction[test]):
            raise ValueError('Raw-feature model export replay failed')
        scales_record = {'outer_training_ids':data['ids'][train].tolist(),'outer_median_squared_distance':median,
                         'inner':[{'fold':i,'training_ids':data['ids'][tr].tolist(),
                                   'median_squared_distance':inner_scales[i]}
                                  for i,(tr,_) in enumerate(splits)]}
        write_json(target/f'outer_{fold}_scale.json',scales_record)
        result = {'outer_fold':fold,'best':best,'outer_effective_gamma':gamma,'outer_median_squared_distance':median,
                  'inner_median_squared_distances':inner_scales,'grid_boundary':boundary(best,protocol),
                  'train_n':len(train),'test_n':len(test),'metrics':metrics(data['y'][test],prediction[test],scores[test]),
                  'support_vectors':len(model.support_),'iterations':int(model.n_iter_[0]),'export_max_score_error':error}
        folds.append(result);write_json(target/f'outer_{fold}_result.json',result)
        print(f'{arm}/{layer}: outer fold {fold+1}/5 saved',flush=True)
    if not np.all(seen==1) or not np.isfinite(scores).all() or (prediction < 0).any():
        raise ValueError('Invalid held-out coverage')
    return prediction,scores,folds


def read_previous(data,arm,layer,previous,output):
    source = previous/(arm+'__retuned')/layer
    target = output/('previous_'+arm)/layer;target.mkdir(parents=True)
    with (source/'held_out_predictions.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    if [r['record_id'] for r in rows] != list(data['ids']) or [r['group_id'] for r in rows] != list(data['groups']):
        raise ValueError('Previous identities differ')
    for key,expected in [('true_label',data['y']),('outer_fold',data['outer'])]:
        np.testing.assert_array_equal([int(r[key]) for r in rows],expected)
    prediction=np.asarray([int(r['predicted_label']) for r in rows]);scores=np.asarray([float(r['decision_score']) for r in rows])
    result=json.loads((source/'summary.json').read_text())
    if result['feature_array_sha256'] != array_hash(data['X']):
        raise ValueError('Feature matrix differs from previous evaluation')
    if summarize_oof(data['y'],prediction,scores,data['outer']) != result['metrics']:
        raise ValueError('Previous metrics differ')
    references=[]
    for fold in range(5):
        train,test,_ = splits_for_outer(data,fold)
        path=source/f'outer_{fold}_model.npz'
        with np.load(path,allow_pickle=False) as saved:
            ids=list(saved['support_record_ids'])
            if not set(ids) <= set(data['ids'][train]):
                raise ValueError('Previous support vectors leave training set')
            index={r:i for i,r in enumerate(data['ids'])}
            np.testing.assert_array_equal(saved['support_vectors'],data['X'][[index[r] for r in ids]])
            if list(saved['feature_names']) != component_names(arm):
                raise ValueError('Previous feature names differ')
        replay=portable_scores(path,data['X'][test]);error=float(abs(replay-scores[test]).max())
        if error>1e-6 or not np.array_equal((replay>0).astype(int),prediction[test]):
            raise ValueError('Previous prediction replay failed')
        shutil.copy2(path,target/path.name)
        references.append({'path':str(path.relative_to(ROOT)),'sha256':sha256(path),'replay_max_error':error})
    return prediction,scores,{'origin':'verified previous raw-gamma search','metrics':result['metrics'],
                             'feature_array_sha256':array_hash(data['X']),'model_references':references,
                             'boundary_folds':result['boundary_folds']}


def render_report(audit,output):
    sections=[];summary=[];contrasts=[]
    for layer,content in audit['layers'].items():
        sections.append('<h2>'+('Enhancer versus non-enhancer' if layer=='layer1' else 'Strong versus weak · known enhancers only')+'</h2>')
        rows=[]
        for arm in ARMS:
            new=content['methods'][arm];old=content['methods']['previous_'+arm]
            m=new['metrics']['macro_mean'];p=old['metrics']['macro_mean']
            rows.append(f'<tr><th>{LABELS[arm]}</th><td>{100*p["accuracy"]:.2f}%</td><td>{100*m["accuracy"]:.2f}%</td>'
                        f'<td>{m["roc_auc"]:.4f}</td><td>{m["mcc"]:.3f}</td><td>{len(new["boundary_folds"])}/5</td></tr>')
            for mode,item in [('previous',old),('scale_aware',new)]:
                summary.append({'layer':layer,'arm':arm,'search':mode,**item['metrics']['macro_mean'],'boundary_folds':len(item['boundary_folds'])})
        sections.append('<div class="scroll"><table><tr><th>Representation</th><th>Previous accuracy</th><th>Scale-aware accuracy</th><th>Scale-aware AUC</th><th>MCC</th><th>Grid edge</th></tr>'+''.join(rows)+'</table></div>')
        rows=[]
        for name,c in content['inference']['contrasts'].items():
            a=c['metrics']['accuracy'];b=c['metrics']['roc_auc']
            rows.append(f'<tr><th>{name.replace("_"," ")}</th><td>{100*a["estimate"]:+.2f} [{100*a["ci95"][0]:+.2f}, {100*a["ci95"][1]:+.2f}]</td>'
                        f'<td>{b["estimate"]:+.4f} [{b["ci95"][0]:+.4f}, {b["ci95"][1]:+.4f}]</td></tr>')
            for metric,value in c['metrics'].items():
                contrasts.append({'layer':layer,'contrast':name,'metric':metric,'estimate':value['estimate'],
                                  'ci95_low':value['ci95'][0],'ci95_high':value['ci95'][1]})
        sections.append('<div class="scroll"><table><tr><th>Paired contrast</th><th>Accuracy difference, pp [95% interval]</th><th>AUC difference [95% interval]</th></tr>'+''.join(rows)+'</table></div>')
    write_csv(output/'scale_summary.csv',summary);write_csv(output/'scale_contrasts.csv',contrasts)
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scale-aware SVM comparison · local analysis</title><style>
body{margin:0;background:#f6f5ef;color:#183c45;font:16px/1.65 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:40px 24px}h1{font:500 2.7rem/1.2 Georgia,serif}h2{margin-top:2.5rem}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;background:white;font-size:14px}th,td{padding:12px;border-bottom:1px solid #dbe4e1;text-align:right;white-space:nowrap}th:first-child{text-align:left}tr:first-child{background:#183c45;color:white}a{color:#006f6d}.badge{background:#e9d5a7;padding:6px 12px;border-radius:6px}code{overflow-wrap:anywhere}li{margin:.6rem 0}</style><main>
<span class="badge">Local research draft · not published</span><h1>Do ordinary DNA words still perform better with a scale-aware search?</h1>
<p>The same four representations are evaluated on the frozen grouped folds. Each inner training set supplies its own median squared pair distance m. The RBF kernel is exp(−alpha × distance² / m). After inner selection of C and alpha, the outer model recomputes m from its outer training records only. Validation and test records never enter the scale statistic.</p>
<p>Every representation receives the same 90-setting C/alpha search. This is denser than the earlier 48-setting raw-gamma search, so changes from those earlier scores reflect a changed search procedure, not median normalization alone. Feature coordinates, relative block weights, sequence-specific Z and evaluation groups remain unchanged. The method cancels a uniform feature-unit change; it does not equalize individual coordinates or blocks.</p>
<p><a href="interpretation.html">Plain-language interpretation</a> · <a href="scale_summary.csv">Summary CSV</a> · <a href="scale_contrasts.csv">Paired differences CSV</a> · <a href="scale_audit.json">Full audit</a> · <a href="protocol_snapshot.json">Frozen protocol</a> · <a href="validation.json">Validation</a></p>'''
    doc+=''.join(sections)
    doc+='''<h2>How to read the comparisons</h2><ul><li>Words-minus contrasts compare current scale-aware models. Positive values favor ordinary word frequencies. Search-change contrasts compare the new procedure minus the saved earlier procedure for the same representation; those older models are reused, not independently confirmed.</li><li>Metrics are equal-weight means across five held-out folds. AUC rankings stay within each fold. The strength task uses only known enhancers and does not measure the complete two-stage cascade.</li><li>Conditional pointwise intervals resample whole groups 1,000 times using paired draws. They exclude retraining and protocol-selection uncertainty and are not corrected for multiple comparisons. Crossing zero does not prove equivalence.</li><li>This follow-up was motivated by earlier results on the same benchmark. It remains exploratory; an independent evaluation is needed for confirmation. Grid boundaries are reported without post-result expansion. No replacement or full-data final model was selected.</li><li>No contaminated historical-test records or new lentiMPRA measurements entered fitting. Historical annotations differ from experimentally measured reporter activity. Original author-code and numerical reproduction remain unresolved.</li></ul>'''
    doc+=f'<p>{audit["new_svm_fits"]:,} new SVM fits; {audit["new_outer_models"]} new outer-fold models. Protocol SHA-256: <code>{audit["protocol_sha256"]}</code>.</p></main></html>'
    (output/'report.html').write_text(doc)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();output=args.output.resolve()
    if not 1<=args.workers<=8 or (output.exists() and any(output.iterdir())):
        parser.error('Use 1–8 workers and a new or empty output directory')
    protocol=json.loads(PROTOCOL.read_text());solver_path=HERE/'training_protocol.json';solver=json.loads(solver_path.read_text())
    previous=HERE/protocol['previous_run'];checkpoint_path=HERE/'checkpoints/2026-10-14-component-ablation.json'
    checkpoint=json.loads(checkpoint_path.read_text())
    if sha256(previous/'delivery_manifest.json')!=checkpoint['delivery_manifest_sha256'] or sha256(previous/'component_audit.json')!=checkpoint['audit_sha256']:
        raise ValueError('Changed previous checkpoint')
    verify_manifest(previous,json.loads((previous/'delivery_manifest.json').read_text()),'files_sha256')
    layers=load_inputs();seq={r['record_id']:r['sequence'] for r in load_benchmark()}
    output.mkdir(parents=True,exist_ok=True);snapshot=output/'source_snapshot';snapshot.mkdir()
    for p in [*sorted(HERE.glob('*.py')),PROTOCOL,solver_path,HERE/'component_protocol.json',HERE/'properties_s2.json']:
        shutil.copy2(p,snapshot/p.name)
    shutil.copy2(PROTOCOL,output/'protocol_snapshot.json')
    input_paths=[checkpoint_path,PREPARED/'benchmark.csv',DEFAULT_FEATURES,FEATURE_CHECKPOINT/'evaluation_assignments.csv',
                 FEATURE_CHECKPOINT/'features_audit.json',previous/'component_audit.json',previous/'delivery_manifest.json']
    for arm in ARMS:
        input_paths+=list((previous/(arm+'__retuned')).rglob('*'))
    inputs={str(p.relative_to(ROOT)):sha256(p) for p in input_paths if p.is_file()}
    audit={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'protocol':protocol,'protocol_sha256':sha256(PROTOCOL),
           'source_sha256':{p.name:sha256(p) for p in snapshot.iterdir()},'input_sha256':inputs,
           'environment':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','threadpoolctl')}},
           'git_head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'git_status_at_start':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
           'workers':args.workers,'layers':{},'new_svm_fits':0,'new_outer_models':0,'full_data_model_fitted':False,'publication_status':'Local only; no push authorized'}
    (output/'environment-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    write_json(output/'scale_audit.json',audit);start=time.monotonic()
    print(f'Protocol frozen before fits: {audit["protocol_sha256"]}',flush=True)
    with threadpool_limits(limits=1):
        for layer,data in layers.items():
            parts=[components(seq[r]) for r in data['ids']]
            F=np.stack([p[0] for p in parts]);theta=np.stack([p[1] for p in parts])
            matrices,Z=component_matrices(F,theta,protocol['weights'][layer]);np.testing.assert_array_equal(matrices['full'],data['X'])
            np.savez_compressed(output/f'{layer}_components.npz',F=F,theta=theta,Z=Z,ids=data['ids'],y=data['y'])
            methods={};predictions={}
            for arm in ARMS:
                X=matrices[arm];changed={**data,'X':X}
                old_pred,old_scores,old_result=read_previous(changed,arm,layer,previous,output)
                predictions['previous_'+arm]=(old_pred,old_scores);methods['previous_'+arm]=old_result
                save_predictions(output,'previous_'+arm,layer,data,old_pred,old_scores)
                write_json(output/('previous_'+arm)/layer/'summary.json',old_result)
                with threadpool_limits(limits=4):
                    distances=euclidean_distances(X,squared=True)
                np.maximum(distances,0,out=distances);np.fill_diagonal(distances,0)
                pred,scores,folds=evaluate_scale(changed,distances,arm,layer,protocol,solver,output,args.workers,audit['protocol_sha256'])
                predictions[arm]=(pred,scores)
                methods[arm]={'origin':'new scale-aware fits','metrics':summarize_oof(data['y'],pred,scores,data['outer']),
                              'feature_array_sha256':array_hash(X),'feature_shape':list(X.shape),'folds':folds,
                              'boundary_folds':[f['outer_fold'] for f in folds if any(f['grid_boundary'].values())]}
                save_predictions(output,arm,layer,data,pred,scores);write_json(output/arm/layer/'summary.json',methods[arm])
                audit['new_svm_fits']+=5*(len(protocol['C_exponents_base2'])*len(protocol['alpha_exponents_base2'])*3+1)
                audit['new_outer_models']+=5
                del distances
            inference=contrasts_with_intervals(data,predictions,protocol['paired_bootstrap'],protocol['contrasts'])
            audit['layers'][layer]={'n':len(data['y']),'methods':methods,'inference':inference}
            write_json(output/'scale_audit.json',audit);print(f'{layer}: paired comparisons saved',flush=True)
    if audit['new_svm_fits']!=protocol['expected_new_svm_fits'] or audit['new_outer_models']!=protocol['expected_new_outer_models']:
        raise ValueError('Unexpected fit count')
    if any(sha256(ROOT/p)!=h for p,h in inputs.items()) or any(sha256(HERE/p)!=h for p,h in audit['source_sha256'].items()):
        raise ValueError('Inputs or source changed during fits')
    audit.update(status='complete',completed_utc=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start)
    render_report(audit,output)
    audit['artifact_sha256']={str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='scale_audit.json'}
    write_json(output/'scale_audit.json',audit)
    print(f'Complete: {audit["new_svm_fits"]} fits in {audit["seconds"]:.1f}s; {output/"report.html"}',flush=True)


if __name__=='__main__':
    main()
