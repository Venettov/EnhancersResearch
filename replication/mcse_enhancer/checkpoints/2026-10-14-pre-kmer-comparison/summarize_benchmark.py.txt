"""Audit a completed MCSE benchmark and summarize its prespecified comparison.

No models are fitted and no thresholds, variants or parameters are selected.
The saved fit audits are checked against the original frozen row assignments.
"""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import shutil

import numpy as np
from scipy.stats import rankdata

from common import HERE, ROOT, check_file, read_csv, sha256, write_csv, write_json


def metrics(y, score, prediction):
    """Confusion counts and rank-based AUROC, independently of runner metrics."""
    tn=int(np.sum((y==0)&(prediction==0)));fp=int(np.sum((y==0)&(prediction==1)))
    fn=int(np.sum((y==1)&(prediction==0)));tp=int(np.sum((y==1)&(prediction==1)))
    denominator=float(np.sqrt(float(tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))
    positives=int(np.sum(y==1));negatives=len(y)-positives
    auc=(rankdata(score)[y==1].sum()-positives*(positives+1)/2)/(positives*negatives)
    return {'n':len(y),'accuracy':(tp+tn)/len(y),'auroc':float(auc),
            'mcc':(tp*tn-fp*fn)/denominator if denominator else 0.,
            'sensitivity':tp/(tp+fn),'specificity':tn/(tn+fp),
            'tn':tn,'fp':fp,'fn':fn,'tp':tp}


def paired_bootstrap(y, a, b, groups, folds, repeats, seed):
    """Sample whole groups within fold; identical weights for both predictions."""
    rng=np.random.default_rng(seed);parts=[]
    for fold in sorted(set(folds)):
        mask=folds==fold;g,ix=np.unique(groups[mask],return_inverse=True)
        parts.append(np.column_stack([
            np.bincount(ix),np.bincount(ix,weights=(a[mask]==y[mask])),
            np.bincount(ix,weights=(b[mask]==y[mask]))]))
    estimates=np.empty((repeats,2))
    for i in range(repeats):
        n,correct_a,correct_b=sum((p[rng.integers(len(p),size=len(p))].sum(axis=0) for p in parts))
        estimates[i]=[correct_a/n,(correct_a-correct_b)/n]
    return {'mcse_accuracy_interval':np.quantile(estimates[:,0],[.025,.975]).tolist(),
            'mcse_minus_reference_accuracy_interval':np.quantile(estimates[:,1],[.025,.975]).tolist(),
            'replicates':repeats,'seed':seed,
            'method':'Paired whole-group bootstrap within each outer fold; percentile 95% intervals',
            'scope':'Conditional on fitted predictions; no refitting or parameter-selection uncertainty'}


def validate_and_collect(output):
    if list(output.glob('*failure.json')):
        raise ValueError('A failed run cannot be summarized as complete')
    plan=json.loads((output/'plan.json').read_text())
    provenance=json.loads((output/'provenance.json').read_text())
    source=output/'source_snapshot'
    for name,digest in provenance['sources_sha256'].items():check_file(source/name,digest)
    for name,digest in provenance['inputs_sha256'].items():check_file(HERE/name,digest)
    check_file(source/'repair_protocol.json',plan['protocol_sha256'])
    check_file(source/'model_settings.json',plan['settings_sha256'])
    specification=json.loads((source/'benchmark_protocol.json').read_text())
    protocol=json.loads((source/'repair_protocol.json').read_text())
    assert plan['mode']=='run' and plan['feature_variant']==specification['feature_variant']=='notebook_k2_full'
    assert plan['historical_test_loaded'] is False and plan['feature_shape']==[2968,15169]
    assert protocol['architecture']['passthrough'] is False
    order=protocol['architecture']['base_order']
    rows=read_csv(HERE/'output/2026-10-14-recovery/train.csv')
    ids=np.array([r['record_id'] for r in rows]);groups=np.array([r['group_id'] for r in rows])
    y=np.array([int(r['label']) for r in rows]);outer=np.array([int(r['outer_fold']) for r in rows])
    assert len(set(ids))==2968 and len(set(groups))==2451 and int(sum(y))==1484
    expected_ids=set(ids);id_index={r:i for i,r in enumerate(ids)}
    probabilities=np.full((len(y),len(order)+1),np.nan);seen=np.zeros(len(y),dtype=int)
    fit_count=0;warnings=Counter();selections=0

    def check_event(event,train,test):
        assert event['train_ids']==ids[train].tolist()
        assert event['predict_ids']==ids[test].tolist()
        assert event['train_groups']==sorted(set(groups[train]))
        assert event['predict_groups']==sorted(set(groups[test]))
        assert not set(groups[train])&set(groups[test])
        assert not set(ids[train])&set(ids[test])
        assert set(event['train_ids'])|set(event['predict_ids'])<=expected_ids

    for fold in range(5):
        train=np.flatnonzero(outer!=fold);test=np.flatnonzero(outer==fold)
        inner=np.array([int(rows[i][f'inner_fold_outer_{fold}']) for i in train])
        audit=json.loads((output/f'fold_{fold}_audit.json').read_text())
        events=[json.loads(line) for line in (output/f'fold_{fold}_events.jsonl').read_text().splitlines()]
        assert audit==events
        fits={e['stage']:e for e in audit if e['kind']=='fit'}
        assert len(fits)==sum(e['kind']=='fit' for e in audit)==25
        expected_stages={'meta/fixed'}
        for name in order:
            covered=[]
            for inner_fold in range(3):
                stage=f'{name}/oof{inner_fold}/predict';expected_stages.add(stage)
                inner_train=train[inner!=inner_fold];inner_test=train[inner==inner_fold]
                check_event(fits[stage],inner_train,inner_test);covered.extend(inner_test)
            assert sorted(covered)==train.tolist()
            stage=f'{name}/full/predict';expected_stages.add(stage)
            check_event(fits[stage],train,test)
        check_event(fits['meta/fixed'],train,test)
        assert set(fits)==expected_stages
        for e in audit:
            if e['kind']=='selection':
                assert e['policy']=='one fixed candidate; no tuning' and e['selected']==0
                fitting_stage=e['stage'].replace('/tune','/predict')
                assert e['training_ids']==fits[fitting_stage]['train_ids'];selections+=1
            else:
                assert e['kind']=='fit'
                warnings.update(w['category'] for w in e['warnings']);fit_count+=1
        assert not warnings.get('ConvergenceWarning',0)
        with np.load(output/f'fold_{fold}_predictions.npz',allow_pickle=False) as saved:
            np.testing.assert_array_equal(saved['record_ids'],ids[test])
            np.testing.assert_array_equal(saved['train_record_ids'],ids[train])
            np.testing.assert_array_equal(saved['base_order'],order)
            assert saved['oof_features'].shape==(len(train),6)
            assert saved['prediction_features'].shape==(len(test),6)
            assert saved['probability'].shape==(len(test),)
            for key in ['oof_features','prediction_features','probability']:
                assert np.isfinite(saved[key]).all() and ((saved[key]>=0)&(saved[key]<=1)).all()
            probabilities[test,:6]=saved['prediction_features']
            probabilities[test,6]=saved['probability'];seen[test]+=1
    assert fit_count==specification['expected_fits']==125 and selections==120
    assert np.all(seen==1) and np.isfinite(probabilities).all()
    exported=read_csv(output/'predictions.csv')
    assert len(exported)==2968 and len({r['record_id'] for r in exported})==2968
    for r in exported:
        i=id_index[r['record_id']]
        assert int(r['outer_fold'])==outer[i] and int(r['label'])==y[i]
        assert float(r['probability'])==probabilities[i,6]
    preflight=json.loads((output/'preflight.json').read_text())
    reference_path=ROOT/preflight['reference_path'];check_file(reference_path,preflight['reference_sha256'])
    reference_rows=read_csv(reference_path);reference={r['record_id']:r for r in reference_rows}
    assert len(reference_rows)==len(reference)==2968 and set(reference)==expected_ids
    reference_score=np.zeros(len(y));reference_prediction=np.zeros(len(y),dtype=int)
    for i,record_id in enumerate(ids):
        r=reference[record_id]
        assert r['group_id']==groups[i] and int(r['outer_fold'])==outer[i] and int(r['true_label'])==y[i]
        reference_score[i]=float(r['decision_score']);reference_prediction[i]=int(r['predicted_label'])
    np.testing.assert_array_equal(reference_prediction,(reference_score>0).astype(int))
    # Validate reported settings, including runtime overrides, rather than infer from names.
    effective=json.loads((output/'effective_parameters.json').read_text())
    settings=json.loads((source/'model_settings.json').read_text())['reported_parameters']
    for name,p in settings.items():
        for key,value in p.items():
            assert effective[name][('model__' if name=='MLP' else '')+key]==value
    for key,value in settings['CB'].items():assert effective['meta_CB'][key]==value
    assert effective['MLP']['model__max_iter']==2000
    assert effective['MLP']['model__early_stopping'] is False
    assert effective['MLP']['scale__with_mean'] is True and effective['MLP']['scale__with_std'] is True
    validation={'status':'passed','fits_checked':fit_count,'fixed_candidate_selections_checked':selections,
                'outer_folds_checked':5,'oof_base_partitions_checked':90,'held_out_records':len(y),
                'group_disjointness_checked_at_every_fit':True,'reference_ids_groups_labels_folds_match':True,
                'source_snapshots_checked':len(provenance['sources_sha256']),
                'feature_input_hashes_checked':len(provenance['inputs_sha256']),
                'warnings':dict(warnings),'historical_test_used':False,
                'limits':'Audits and saved predictions verified; fitted estimators were not serialized, so predictions were not replayed from model files.'}
    return rows,ids,groups,y,outer,order,probabilities,reference_score,reference_prediction,validation,specification


def summarize(output):
    analysis_source=output/'analysis_source_snapshot';analysis_source.mkdir(exist_ok=True)
    for name in ['summarize_benchmark.py','test_benchmark_summary.py']:
        shutil.copyfile(HERE/name,analysis_source/name)
    rows,ids,groups,y,outer,order,p,ref_score,ref_prediction,validation,spec=validate_and_collect(output)
    names=order+['MCSE stack','iEnhancer-2L binary SVM']
    scores=np.column_stack([p,ref_score]);predicted=np.column_stack([p>=.5,ref_prediction]).astype(int)
    summaries=[];fold_results=[]
    for i,name in enumerate(names):
        per_fold=[]
        for fold in range(5):
            mask=outer==fold;result=metrics(y[mask],scores[mask,i],predicted[mask,i])
            per_fold.append(result);fold_results.append({'model':name,'fold':fold,**result})
        summaries.append({'model':name,**metrics(y,scores[:,i],predicted[:,i]),
                          'mean_fold_accuracy':float(np.mean([r['accuracy'] for r in per_fold])),
                          'mean_fold_auroc':float(np.mean([r['auroc'] for r in per_fold]))})
    main=summaries[6];reference=summaries[7]
    runner=json.loads((output/'metrics.json').read_text())
    for key in ['accuracy','auroc','mcc']:np.testing.assert_allclose(main[key],runner[key],atol=1e-14,rtol=0)
    inference=paired_bootstrap(y,predicted[:,6],ref_prediction,groups,outer,
                              spec['uncertainty']['replicates'],spec['uncertainty']['seed'])
    difference=main['accuracy']-reference['accuracy']
    evidence={'status':'complete','interpretation':'Prespecified reported-parameter diagnostic, not an exact reproduction',
              'feature_variant':spec['feature_variant'],'feature_count':15169,'rows':2968,'groups':2451,
              'elapsed_seconds':runner['elapsed_seconds'],'validation':validation,
              'model_metrics':summaries,'accuracy_difference_vs_reference':difference,
              'uncertainty':inference,'limits':spec['limits'],
              'reference_comparison_limit':spec['reference']['not_a_controlled_algorithm_comparison'],
              'full_training_model_fitted':False,'historical_test_used':False,'lentiMPRA_used':False}
    write_json(output/'benchmark_summary.json',evidence)
    write_json(output/'validation.json',validation)
    write_csv(output/'model_metrics.csv',summaries);write_csv(output/'fold_metrics.csv',fold_results)
    write_csv(output/'all_held_out_predictions.csv',[
        {'record_id':str(ids[i]),'group_id':str(groups[i]),'outer_fold':int(outer[i]),'label':int(y[i]),
         **{f'{n}_probability':float(p[i,j]) for j,n in enumerate(order)},
         'MCSE_probability':float(p[i,6]),'SVM_decision_score':float(ref_score[i]),
         'SVM_predicted_label':int(ref_prediction[i])} for i in range(len(y))])
    render_report(output,evidence,fold_results)
    # Hash every run artifact after analysis; the manifest itself is excluded.
    artifacts={str(path.relative_to(output)):sha256(path) for path in sorted(output.rglob('*'))
               if path.is_file() and path.name!='artifact_manifest.json'}
    write_json(output/'artifact_manifest.json',artifacts)
    print(json.dumps({'status':'complete','mcse':main,'reference':reference,
                      'difference':difference,'uncertainty':inference,'validation':validation},indent=2))


def render_report(output,evidence,fold_results):
    main=evidence['model_metrics'][6];reference=evidence['model_metrics'][7]
    interval=evidence['uncertainty']['mcse_accuracy_interval']
    delta=evidence['accuracy_difference_vs_reference']*100
    ci=[v*100 for v in evidence['uncertainty']['mcse_minus_reference_accuracy_interval']]
    labels={'RF':'Random forest','XGB':'XGBoost','LGBM':'LightGBM','CB':'CatBoost',
            'ET':'Extra Trees','MLP':'Neural network (MLP)','MCSE stack':'MCSE combined model'}
    table=''.join(f"<tr><th scope='row'>{html.escape(labels.get(r['model'],r['model']))}</th><td>{r['accuracy']:.2%}</td>"
                  f"<td>{r['mean_fold_auroc']:.3f}</td><td>{r['mcc']:.3f}</td></tr>" for r in evidence['model_metrics'])
    folds=''.join(f"<tr><th scope='row'>{r['fold']+1}</th><td>{r['n']}</td><td>{r['accuracy']:.2%}</td>"
                 f"<td>{r['auroc']:.3f}</td></tr>" for r in fold_results if r['model']=='MCSE stack')
    difference_text=("The interval includes zero, so this run does not establish a clear accuracy improvement over that reference."
                     if ci[0]<=0<=ci[1] else
                     "This conditional interval excludes zero, but it does not account for parameter selection or previous exploration of these data.")
    content=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCSE-Enhancer · first local benchmark</title><style>
body{{margin:0;background:#f6f5ef;color:#183c45;font:17px/1.6 system-ui,sans-serif}}
main{{max-width:1060px;margin:auto;padding:48px 24px}}h1,h2{{line-height:1.2}}h1{{font:48px/1.12 Georgia,serif;max-width:850px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.13em;font-size:13px;color:#276f69}}.lead{{font-size:21px;max-width:850px}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:30px 0}}.card,section{{background:white;border:1px solid #d3dfdb;border-radius:14px;padding:24px;margin:20px 0}}
.card{{margin:0}}.number{{display:block;font-size:37px;line-height:1.3}}.note{{background:#e7efeb;padding:18px;border-radius:10px}}
table{{width:100%;border-collapse:collapse;margin:20px 0}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #d3dfdb}}thead{{background:#eff4f1}}
a{{color:#006e72}}code{{font-size:.87em;overflow-wrap:anywhere}}.scroll{{overflow-x:auto}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:36px}}section{{padding:18px}}}}</style>
<main><div class="eyebrow">Local research result · 14 October 2026</div><h1>MCSE-Enhancer: the repaired benchmark runs.</h1>
<p class="lead">A code-assisted reconstruction distinguishes legacy enhancer sequences from non-enhancer sequences using six classifiers and a final combined prediction.</p>
<p class="note"><strong>Reported-parameter diagnostic.</strong> This is a completed evaluation of our declared implementation. It is not an exact reproduction of the published pipeline: the original feature mapping and final ensemble settings remain ambiguous.</p>
<div class="cards"><div class="card">Held-out accuracy<strong class="number">{main['accuracy']:.2%}</strong>About {main['accuracy']*100:.0f} correct classifications per 100 sequences.</div>
<div class="card">Mean fold AUROC<strong class="number">{main['mean_fold_auroc']:.3f}</strong>Ranking separation; 0.5 is chance and 1.0 is perfect.</div>
<div class="card">Verified model fits<strong class="number">125</strong>Five outer folds, with three-fold base-model cross-fitting.</div></div>
<section><h2>What was tested</h2><p>All 2,968 training sequences, balanced between 1,484 enhancers and 1,484 non-enhancers, retained their 2,451 sequence/locus groups. Related sequences stayed together. Each record was held out once. The contaminated historical 400-sequence test set was excluded.</p>
<p>The <code>notebook_k2_full</code> variant was chosen before viewing results: 15,169 features, the six reported Table S1 base-model settings, and fixed CatBoost meta settings. The meta-model learned from out-of-fold base probabilities. MLP standardization was fitted within each training partition. No settings or thresholds were optimized during this run.</p>
<p>All 125 fit audits passed the row/group separation checks, and the run recorded {sum(evidence['validation']['warnings'].values())} warnings. Runtime: {evidence['elapsed_seconds']/60:.1f} minutes. The 23 preflight tests passed.</p></section>
<section><h2>Comparison with the earlier binary SVM</h2><p>The MCSE stack achieved <strong>{main['accuracy']:.2%}</strong> accuracy; the reconstructed iEnhancer-2L binary SVM achieved <strong>{reference['accuracy']:.2%}</strong> on exactly the same held-out records and groups. The difference is <strong>{delta:+.2f} percentage points</strong>.</p>
<p>The paired group-bootstrap interval for this difference is {ci[0]:+.2f} to {ci[1]:+.2f} points. {difference_text} The accuracy interval for MCSE alone is {interval[0]:.2%}–{interval[1]:.2%}.</p>
<p>These intervals describe uncertainty in the saved predictions, conditional on the fitted models. The two methods used different features and parameter-selection procedures, so the comparison cannot isolate the benefit of stacking.</p>
<div class="scroll"><table><thead><tr><th>Model</th><th>Accuracy</th><th>Mean fold AUROC</th><th>MCC</th></tr></thead><tbody>{table}</tbody></table></div>
<p>MCC is the Matthews correlation coefficient: +1 is perfect agreement, 0 is no correlation, and −1 is complete disagreement. Individual base classifiers are descriptive diagnostics. Their scores are not used to select a new model after seeing held-out outcomes.</p></section>
<section><h2>Results across the five outer folds</h2><table><thead><tr><th>Fold</th><th>Held-out sequences</th><th>Accuracy</th><th>AUROC</th></tr></thead><tbody>{folds}</tbody></table>
<p>Across all held-out rows: {main['tp']} enhancers and {main['tn']} non-enhancers correctly classified; {main['fn']} enhancers missed and {main['fp']} non-enhancers called enhancers. Sensitivity: {main['sensitivity']:.2%}; specificity: {main['specificity']:.2%}.</p></section>
<section><h2>What this means for the research</h2><p>The recovered features and settings now support a complete executable benchmark with repaired evaluation. That establishes a working reference implementation, not validation of the paper’s exact result or proof of biological mechanism.</p>
<p>The paper’s settings may already have been chosen using these benchmark labels, and these folds have informed earlier exploratory work. A stronger comparison would freeze any remaining choices and use an independently held-out evaluation, or clearly label a newly nested tuning analysis. The historical 81.5% accuracy is from a different evaluation and cannot be treated as a directly comparable target.</p>
<p>This experiment addresses enhancer versus non-enhancer labels. It does not test strong versus weak enhancers, cell specificity or measured lentiMPRA activity. Linking to <code>NEW_2026_DATA</code> still requires resolving assay normalization, defining the new target and checking sequence overlap.</p></section>
<section><h2>Inspect the evidence</h2><p><a href="benchmark_summary.json">Summary and intervals</a> · <a href="all_held_out_predictions.csv">All held-out predictions</a> · <a href="fold_metrics.csv">Fold metrics</a> · <a href="validation.json">Validation audit</a> · <a href="effective_parameters.json">Effective settings</a> · <a href="source_snapshot/benchmark_protocol.json">Frozen run protocol</a> · <a href="artifact_manifest.json">Checksums</a></p>
<p>Source snapshots, input hashes, per-fit membership audits and base/meta predictions are saved. Fitted estimators were not serialized; prediction replay requires rerunning the saved source with the pinned environment. No full-training deployment model was fitted.</p>
<p><a href="https://doi.org/10.1016/j.jmb.2023.168314" target="_blank" rel="noopener noreferrer">Mir et al. (2023)</a> · <a href="https://github.com/MirBilalAhmad/DNA-Enhancers/tree/d76c48946de9c46e0845df12c119a27b7e455444" target="_blank" rel="noopener noreferrer">Pinned author code</a></p><p>Everything in this run remains local. Nothing was committed or pushed.</p></section></main></html>'''
    (output/'report.html').write_text(content)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    summarize(parser.parse_args().output.resolve())
