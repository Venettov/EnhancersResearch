"""Factories for the six reported classifiers, with explicit runtime choices."""
import json
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from common import HERE, check_file


def reported_parameters():
    record=json.loads((HERE/'model_settings.json').read_text())
    check_file(HERE/record['source']['file'],record['source']['sha256'])
    return record['reported_parameters']


def make_model(name, parameters, *, seed, scale_mlp):
    """No early-stopping/eval_set receives held-out labels; one CPU thread."""
    p=dict(parameters)
    if any(k != k.strip() for k in p):
        raise ValueError('Parameter names contain whitespace; repair before use')
    if p.get('max_features')=='auto':
        raise ValueError('Resolve deprecated max_features=auto explicitly')
    if name=='RF':
        model=RandomForestClassifier(**p,random_state=seed,n_jobs=1)
    elif name=='ET':
        model=ExtraTreesClassifier(**p,random_state=seed,n_jobs=1)
    elif name=='MLP':
        p['hidden_layer_sizes']=tuple(p['hidden_layer_sizes'])
        # S1 gives no iteration budget. Use an explicit larger cap and still
        # reject ConvergenceWarning in benchmark evaluation; never assume it converged.
        p.setdefault('max_iter',2000)
        model=MLPClassifier(**p,random_state=seed,early_stopping=False)
        if scale_mlp:
            model=Pipeline([('scale',StandardScaler()),('model',model)])
    elif name=='LGBM':
        from lightgbm import LGBMClassifier
        # Keep subsample_freq=0, the library default; S1 does not supply it.
        model=LGBMClassifier(**p,random_state=seed,n_jobs=1,verbosity=-1)
    elif name=='XGB':
        from xgboost import XGBClassifier
        model=XGBClassifier(**p,random_state=seed,n_jobs=1,objective='binary:logistic',eval_metric='logloss')
    elif name=='CB':
        from catboost import CatBoostClassifier
        model=CatBoostClassifier(**p,random_seed=seed,thread_count=1,verbose=False,allow_writing_files=False,loss_function='Logloss')
    else:
        raise ValueError(f'Unknown classifier: {name}')
    return model
