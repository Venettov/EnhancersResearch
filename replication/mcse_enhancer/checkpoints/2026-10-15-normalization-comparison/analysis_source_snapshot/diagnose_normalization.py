"""Post-result repeatability probe; four fixed MLP fits, no metric-driven selection.

Uses outer fold 0 by rule, not the fold with the largest observed difference.
Primary benchmark predictions and its inference are never changed.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import numpy as np
from common import HERE, sha256, write_json, write_csv
from feature_matrix import load_matrix as load_ilearn
from normalization_features import load_matrix as load_paper, VARIANT
from models import make_model, reported_parameters
from evaluation import fitted_prediction
from compare_normalization import probability_diagnostics


def run():
    output=HERE/'output/2026-10-15-normalization-repeatability'
    if output.exists():raise ValueError('Preserve the existing diagnostic')
    output.mkdir()
    spec={'created_before_diagnostic_fits_utc':datetime.now(timezone.utc).isoformat(),
        'stage':'Post-result diagnostic; not prespecified primary inference',
        'reason':'Five tree bases gave identical predictions but MLP changed despite nearly identical standardized features.',
        'fold':0,'fold_selection':'First outer fold by fixed rule, not largest difference',
        'runs':['ilearn_1','ilearn_2','paper_1','paper_2'],'expected_fits':4,
        'fixed':'Same S1 MLP, seed, train-only StandardScaler, records, groups, software and threads; no tuning',
        'comparisons':'Repeat versus repeat, and each repeat versus its saved benchmark full-fit MLP predictions',
        'limits':'One fold and process; this can detect repeatability problems but cannot establish their complete cause or general stability.',
        'primary_results_unchanged':True,'source_sha256':sha256(Path(__file__))}
    write_json(output/'protocol.json',spec)
    shutil.copyfile(__file__,output/'diagnose_normalization.py')
    a,y,g,ids,names,rows=load_ilearn('k3_full')
    b,yb,gb,idb,nb,rb=load_paper(VARIANT)
    for c,d in [(y,yb),(g,gb),(ids,idb),(names,nb)]:np.testing.assert_array_equal(c,d)
    assert rows==rb
    fold=np.array([int(r['outer_fold']) for r in rows]);tr=np.flatnonzero(fold!=0);te=np.flatnonzero(fold==0)
    estimator=make_model('MLP',reported_parameters()['MLP'],seed=20261014,scale_mlp=True)
    audit=[];predictions={}
    for tag,x in [('ilearn',a),('paper',b)]:
        for repeat in [1,2]:
            key=f'{tag}_{repeat}'
            predictions[key]=fitted_prediction(estimator,x[tr],y[tr],g[tr],ids[tr],x[te],g[te],ids[te],stage=key,audit=audit)
            print('Completed repeatability fit',key,flush=True)
    comparisons=[]
    for tag,folder in [('ilearn','2026-10-14-benchmark-k3-full'),('paper','2026-10-15-benchmark-k3-paperL')]:
        with np.load(HERE/'output'/folder/'fold_0_predictions.npz',allow_pickle=False) as saved:
            np.testing.assert_array_equal(saved['record_ids'],ids[te])
            reference=saved['prediction_features'][:,5]
        comparisons.append({'comparison':tag+'_repeat_1_vs_2',**probability_diagnostics(predictions[tag+'_1'],predictions[tag+'_2'])})
        for repeat in [1,2]:
            comparisons.append({'comparison':f'{tag}_saved_vs_repeat_{repeat}',**probability_diagnostics(reference,predictions[f'{tag}_{repeat}'])})
    comparisons.append({'comparison':'ilearn_1_vs_paper_1',**probability_diagnostics(predictions['ilearn_1'],predictions['paper_1'])})
    write_json(output/'fit_audits.json',audit)
    write_csv(output/'predictions.csv',[{'record_id':str(ids[i]),'group_id':str(g[i]),'outer_fold':0,**{tag:float(p[j]) for tag,p in predictions.items()}} for j,i in enumerate(te)])
    result={'status':'complete','fits':4,'warnings':sum(len(e['warnings']) for e in audit),'held_out_rows':len(te),'comparisons':comparisons,'limits':spec['limits'],'primary_results_unchanged':True}
    write_json(output/'summary.json',result)
    write_json(output/'artifact_manifest.json',{p.name:sha256(p) for p in sorted(output.iterdir()) if p.is_file()})
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()
