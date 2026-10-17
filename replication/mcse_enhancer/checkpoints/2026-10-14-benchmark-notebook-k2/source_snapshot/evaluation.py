"""Repaired grouped CV and nested out-of-fold stacking.

This module never loads files. Prediction-set labels are deliberately absent
from its API. Candidate tuning is repeated within each cross-fit training set.
"""
import warnings
import numpy as np
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedGroupKFold


def validate_splits(y, groups, splits):
    n=len(y);seen=np.zeros(n,dtype=int);normalized=[]
    for train,valid in splits:
        train=np.asarray(train,dtype=int);valid=np.asarray(valid,dtype=int)
        if not len(train) or not len(valid):
            raise ValueError('Empty fold')
        if np.any(train<0) or np.any(valid<0) or np.any(train>=n) or np.any(valid>=n):
            raise ValueError('Fold index out of bounds')
        if len(np.unique(train))!=len(train) or len(np.unique(valid))!=len(valid):
            raise ValueError('Repeated fold index')
        if set(train)&set(valid) or set(train)|set(valid)!=set(range(n)):
            raise ValueError('Folds must partition the available training rows')
        if set(groups[train])&set(groups[valid]):
            raise ValueError('Group leakage')
        if set(y[train])!={0,1} or set(y[valid])!={0,1}:
            raise ValueError('Each partition needs both binary classes')
        seen[valid]+=1;normalized.append((train,valid))
    if len(normalized)<2 or not np.all(seen==1):
        raise ValueError('Every row must be held out exactly once')
    return normalized


def make_splits(y, groups, n_splits, seed):
    cv=StratifiedGroupKFold(n_splits=n_splits,shuffle=True,random_state=seed)
    return validate_splits(y,groups,list(cv.split(np.zeros((len(y),1)),y,groups)))


def positive_probability(model, x):
    classes=np.asarray(model.classes_)
    if len(classes)!=2 or set(classes.tolist())!={0,1}:
        raise ValueError('Expected binary classes 0 and 1')
    p=np.asarray(model.predict_proba(x),dtype=float)
    if p.shape!=(len(x),2) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Invalid class probabilities')
    if not np.allclose(p.sum(axis=1),1,atol=1e-7):
        raise ValueError('Probabilities do not sum to one')
    return p[:,int(np.flatnonzero(classes==1)[0])]


def fitted_prediction(estimator,x,y,groups,ids,x_new,new_groups,new_ids,*,stage,audit,strict_convergence=True):
    if set(groups)&set(new_groups) or set(ids)&set(new_ids):
        raise ValueError('Fit/prediction group or record overlap')
    model=clone(estimator)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model.fit(x,y)
        probability=positive_probability(model,x_new)
    messages=[{'category':w.category.__name__,'message':str(w.message)} for w in caught]
    audit.append({'kind':'fit','stage':stage,'train_ids':list(map(str,ids)),
                  'predict_ids':list(map(str,new_ids)),'train_groups':sorted(set(map(str,groups))),
                  'predict_groups':sorted(set(map(str,new_groups))),'warnings':messages})
    if strict_convergence and any(issubclass(w.category,ConvergenceWarning) for w in caught):
        raise ValueError(f'Nonconverged model at {stage}; inspect before reporting benchmark results')
    return probability


def select_candidate(x,y,groups,ids,candidates,*,seed,n_splits,audit,stage,splits=None,strict_convergence=True):
    if not candidates:
        raise ValueError('No candidate models')
    if len(candidates)==1:
        audit.append({'kind':'selection','stage':stage,'policy':'one fixed candidate; no tuning',
                      'training_ids':list(map(str,ids)),'selected':0})
        return clone(candidates[0])
    splits=make_splits(y,groups,n_splits,seed) if splits is None else validate_splits(y,groups,splits)
    scores=[]
    for candidate_index,estimator in enumerate(candidates):
        fold_scores=[]
        for fold,(train,valid) in enumerate(splits):
            p=fitted_prediction(estimator,x[train],y[train],groups[train],ids[train],
                                x[valid],groups[valid],ids[valid],stage=f'{stage}/candidate{candidate_index}/fold{fold}',
                                audit=audit,strict_convergence=strict_convergence)
            fold_scores.append(float(accuracy_score(y[valid],p>=0.5)))
        scores.append(fold_scores)
    winner=int(np.argmax(np.mean(scores,axis=1)))
    audit.append({'kind':'selection','stage':stage,'policy':'mean of all fold accuracies; first candidate breaks ties',
                  'training_ids':list(map(str,ids)),'fold_scores':scores,'selected':winner})
    return clone(candidates[winner])


def predict_stack(x,y,groups,ids,x_new,new_groups,new_ids,candidates,meta_estimator,*,
                  seed=20261014,n_splits=3,crossfit_splits=None,passthrough=False,
                  audit=None,strict_convergence=True):
    """Fit on x/y only. Meta settings and architecture must be fixed in advance.

    Hyperparameter selection for an OOF base prediction sees only that OOF
    fold's training rows. A separately tuned full-training refit predicts x_new.
    Selecting meta settings requires additional nesting of the ENTIRE stack;
    searching a precomputed OOF matrix is intentionally not implemented here.
    """
    x=np.asarray(x);y=np.asarray(y);groups=np.asarray(groups);ids=np.asarray(ids)
    x_new=np.asarray(x_new);new_groups=np.asarray(new_groups);new_ids=np.asarray(new_ids)
    if x.ndim!=2 or x_new.ndim!=2 or x.shape[1]!=x_new.shape[1] or not np.isfinite(x).all() or not np.isfinite(x_new).all():
        raise ValueError('Invalid feature matrices')
    if not len(x_new) or not (len(x)==len(y)==len(groups)==len(ids)) or not (len(x_new)==len(new_ids)==len(new_groups)):
        raise ValueError('Row identity/label length mismatch')
    if set(y)!={0,1} or len(set(ids))!=len(ids) or len(set(new_ids))!=len(new_ids):
        raise ValueError('Invalid labels or duplicate row IDs')
    if set(groups)&set(new_groups) or set(ids)&set(new_ids):
        raise ValueError('Outer prediction groups overlap training')
    if not candidates:
        raise ValueError('No base models')
    if audit is None:
        audit=[]
    splits=make_splits(y,groups,n_splits,seed) if crossfit_splits is None else validate_splits(y,groups,crossfit_splits)
    names=list(candidates);z=np.full((len(y),len(names)),np.nan);z_new=np.full((len(x_new),len(names)),np.nan)
    for column,name in enumerate(names):
        for fold,(train,valid) in enumerate(splits):
            stage=f'{name}/oof{fold}'
            selected=select_candidate(x[train],y[train],groups[train],ids[train],candidates[name],
                                      seed=seed+fold,n_splits=n_splits,audit=audit,stage=f'{stage}/tune',strict_convergence=strict_convergence)
            z[valid,column]=fitted_prediction(selected,x[train],y[train],groups[train],ids[train],
                x[valid],groups[valid],ids[valid],stage=f'{stage}/predict',audit=audit,strict_convergence=strict_convergence)
        selected=select_candidate(x,y,groups,ids,candidates[name],seed=seed,n_splits=n_splits,
                                  audit=audit,stage=f'{name}/full/tune',splits=splits,strict_convergence=strict_convergence)
        z_new[:,column]=fitted_prediction(selected,x,y,groups,ids,x_new,new_groups,new_ids,
            stage=f'{name}/full/predict',audit=audit,strict_convergence=strict_convergence)
    if not np.isfinite(z).all() or not np.isfinite(z_new).all():
        raise ValueError('Incomplete out-of-fold predictions')
    meta_x=np.column_stack([z,x]) if passthrough else z
    meta_new=np.column_stack([z_new,x_new]) if passthrough else z_new
    p=fitted_prediction(meta_estimator,meta_x,y,groups,ids,meta_new,new_groups,new_ids,
                        stage='meta/fixed',audit=audit,strict_convergence=strict_convergence)
    return {'probability':p,'oof_features':z,'prediction_features':z_new,'base_order':names,'audit':audit}
