"""Audit and summarize the fixed 3-mer denominator comparison; never fit models."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil
import numpy as np
from sklearn.preprocessing import StandardScaler
from common import HERE, ROOT, check_file, read_csv, sha256, write_json, write_csv
from feature_matrix import load_matrix as load_control_matrix
from normalization_features import VARIANT, load_matrix as load_alternative_matrix
from summarize_benchmark import metrics, paired_bootstrap, validate_and_collect

CONTROL=HERE/'output/2026-10-14-benchmark-k3-full'
ALTERNATIVE=HERE/'output/2026-10-15-benchmark-k3-paperL'
CORE=['evaluation.py','models.py','feature_matrix.py','run.py','model_settings.json','repair_protocol.json']


def check_feature_change(a,b,na,nb,sequences):
    """Independent substring counts check the base-4 counter and every other column."""
    na=np.asarray(na);nb=np.asarray(nb)
    np.testing.assert_array_equal(na,nb)
    if a.shape!=b.shape or a.shape!=(len(sequences),len(na)):
        raise ValueError('Mismatched feature shapes')
    mask=np.char.startswith(na,'Kmer3:')
    words=[n.split(':',1)[1] for n in na[mask]]
    if len(set(words))!=64 or any(len(w)!=3 or set(w)-set('ACGT') for w in words):
        raise ValueError('Expected 64 unique standalone triplets')
    common=np.flatnonzero(~mask)
    for start in range(0,len(common),256):
        np.testing.assert_array_equal(a[:,common[start:start+256]],b[:,common[start:start+256]])
    expected_a=[];expected_b=[];factors=[]
    for s in sequences:
        if len(s)<3 or set(s)-set('ACGT'):raise ValueError('Invalid sequence')
        counts=Counter(s[i:i+3] for i in range(len(s)-2))
        expected_a.append([counts[w]/(len(s)-2) for w in words])
        expected_b.append([counts[w]/len(s) for w in words])
        factors.append((len(s)-2)/len(s))
    np.testing.assert_allclose(a[:,mask],expected_a,rtol=0,atol=1e-15)
    np.testing.assert_allclose(b[:,mask],expected_b,rtol=0,atol=1e-15)
    np.testing.assert_allclose(a[:,mask].sum(axis=1),1,rtol=0,atol=1e-14)
    np.testing.assert_allclose(b[:,mask].sum(axis=1),factors,rtol=0,atol=1e-14)
    np.testing.assert_allclose(b[:,mask],a[:,mask]*np.asarray(factors)[:,None],rtol=0,atol=1e-15)
    return {'common_columns_exactly_equal':len(common),'word_columns':int(mask.sum()),
            'all_column_names_identical':True,'recounted_rows':len(sequences),
            'sequence_lengths':sorted(set(map(len,sequences))),
            'paper_to_ilearn_factors':sorted(set(factors)),
            'independent_count_max_error':{'ilearn':float(np.max(np.abs(a[:,mask]-expected_a))),
                                           'paper':float(np.max(np.abs(b[:,mask]-expected_b)))},
            'scale_relation_max_error':float(np.max(np.abs(b[:,mask]-a[:,mask]*np.asarray(factors)[:,None])))}


def verify_control(spec):
    check_file(CONTROL/'artifact_manifest.json',spec['control_manifest_sha256'])
    check_file(CONTROL/'benchmark_summary.json',spec['control_summary_sha256'])
    manifest=json.loads((CONTROL/'artifact_manifest.json').read_text())
    for name,digest in manifest.items():check_file(CONTROL/name,digest)
    return validate_and_collect(CONTROL)


def preflight(output):
    if output.exists():raise ValueError('Comparison output must be new')
    spec=json.loads((HERE/'normalization_comparison_protocol.json').read_text())
    control=verify_control(spec)
    for source in spec['sources'].values():check_file(ROOT/source['path'],source['sha256'])
    a,ya,ga,ida,na,ra=load_control_matrix('k3_full')
    b,yb,gb,idb,nb,rb=load_alternative_matrix(VARIANT)
    for v,w in [(ya,yb),(ga,gb),(ida,idb)]:np.testing.assert_array_equal(v,w)
    assert ra==rb and a.shape==b.shape==(2968,15217)
    result=check_feature_change(a,b,na,nb,[r['sequence'] for r in ra])
    assert result['common_columns_exactly_equal']==15153 and result['paper_to_ilearn_factors']==[.99]
    mask=np.char.startswith(na,'Kmer3:')
    aa=a[:,mask];bb=b[:,mask]
    # Both block representations preserve all observed orderings and ties.
    np.testing.assert_array_equal(np.argsort(aa,axis=0,kind='stable'),np.argsort(bb,axis=0,kind='stable'))
    outer=np.array([int(r['outer_fold']) for r in ra]);scaling=[]
    for fold in range(5):
        train=np.flatnonzero(outer!=fold);test=np.flatnonzero(outer==fold)
        splits=[('outer',train,test)]
        inner=np.array([int(ra[i][f'inner_fold_outer_{fold}']) for i in train])
        for j in range(3):splits.append((f'inner_{j}',train[inner!=j],train[inner==j]))
        for name,tr,te in splits:
            assert not set(ga[tr])&set(ga[te])
            sa=StandardScaler().fit(aa[tr]);sb=StandardScaler().fit(bb[tr])
            train_error=float(np.max(np.abs(sa.transform(aa[tr])-sb.transform(bb[tr]))))
            test_error=float(np.max(np.abs(sa.transform(aa[te])-sb.transform(bb[te]))))
            assert max(train_error,test_error)<1e-12
            scaling.append({'fold':fold,'split':name,'train_max_abs_difference':train_error,'held_out_max_abs_difference':test_error})
    for name in CORE:check_file(HERE/name,sha256(CONTROL/'source_snapshot'/name))
    output.mkdir(parents=True)
    shutil.copyfile(HERE/'normalization_comparison_protocol.json',output/'comparison_protocol.json')
    shutil.copyfile(HERE/'benchmark_normalization_protocol.json',output/'benchmark_normalization_protocol.json')
    result.update(status='passed',created_utc=datetime.now(timezone.utc).isoformat(),
        control_validation=control[9],ids_labels_groups_folds_identical=True,
        unchanged_core_sources={n:sha256(HERE/n) for n in CORE},
        orchestrator_changes='evaluate_repaired.run accepts an explicit feature loader; model and evaluation algorithms unchanged',
        feature_loader_sha256=sha256(HERE/'normalization_features.py'),
        observed_word_orderings_identical=True,train_only_standardization=scaling,
        historical_test_used=False,lentiMPRA_used=False)
    write_json(output/'feature_preflight.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='control_validation'},indent=2))


def probability_diagnostics(a,b):
    delta=np.abs(b-a)
    return {'max_abs_difference':float(delta.max()),'mean_abs_difference':float(delta.mean()),
            'unequal_probabilities':int(np.sum(a!=b)),
            'probabilities_differing_over_1e_12':int(np.sum(delta>1e-12)),
            'changed_labels_at_0_5':int(np.sum((a>=.5)!=(b>=.5)))}


def summarize(output):
    if (output/'comparison_summary.json').exists():raise ValueError('Summary output already exists; preserve completed evidence')
    spec=json.loads((output/'comparison_protocol.json').read_text())
    check_file(HERE/'normalization_comparison_protocol.json',sha256(output/'comparison_protocol.json'))
    check_file(ALTERNATIVE/'source_snapshot/benchmark_protocol.json',sha256(output/'benchmark_normalization_protocol.json'))
    a=verify_control(spec);b=validate_and_collect(ALTERNATIVE)
    for i in [1,2,3,4,7,8]:np.testing.assert_array_equal(a[i],b[i])
    assert a[0]==b[0] and a[5]==b[5]
    pa=json.loads((CONTROL/'provenance.json').read_text());pb=json.loads((ALTERNATIVE/'provenance.json').read_text())
    for key in ['inputs_sha256','python','packages']:assert pa[key]==pb[key],key
    for name in CORE:assert pa['sources_sha256'][name]==pb['sources_sha256'][name]
    assert (CONTROL/'effective_parameters.json').read_bytes()==(ALTERNATIVE/'effective_parameters.json').read_bytes()
    assert (CONTROL/'feature_names.json').read_bytes()==(ALTERNATIVE/'feature_names.json').read_bytes()
    feature_receipt=json.loads((output/'feature_preflight.json').read_text())
    assert pb['sources_sha256']['normalization_features.py']==feature_receipt['feature_loader_sha256']
    _,ids,groups,y,folds,order,old,_,_,_,_=a
    new=b[6];old_pred=(old>=.5).astype(int);new_pred=(new>=.5).astype(int)
    summaries=[];fold_rows=[];diagnostics=[]
    for variant,pred,score in [('k3_full',old_pred,old),(VARIANT,new_pred,new)]:
        for j,name in enumerate(order+['MCSE stack']):
            parts=[]
            for fold in range(5):
                mask=folds==fold;r=metrics(y[mask],score[mask,j],pred[mask,j]);parts.append(r)
                fold_rows.append({'variant':variant,'model':name,'fold':fold,**r})
            summaries.append({'variant':variant,'model':name,**metrics(y,score[:,j],pred[:,j]),
                              'mean_fold_auroc':float(np.mean([r['auroc'] for r in parts]))})
    for j,name in enumerate(order+['MCSE stack']):
        diagnostics.append({'model':name,'stage':'held_out',**probability_diagnostics(old[:,j],new[:,j])})
    for fold in range(5):
        with np.load(CONTROL/f'fold_{fold}_predictions.npz',allow_pickle=False) as c,np.load(ALTERNATIVE/f'fold_{fold}_predictions.npz',allow_pickle=False) as d:
            np.testing.assert_array_equal(c['train_record_ids'],d['train_record_ids'])
            for j,name in enumerate(order):
                diagnostics.append({'model':name,'stage':f'fold_{fold}_training_oof',**probability_diagnostics(c['oof_features'][:,j],d['oof_features'][:,j])})
    new_ci=paired_bootstrap(y,new_pred[:,6],old_pred[:,6],groups,folds,2000,20261014)
    old_ci=paired_bootstrap(y,old_pred[:,6],new_pred[:,6],groups,folds,2000,20261014)
    old_correct=old_pred[:,6]==y;new_correct=new_pred[:,6]==y
    transitions={'both_correct':int(sum(old_correct&new_correct)),
                 'paper_only_correct':int(sum(~old_correct&new_correct)),
                 'ilearn_only_correct':int(sum(old_correct&~new_correct)),
                 'both_wrong':int(sum(~old_correct&~new_correct))}
    difference=summaries[13]['accuracy']-summaries[6]['accuracy']
    assert abs(difference-(transitions['paper_only_correct']-transitions['ilearn_only_correct'])/len(y))<1e-14
    runner=json.loads((ALTERNATIVE/'metrics.json').read_text())
    for key in ['accuracy','auroc','mcc']:np.testing.assert_allclose(summaries[13][key],runner[key],atol=1e-14,rtol=0)
    result={'status':'complete','interpretation':'Exploratory repaired reconstruction; standalone 3-mer normalization sensitivity, not exact paper reproduction',
        'primary_difference_paper_minus_ilearn':difference,
        'uncertainty':{'accuracy_difference_95_interval':new_ci['mcse_minus_reference_accuracy_interval'],
                       'paper_accuracy_95_interval':new_ci['mcse_accuracy_interval'],
                       'ilearn_accuracy_95_interval':old_ci['mcse_accuracy_interval'],
                       'replicates':2000,'seed':20261014,'method':new_ci['method'],'scope':new_ci['scope']},
        'transitions':transitions,'model_metrics':summaries,'probability_diagnostics':diagnostics,
        'rows':len(y),'groups':len(set(groups)),'feature_count':15217,
        'validation':{'control':a[9],'alternative':b[9],'effective_parameters_identical':True,
                      'runtime_and_inputs_identical':True,'core_model_feature_evaluation_sources_identical':True,
                      'ids_groups_labels_folds_identical':True,'features':feature_receipt},
        'source_runs':{'ilearn':str(CONTROL.relative_to(ROOT)),'paper':str(ALTERNATIVE.relative_to(ROOT))},
        'elapsed_seconds':runner['elapsed_seconds'],'sources':spec['sources'],'limits':spec['limits'],
        'historical_test_used':False,'lentiMPRA_used':False,'winner_selected':False,
        'new_fits':125,'saved_control_fits_revalidated':125,'models_saved':False}
    write_json(output/'comparison_summary.json',result)
    write_csv(output/'model_metrics.csv',summaries);write_csv(output/'fold_metrics.csv',fold_rows)
    write_csv(output/'probability_diagnostics.csv',diagnostics)
    write_csv(output/'paired_predictions.csv',[{'record_id':str(ids[i]),'group_id':str(groups[i]),'outer_fold':int(folds[i]),'label':int(y[i]),
        **{f'{tag}_{model}_probability':float(score[i,j]) for tag,score in [('ilearn',old),('paper',new)] for j,model in enumerate(order+['MCSE'])},
        'ilearn_prediction':int(old_pred[i,6]),'paper_prediction':int(new_pred[i,6]),
        'ilearn_correct':int(old_correct[i]),'paper_correct':int(new_correct[i])} for i in range(len(y))])
    write_json(ALTERNATIVE/'validation.json',b[9])
    source=output/'analysis_source_snapshot';source.mkdir()
    for name in ['compare_normalization.py','summarize_benchmark.py','test_normalization.py','test_benchmark_summary.py']:
        shutil.copyfile(HERE/name,source/name)
    render_report(output,result)
    for folder in [ALTERNATIVE,output]:
        write_json(folder/'artifact_manifest.json',{str(p.relative_to(folder)):sha256(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='artifact_manifest.json'})
    print(json.dumps({k:result[k] for k in ['status','primary_difference_paper_minus_ilearn','uncertainty','transitions']},indent=2))


def render_report(output,r):
    a,b=r['model_metrics'][6],r['model_metrics'][13]
    ci=r['uncertainty']['accuracy_difference_95_interval'];delta=r['primary_difference_paper_minus_ilearn']*100
    same=r['probability_diagnostics'][6]['changed_labels_at_0_5']==0
    meaning=('The combined model made exactly the same held-out class decisions. The zero paired accuracy interval describes these identical decisions only; it does not prove equivalence on future data or other implementations.' if same else ('The paired interval includes zero, so this run does not establish a clear accuracy gain or loss. It does not prove equivalence.' if ci[0]<=0<=ci[1] else 'The paired interval excludes zero in this fixed comparison, but the reused benchmark does not provide fresh independent confirmation.'))
    table=''.join(f'<tr><th scope="row">{html.escape(x["model"])}</th><td>{x["accuracy"]:.2%}</td><td>{y["accuracy"]:.2%}</td><td>{100*(y["accuracy"]-x["accuracy"]):+.2f}</td><td>{x["mean_fold_auroc"]:.4f} / {y["mean_fold_auroc"]:.4f}</td></tr>' for x,y in zip(r['model_metrics'][:7],r['model_metrics'][7:]))
    diagnostics=''.join(f'<tr><th scope="row">{html.escape(d["model"])}</th><td>{d["max_abs_difference"]:.3g}</td><td>{d["probabilities_differing_over_1e_12"]}</td><td>{d["changed_labels_at_0_5"]}</td></tr>' for d in r['probability_diagnostics'][:7])
    t=r['transitions'];tests=json.loads((output/'preflight.json').read_text())['tests_passed_before_fitting']
    (output/'report.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MCSE: paper versus iLearn normalization</title><style>
body{{margin:0;background:#f6f5ef;color:#183c45;font:17px/1.65 system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:42px 24px}}h1{{font:46px/1.15 Georgia,serif}}h2{{line-height:1.25}}section,.note,.card{{background:white;border:1px solid #d3dfdb;border-radius:12px;padding:24px;margin:22px 0}}.note{{background:#e7efeb}}.eyebrow{{text-transform:uppercase;letter-spacing:.13em;font-size:13px}}.lead{{font-size:21px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.number{{display:block;font-size:36px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d3dfdb}}thead{{background:#eff4f1}}a{{color:#006e72}}code{{overflow-wrap:anywhere}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:35px}}main{{padding:25px 16px}}}}</style><main>
<p class="eyebrow">Local research · repaired reconstruction · 15 October 2026</p><h1>Does the paper’s normalization change MCSE predictions?</h1><p class="lead">The same three-letter DNA words, data groups and model settings. Only the denominator of the standalone word-frequency block changed.</p><p class="note"><strong>Normalization sensitivity, not exact reproduction.</strong> We compared a literal reading of Equation 7 with the inspected iLearn calculation. All other feature interpretations and evaluation repairs remain in place.</p>
<div class="cards"><div class="card">Saved iLearn control<strong class="number">{a['accuracy']:.2%}</strong>Word count / 198.</div><div class="card">Paper denominator<strong class="number">{b['accuracy']:.2%}</strong>Word count / 200.</div><div class="card">Accuracy difference<strong class="number">{delta:+.2f} pp</strong>Paper minus iLearn.</div></div>
<section><h2>What the result means</h2><p>The paper-normalized model correctly classified {b['tp']+b['tn']:,} of 2,968 sequences; the saved iLearn model classified {a['tp']+a['tn']:,} correctly. The conditional paired 95% interval for the difference is <strong>{ci[0]*100:+.2f} to {ci[1]*100:+.2f} percentage points</strong>. {meaning}</p><p>Mean fold AUROC was {a['mean_fold_auroc']:.4f} with iLearn normalization and {b['mean_fold_auroc']:.4f} with the paper denominator. AUROC describes ranking; differences are descriptive, without a specified uncertainty interval.</p></section>
<section><h2>Why the two formulas differ</h2><p>A 200-base sequence contains 198 overlapping three-letter windows. iLearn divides each word’s count by 198, so the 64 word frequencies sum to 1. The paper’s Equation 7 defines the denominator as sequence length: 200. Those frequencies sum to 0.99. For example, a word occurring 10 times has values 10/198 ≈ 0.050505 and 10/200 = 0.05.</p><p>Every sequence has the same length, so the paper formula is a uniform 1% reduction of this block, not additional sequence information. The 64 word columns retain their ordering across records; all 15,153 other columns are exactly unchanged. Total dimensionality remains 15,217.</p><p>Order-based tree splits and per-feature standardization can be invariant to a positive constant rescaling in exact arithmetic. Our training-only standardization check found agreement within numerical precision for all 20 outer/inner partitions. Finite-precision training can still change a fitted model; the measured probability and decision differences are recorded below. This result cannot establish the authors’ actual normalization choice.</p></section>
<section><h2>All classifier results</h2><div class="scroll"><table><thead><tr><th>Classifier</th><th>iLearn accuracy</th><th>Paper accuracy</th><th>Difference (pp)</th><th>Mean fold AUROC<br>iLearn / paper</th></tr></thead><tbody>{table}</tbody></table></div><p>Accuracy uses a fixed 0.5 probability threshold. The six base models are descriptive diagnostics; no winner or replacement was selected.</p></section>
<section><h2>Did the actual predictions change?</h2><p>The paper-normalized model corrected {t['paper_only_correct']} errors and introduced {t['ilearn_only_correct']} new errors. Both versions were correct on {t['both_correct']:,} records and wrong on {t['both_wrong']:,}.</p><div class="scroll"><table><thead><tr><th>Model</th><th>Largest probability change</th><th>Changes above 10⁻¹²</th><th>Changed class decisions</th></tr></thead><tbody>{diagnostics}</tbody></table></div><p>The CSV also records out-of-fold training probability differences for each base model and outer fold. A probability difference need not cross the decision threshold or change ranking.</p></section>
<section><h2>What was fixed and checked</h2><p>The same 2,968 records, 2,451 sequence/locus groups, five outer folds, three inner cross-fitting folds, six bases, CatBoost final model, S1 effective settings, software versions, seed, one-thread execution, MLP training-only scaling and 0.5 threshold were retained. There was no retuning. The saved 3-mer control was verified and reused without changing its files.</p><p>{tests} preflight tests passed. All 125 new fits and 125 saved control fits were audited. New warnings: {sum(r['validation']['alternative']['warnings'].values())}. New-run time: {r['elapsed_seconds']/60:.1f} minutes. Independent substring counts checked all changed feature values. Group separation and held-out coverage were checked at every fit.</p><p>Fitted estimators were not serialized; prediction replay from model weights was not performed. Sources, settings, fit audits and prediction arrays are retained. No full-training deployment model was produced.</p></section>
<section><h2>What remains unresolved</h2><p>This is an exploratory repaired reconstruction on previously examined historical enhancer/non-enhancer labels. It does not test strong versus weak enhancers or cell-specific activity. Published settings may already have used these labels. Bootstrap intervals condition on saved predictions and omit refitting, seed variation and prior-selection uncertainty.</p><p>The contaminated historical test and all NEW_2026_DATA outcomes were excluded. Feature-family mapping, final ensemble choices and the historical software environment remain unresolved. This denominator test does not reproduce the complete paper or resolve the separate lentiMPRA specificity-score normalization problem. A stronger confirmation needs an independently specified evaluation.</p><p><a href="comparison_summary.json">Full results and validation</a> · <a href="model_metrics.csv">All model metrics</a> · <a href="fold_metrics.csv">All fold metrics</a> · <a href="paired_predictions.csv">Paired predictions</a> · <a href="probability_diagnostics.csv">Probability differences</a> · <a href="feature_preflight.json">Feature and scaling checks</a> · <a href="comparison_protocol.json">Frozen comparison protocol</a> · <a href="artifact_manifest.json">Checksums</a></p><p>Sources: <a href="https://doi.org/10.1016/j.jmb.2023.168314" target="_blank" rel="noopener noreferrer">Mir et al. (2023), Equation 7, page 4</a> · <a href="https://github.com/Superzchen/iLearn/blob/507aae17d9fea3d74a7c77984f1f1750eb734f53/descnucleotide/Kmer.py" target="_blank" rel="noopener noreferrer">Inspected iLearn Kmer calculation</a>.</p><p>Local analysis only. No website edits, commits or pushes.</p></section></main></html>''')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['preflight','summarize']);parser.add_argument('output',type=Path)
    args=parser.parse_args();globals()[args.mode](args.output.resolve())
