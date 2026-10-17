"""Plan or run all five grouped folds using reported S1 parameters.

Reported-parameter diagnostics only; this does not recover the unique published
pipeline or independently reselect parameters. Default mode writes a plan.
"""
import argparse
import json
import platform
import shutil
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score, matthews_corrcoef
from common import HERE, sha256, write_json, write_csv
from evaluation import predict_stack
from feature_matrix import VARIANTS, load_matrix
from models import make_model, reported_parameters


class ProgressAudit(list):
    """Persist each completed event without changing the evaluation algorithm."""
    def __init__(self, output, fold):
        super().__init__()
        self.output=output;self.fold=fold;self.started=time.monotonic()

    def append(self, event):
        super().append(event)
        with (self.output/f'fold_{self.fold}_events.jsonl').open('a') as handle:
            handle.write(json.dumps(event)+'\n')
        if event['kind']=='fit':
            print(f"fold {self.fold+1}/5 completed {event['stage']} "
                  f"({time.monotonic()-self.started:.1f}s elapsed; "
                  f"{len(event['warnings'])} warnings)",flush=True)


def run(variant,mode,output):
    output=Path(output)
    if output.exists():raise ValueError('Output must be new')
    x,y,groups,ids,names,rows=load_matrix(variant)
    protocol=json.loads((HERE/'repair_protocol.json').read_text())
    outer=np.array([int(r['outer_fold']) for r in rows])
    plan={'mode':mode,'created_utc':datetime.now(timezone.utc).isoformat(),
          'interpretation':'Reported-parameter diagnostic; not independent retuning or an exact published reproduction',
          'feature_variant':variant,'feature_shape':list(x.shape),'historical_test_loaded':False,
          'protocol_sha256':sha256(HERE/'repair_protocol.json'),'settings_sha256':sha256(HERE/'model_settings.json'),
          'folds':[{'fold':i,'train':int(sum(outer!=i)),'test':int(sum(outer==i)),
                    'train_groups':len(set(groups[outer!=i])),'test_groups':len(set(groups[outer==i]))} for i in range(5)]}
    output.mkdir(parents=True);write_json(output/'plan.json',plan)
    if mode=='plan':
        print(json.dumps(plan,indent=2));return
    params=reported_parameters();order=protocol['architecture']['base_order']
    models={n:[make_model(n,params[n],seed=protocol['runtime_choices']['seed'],scale_mlp=True)] for n in order}
    meta=make_model('CB',params['CB'],seed=protocol['runtime_choices']['seed'],scale_mlp=True)
    # Freeze executable sources, defaults, features and inputs before any fit.
    source_dir=output/'source_snapshot';source_dir.mkdir()
    source_paths=list(HERE.glob('*.py'))+list(HERE.glob('*.json'))+[HERE/'requirements-repaired.txt']
    for path in source_paths:
        shutil.copyfile(path,source_dir/path.name)
    input_paths=[HERE/'output/2026-10-14-recovery/train.csv',
                 HERE/'output/2026-10-14-notebook-features/notebook_block_train.npz',
                 HERE/'output/2026-10-14-notebook-features/basic_summaries_train.npz',
                 HERE/'output/2026-10-14-ilearn-validated/ilearn_train.npz']
    write_json(output/'provenance.json',{
        'sources_sha256':{p.name:sha256(p) for p in source_paths},
        'inputs_sha256':{str(p.relative_to(HERE)):sha256(p) for p in input_paths},
        'python':platform.python_version(),'platform':platform.platform(),
        'packages':{n:version(n) for n in ['numpy','scipy','scikit-learn','lightgbm','xgboost','catboost']},
        'models_saved':False,'prediction_arrays_and_source_snapshot_saved':True})
    effective={n:estimators[0].get_params(deep=True) for n,estimators in models.items()}
    effective['meta_CB']=meta.get_params(deep=True)
    (output/'effective_parameters.json').write_text(json.dumps(effective,indent=2,default=str)+'\n')
    write_json(output/'feature_names.json',names.tolist())
    started=time.monotonic()
    predictions=np.full(len(y),np.nan)
    for fold in range(5):
        train=np.flatnonzero(outer!=fold);test=np.flatnonzero(outer==fold)
        inner=np.array([int(rows[i][f'inner_fold_outer_{fold}']) for i in train])
        splits=[(np.flatnonzero(inner!=j),np.flatnonzero(inner==j)) for j in range(3)]
        audit=ProgressAudit(output,fold)
        print(f'Starting fold {fold+1}/5: {len(train)} training; {len(test)} held-out rows',flush=True)
        try:
            r=predict_stack(x[train],y[train],groups[train],ids[train],x[test],groups[test],ids[test],
                            models,meta,crossfit_splits=splits,seed=protocol['runtime_choices']['seed'],audit=audit)
        except Exception as e:
            write_json(output/f'fold_{fold}_failure.json',{'error':str(e),'audit':audit})
            raise
        predictions[test]=r['probability'];write_json(output/f'fold_{fold}_audit.json',audit)
        np.savez_compressed(output/f'fold_{fold}_predictions.npz',record_ids=ids[test],probability=r['probability'],
                            train_record_ids=ids[train],oof_features=r['oof_features'],
                            prediction_features=r['prediction_features'],base_order=np.asarray(r['base_order']))
    if not np.isfinite(predictions).all():raise ValueError('Incomplete outer-fold coverage')
    write_csv(output/'predictions.csv',[{'record_id':str(ids[i]),'outer_fold':int(outer[i]),'label':int(y[i]),'probability':float(predictions[i])} for i in range(len(y))])
    metrics={'interpretation':plan['interpretation'],'accuracy':float(accuracy_score(y,predictions>=.5)),
             'auroc':float(roc_auc_score(y,predictions)),'mcc':float(matthews_corrcoef(y,predictions>=.5)),
             'elapsed_seconds':time.monotonic()-started}
    write_json(output/'metrics.json',metrics);print(json.dumps(metrics,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',required=True,choices=VARIANTS)
    p.add_argument('--mode',choices=['plan','run'],default='plan')
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();run(a.variant,a.mode,a.output)
