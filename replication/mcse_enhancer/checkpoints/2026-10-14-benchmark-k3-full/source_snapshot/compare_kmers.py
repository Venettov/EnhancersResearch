"""Controlled, paired Kmer2/Kmer3 comparison; no fitting or model selection here."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil
import numpy as np
from common import HERE, ROOT, check_file, read_csv, sha256, write_json, write_csv
from feature_matrix import load_matrix
from summarize_benchmark import metrics, paired_bootstrap, validate_and_collect

CONTROL=HERE/'output/2026-10-14-benchmark-notebook-k2'
ALTERNATIVE=HERE/'output/2026-10-14-benchmark-k3-full'
CORE=['evaluation.py','models.py','feature_matrix.py','run.py','model_settings.json','repair_protocol.json']


def check_feature_change(a,b,na,nb,sequences):
    """Compare all common columns exactly; independently recount the changed block."""
    na=np.asarray(na);nb=np.asarray(nb)
    ma=np.char.startswith(na,'Kmer2:');mb=np.char.startswith(nb,'Kmer3:')
    if sum(ma)!=16 or sum(mb)!=64:raise ValueError('Expected 16/64 standalone word columns')
    np.testing.assert_array_equal(na[~ma],nb[~mb])
    # Avoid allocating a second complete matrix just to compare the common block.
    ia=np.flatnonzero(~ma);ib=np.flatnonzero(~mb)
    for start in range(0,len(ia),256):
        np.testing.assert_array_equal(a[:,ia[start:start+256]],b[:,ib[start:start+256]])
    max_error={}
    for x,mask,names,k in [(a,ma,na,2),(b,mb,nb,3)]:
        words=[name.split(':',1)[1] for name in names[mask]]
        if len(set(words))!=4**k or any(len(w)!=k or set(w)-set('ACGT') for w in words):
            raise ValueError('Invalid standalone word names')
        expected=[]
        for s in sequences:
            count=Counter(s[i:i+k] for i in range(len(s)-k+1))
            expected.append([count[w]/(len(s)-k+1) for w in words])
        np.testing.assert_allclose(x[:,mask],expected,rtol=0,atol=1e-15)
        np.testing.assert_allclose(x[:,mask].sum(axis=1),1,rtol=0,atol=1e-14)
        max_error[f'k{k}']=float(np.max(np.abs(x[:,mask]-expected)))
    return {'common_columns_exactly_equal':len(ia),'recounted_rows':len(sequences),
            'k2_columns':16,'k3_columns':64,'independent_count_max_error':max_error,
            'normalization':'Overlapping counts/(L-k+1) in both variants'}


def verify_control(spec):
    check_file(CONTROL/'artifact_manifest.json',spec['control_manifest_sha256'])
    check_file(CONTROL/'benchmark_summary.json',spec['control_summary_sha256'])
    manifest=json.loads((CONTROL/'artifact_manifest.json').read_text())
    for name,digest in manifest.items():check_file(CONTROL/name,digest)
    return validate_and_collect(CONTROL)


def preflight(output):
    if output.exists():raise ValueError('Comparison output must be new')
    spec=json.loads((HERE/'kmer_comparison_protocol.json').read_text())
    control=verify_control(spec)
    a,ya,ga,ida,na,ra=load_matrix('notebook_k2_full')
    b,yb,gb,idb,nb,rb=load_matrix('k3_full')
    for v,w in [(ya,yb),(ga,gb),(ida,idb)]:np.testing.assert_array_equal(v,w)
    assert ra==rb and a.shape==(2968,15169) and b.shape==(2968,15217)
    result=check_feature_change(a,b,na,nb,[r['sequence'] for r in ra])
    assert result['common_columns_exactly_equal']==15153
    for name in CORE:check_file(HERE/name,sha256(CONTROL/'source_snapshot'/name))
    output.mkdir(parents=True)
    shutil.copyfile(HERE/'kmer_comparison_protocol.json',output/'comparison_protocol.json')
    shutil.copyfile(HERE/'benchmark_k3_protocol.json',output/'benchmark_k3_protocol.json')
    result.update(status='passed',created_utc=datetime.now(timezone.utc).isoformat(),
                  control_validation=control[9],rows_labels_groups_folds_identical=True,
                  control_artifacts_checked=len(json.loads((CONTROL/'artifact_manifest.json').read_text())),
                  unchanged_core_sources={name:sha256(HERE/name) for name in CORE},
                  common_source_files_unchanged=True,historical_test_used=False)
    write_json(output/'feature_preflight.json',result)
    print(json.dumps(result,indent=2))


def summarize(output):
    spec=json.loads((output/'comparison_protocol.json').read_text())
    check_file(HERE/'kmer_comparison_protocol.json',sha256(output/'comparison_protocol.json'))
    check_file(ALTERNATIVE/'source_snapshot/benchmark_protocol.json',sha256(output/'benchmark_k3_protocol.json'))
    a=verify_control(spec);b=validate_and_collect(ALTERNATIVE)
    for index in [1,2,3,4,7,8]:np.testing.assert_array_equal(a[index],b[index])
    assert a[0]==b[0] and a[5]==b[5]
    pa=json.loads((CONTROL/'provenance.json').read_text());pb=json.loads((ALTERNATIVE/'provenance.json').read_text())
    for key in ['inputs_sha256','python','packages']:assert pa[key]==pb[key],key
    for name in CORE:assert pa['sources_sha256'][name]==pb['sources_sha256'][name]
    assert (CONTROL/'effective_parameters.json').read_bytes()==(ALTERNATIVE/'effective_parameters.json').read_bytes()
    names_a=json.loads((CONTROL/'feature_names.json').read_text());names_b=json.loads((ALTERNATIVE/'feature_names.json').read_text())
    assert [n for n in names_a if not n.startswith('Kmer2:')]==[n for n in names_b if not n.startswith('Kmer3:')]
    _,ids,groups,y,folds,order,old,_,_,_,_=a
    new=b[6];old_pred=(old>=.5).astype(int);new_pred=(new>=.5).astype(int)
    summaries=[];fold_rows=[]
    for variant,pred,score in [('notebook_k2_full',old_pred,old),('k3_full',new_pred,new)]:
        for j,name in enumerate(order+['MCSE stack']):
            parts=[]
            for fold in range(5):
                mask=folds==fold;r=metrics(y[mask],score[mask,j],pred[mask,j]);parts.append(r)
                fold_rows.append({'variant':variant,'model':name,'fold':fold,**r})
            summaries.append({'variant':variant,'model':name,**metrics(y,score[:,j],pred[:,j]),
                              'mean_fold_auroc':float(np.mean([r['auroc'] for r in parts]))})
    new_ci=paired_bootstrap(y,new_pred[:,6],old_pred[:,6],groups,folds,2000,20261014)
    old_ci=paired_bootstrap(y,old_pred[:,6],new_pred[:,6],groups,folds,2000,20261014)
    old_correct=old_pred[:,6]==y;new_correct=new_pred[:,6]==y
    transitions={'both_correct':int(sum(old_correct&new_correct)),
                 'k3_only_correct':int(sum(~old_correct&new_correct)),
                 'k2_only_correct':int(sum(old_correct&~new_correct)),
                 'both_wrong':int(sum(~old_correct&~new_correct))}
    old_main=summaries[6];new_main=summaries[13]
    difference=new_main['accuracy']-old_main['accuracy']
    assert abs(difference-(transitions['k3_only_correct']-transitions['k2_only_correct'])/len(y))<1e-14
    result={'status':'complete','interpretation':'Exploratory repaired reconstruction; standalone k-mer length sensitivity, not exact paper reproduction',
            'primary_difference_k3_minus_k2':difference,
            'uncertainty':{'accuracy_difference_95_interval':new_ci['mcse_minus_reference_accuracy_interval'],
                           'k3_accuracy_95_interval':new_ci['mcse_accuracy_interval'],
                           'k2_accuracy_95_interval':old_ci['mcse_accuracy_interval'],
                           'replicates':2000,'seed':20261014,'method':new_ci['method'],'scope':new_ci['scope']},
            'transitions':transitions,'model_metrics':summaries,'rows':len(y),'groups':len(set(groups)),
            'validation':{'control':a[9],'alternative':b[9],'effective_parameters_identical':True,
                          'runtime_and_inputs_identical':True,'core_model_feature_evaluation_sources_identical':True,
                          'ids_groups_labels_folds_identical':True,
                          'features':json.loads((output/'feature_preflight.json').read_text())},
            'source_runs':{'k2':str(CONTROL.relative_to(ROOT)),'k3':str(ALTERNATIVE.relative_to(ROOT))},
            'limits':spec['limits'],'historical_test_used':False,'lentiMPRA_used':False,'winner_selected':False,
            'new_fits':125,'saved_control_fits_revalidated':125,'models_saved':False}
    write_json(output/'comparison_summary.json',result)
    write_csv(output/'model_metrics.csv',summaries);write_csv(output/'fold_metrics.csv',fold_rows)
    write_csv(output/'paired_predictions.csv',[{'record_id':str(ids[i]),'group_id':str(groups[i]),'outer_fold':int(folds[i]),'label':int(y[i]),
               **{f'{tag}_{model}_probability':float(score[i,j]) for tag,score in [('k2',old),('k3',new)] for j,model in enumerate(order+['MCSE'])},
               'k2_prediction':int(old_pred[i,6]),'k3_prediction':int(new_pred[i,6]),
               'k2_correct':int(old_correct[i]),'k3_correct':int(new_correct[i])} for i in range(len(y))])
    source=output/'analysis_source_snapshot';source.mkdir(exist_ok=True)
    for name in ['compare_kmers.py','summarize_benchmark.py','test_kmer_comparison.py','test_benchmark_summary.py']:
        shutil.copyfile(HERE/name,source/name)
    render_report(output,result)
    write_json(output/'artifact_manifest.json',{str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='artifact_manifest.json'})
    print(json.dumps({k:result[k] for k in ['status','primary_difference_k3_minus_k2','uncertainty','transitions']},indent=2))


def render_report(output,r):
    a=r['model_metrics'][6];b=r['model_metrics'][13];ci=r['uncertainty']['accuracy_difference_95_interval'];delta=100*r['primary_difference_k3_minus_k2']
    interpretation=('The interval includes zero: this comparison does not establish a clear accuracy advantage for either word length. It does not prove equivalence.' if ci[0]<=0<=ci[1] else 'The conditional interval excludes zero, but these previously explored folds do not provide fresh independent confirmation.')
    rows=''.join(f'<tr><th scope="row">{html.escape(x["model"])}</th><td>{x["accuracy"]:.2%}</td><td>{y["accuracy"]:.2%}</td><td>{(y["accuracy"]-x["accuracy"])*100:+.2f}</td><td>{x["mean_fold_auroc"]:.3f} / {y["mean_fold_auroc"]:.3f}</td></tr>' for x,y in zip(r['model_metrics'][:7],r['model_metrics'][7:]))
    t=r['transitions']
    (output/'report.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MCSE: 2-mer versus 3-mer comparison</title><style>
body{{margin:0;background:#f6f5ef;color:#183c45;font:17px/1.65 system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:42px 24px}}h1{{font:46px/1.15 Georgia,serif}}h2{{line-height:1.25}}section,.note,.card{{background:white;border:1px solid #d3dfdb;border-radius:12px;padding:24px;margin:22px 0}}.note{{background:#e7efeb}}.eyebrow{{text-transform:uppercase;letter-spacing:.13em;font-size:13px}}.lead{{font-size:21px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.number{{display:block;font-size:36px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d3dfdb}}thead{{background:#eff4f1}}a{{color:#006e72}}code{{overflow-wrap:anywhere}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:35px}}main{{padding:25px 16px}}}}</style><main>
<p class="eyebrow">Local research · repaired reconstruction · 14 October 2026</p><h1>Does changing two-letter DNA words to three-letter words improve MCSE?</h1><p class="lead">The same repaired pipeline, data groups and model settings were used. Only the separate word-frequency block changed.</p><p class="note"><strong>Feature sensitivity, not exact reproduction.</strong> The new variant follows the paper’s stated 3-mer length, with the inspected iLearn normalization. Original feature mapping, the paper’s denominator, final ensemble settings and historical software remain unresolved.</p>
<div class="cards"><div class="card">Saved 2-mer control<strong class="number">{a['accuracy']:.2%}</strong>Accuracy; 15,169 features.</div><div class="card">New 3-mer version<strong class="number">{b['accuracy']:.2%}</strong>Accuracy; 15,217 features.</div><div class="card">Difference<strong class="number">{delta:+.2f} pp</strong>3-mer minus 2-mer accuracy.</div></div>
<section><h2>What the result means</h2><p>The 3-mer version classified {b['tp']+b['tn']:,} of 2,968 sequences correctly, compared with {a['tp']+a['tn']:,} for 2-mers. The paired 95% interval for the accuracy difference is <strong>{ci[0]*100:+.2f} to {ci[1]*100:+.2f} percentage points</strong>. {interpretation}</p><p>A 2-mer is a two-letter DNA word such as AC; a 3-mer is a three-letter word such as ACG. Three-letter words describe more specific local patterns, but more detail does not automatically improve predictions. This comparison measures the effect of that representation change under the fixed pipeline; it cannot identify a biological mechanism.</p><p>Accuracy measures correct enhancer/non-enhancer labels. AUROC measures how well scores rank the classes; 0.5 is chance ranking and 1.0 is perfect. Mean fold AUROC was {a['mean_fold_auroc']:.3f} for 2-mers and {b['mean_fold_auroc']:.3f} for 3-mers. Ranking differences are descriptive; no uncertainty interval for them was specified.</p></section>
<section><h2>What changed—and what was held fixed</h2><p>The 16-column Kmer2 frequency block was replaced with the 64-column Kmer3 block. All <strong>15,153 common features</strong> were checked for exact equality. Independent overlapping-window counts verified both word blocks for every training sequence. For these 200-base sequences, frequencies use 199 windows for 2-mers and 198 for 3-mers. The paper instead writes a denominator of sequence length; that separate ambiguity was not mixed into this comparison.</p><p>The other descriptor families already include some 3-mer information. This experiment changes only the separate Kmer block; it does not compare all possible sources of 2-mer versus 3-mer information.</p><p>The same 2,968 rows, labels, 2,451 groups, five outer folds, three inner cross-fitting folds, six base classifiers, CatBoost final model, S1 settings, MLP training-only scaling, random seed, software and 0.5 threshold were retained. No parameter search or selection of a winning model was performed. The original 2-mer predictions were verified and reused, not refitted.</p></section>
<section><h2>All classifier results</h2><div class="scroll"><table><thead><tr><th>Classifier</th><th>2-mer accuracy</th><th>3-mer accuracy</th><th>Difference (pp)</th><th>Mean fold AUROC<br>2-mer / 3-mer</th></tr></thead><tbody>{rows}</tbody></table></div><p>Base-classifier results are descriptive. No replacement is selected from the highest score.</p></section>
<section><h2>Which decisions changed?</h2><p>Both versions were correct on {t['both_correct']:,} sequences and wrong on {t['both_wrong']:,}. The 3-mer version corrected {t['k3_only_correct']} errors from the 2-mer version, while introducing {t['k2_only_correct']} errors on records the 2-mer version classified correctly. The change in accuracy is the net of these changes, not the total number of changed decisions.</p></section>
<section><h2>Validation and limits</h2><p>All 125 new fits and 125 saved control fits were audited for group/record separation and complete prediction coverage. The historical contaminated 400-record test and all new lentiMPRA outcomes were excluded. Sources, inputs, effective settings, runtime versions and feature identities were checked. New fit warnings: {sum(r['validation']['alternative']['warnings'].values())}.</p><p>The paired intervals use 2,000 whole-group resamples within the fixed outer folds, seed 20261014. They are conditional on fitted predictions and omit refitting, seed variation and parameter-selection uncertainty. Published S1 settings may already have been selected using these benchmark labels; this follows earlier inspection of the same folds. No fresh independent confirmation is claimed.</p><p>Changing feature dimensions can change model sampling and training trajectories even with a fixed seed. The result concerns this pipeline as a whole. It does not establish the exact published matrix, optimal word length, or transfer to cell-specific experimental activity. No final deployment model or serialized estimator weights were created.</p></section>
<section><h2>Next research step</h2><p>Carry both documented feature interpretations forward as evidence of the unresolved implementation choice. A stronger confirmation requires a separately specified evaluation on suitable independent examples. Linking to NEW_2026_DATA still requires verified assay processing, resolved normalization, activity targets and sequence/locus overlap checks.</p><p><a href="comparison_summary.json">Full comparison and validation</a> · <a href="model_metrics.csv">Model metrics</a> · <a href="fold_metrics.csv">Fold metrics</a> · <a href="paired_predictions.csv">Matched predictions</a> · <a href="feature_preflight.json">Feature identity audit</a> · <a href="comparison_protocol.json">Prespecified comparison</a> · <a href="artifact_manifest.json">Checksums</a></p><p>Everything remains local. No website updates, commits or pushes were made during this comparison.</p></section></main></html>''')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['preflight','summarize']);parser.add_argument('output',type=Path)
    args=parser.parse_args();globals()[args.mode](args.output.resolve())
