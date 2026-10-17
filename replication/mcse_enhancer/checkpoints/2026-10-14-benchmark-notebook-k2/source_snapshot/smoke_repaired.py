"""Exercise all six S1 models and a full stack on synthetic data only."""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import time
import numpy as np
from common import HERE, sha256, write_json
from evaluation import fitted_prediction, predict_stack
from models import make_model, reported_parameters


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();rng=np.random.default_rng(20261014)
    groups=np.repeat(np.arange(30),4);y=np.repeat(np.arange(30)%2,4)
    x=rng.normal(size=(120,8));x[:,0]+=1.5*y
    ids=np.array([f'synthetic:{i}' for i in range(120)])
    train=np.arange(96);test=np.arange(96,120)
    p=reported_parameters();order=['RF','XGB','LGBM','CB','ET','MLP']
    estimators={name:make_model(name,p[name],seed=20261014,scale_mlp=True) for name in order}
    audit=[];checks={}
    for name,model in estimators.items():
        result=fitted_prediction(model,x[train],y[train],groups[train],ids[train],x[test],groups[test],ids[test],
                                 stage=f'single/{name}',audit=audit,strict_convergence=False)
        checks[name]={'finite_probabilities':bool(np.isfinite(result).all()),'parameters':model.get_params(deep=False)}
    result=predict_stack(x[train],y[train],groups[train],ids[train],x[test],groups[test],ids[test],
        {name:[model] for name,model in estimators.items()},estimators['CB'],audit=audit,strict_convergence=False)
    warning_counts=Counter(w['category'] for e in audit if e['kind']=='fit' for w in e['warnings'])
    record={'status':'Synthetic software smoke test; no enhancer benchmark metrics',
            'synthetic_train_rows':96,'synthetic_prediction_rows':24,'real_benchmark_rows_used':0,
            'all_six_s1_classifiers_fit':checks,'stack_oof_shape':list(result['oof_features'].shape),
            'stack_prediction_shape':list(result['probability'].shape),
            'fits':sum(e['kind']=='fit' for e in audit),'warning_counts':dict(warning_counts),
            'strict_convergence_disabled_for_synthetic_compatibility_check_only':True,
            'real_evaluation_strict_convergence':True,'elapsed_seconds':time.monotonic()-started,
            'model_settings_sha256':sha256(HERE/'model_settings.json'),'python':platform.python_version(),
            'audit':audit}
    # Estimator repr in effective settings is diagnostic, not a reloadable model.
    (output/'smoke.json').write_text(json.dumps(record,indent=2,default=str)+'\n')
    print(json.dumps({k:record[k] for k in ['status','fits','stack_oof_shape','stack_prediction_shape','warning_counts','elapsed_seconds']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
