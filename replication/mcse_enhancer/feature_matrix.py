"""Explicit, identity-checked feature variants; never join by repeated FASTA names."""
import json
import numpy as np
from common import HERE, check_file, read_csv
from prepare import check_groups

VARIANTS={
    'notebook_k2_full':('Kmer2',False,15169),
    'k3_full':('Kmer3',False,15217),
    'notebook_k2_basic7':('Kmer2',True,285),
    'k3_basic7':('Kmer3',True,333),
}


def load_matrix(variant):
    if variant not in VARIANTS:
        raise ValueError('Choose an explicit feature variant')
    prepared=HERE/'output/2026-10-14-recovery'
    prior=HERE/'output/2026-10-14-notebook-features'
    ilearn=HERE/'output/2026-10-14-ilearn-validated'
    data_audit=json.loads((prepared/'data_audit.json').read_text())
    prior_audit=json.loads((prior/'features_audit.json').read_text())
    new_audit=json.loads((ilearn/'ilearn_audit.json').read_text())
    check_file(prepared/'train.csv',data_audit['output_sha256']['train.csv'])
    check_file(prepared/'train.csv',new_audit['inputs_sha256']['train.csv'])
    rows=read_csv(prepared/'train.csv');check_groups(rows)
    ids=np.asarray([r['record_id'] for r in rows])
    kmer,basic,expected=VARIANTS[variant]
    filename='basic_summaries_train.npz' if basic else 'notebook_block_train.npz'
    check_file(prior/filename,prior_audit['outputs_sha256'][filename])
    check_file(ilearn/'ilearn_train.npz',new_audit['outputs_sha256']['ilearn_train.npz'])
    with np.load(prior/filename,allow_pickle=False) as old,np.load(ilearn/'ilearn_train.npz',allow_pickle=False) as new:
        np.testing.assert_array_equal(ids,old['record_ids']);np.testing.assert_array_equal(ids,new['record_ids'])
        methods=['DCC','PseKNC','SCPseDNC','PCPseDNC',kmer]
        x=np.column_stack([*[new[k] for k in methods],old['X']])
        names=np.concatenate([*[new[f'names_{k}'] for k in methods],np.char.add('notebook:',old['feature_names'])])
    if x.shape!=(2968,expected) or len(set(names))!=expected or not np.isfinite(x).all():
        raise ValueError('Feature shape/name/finiteness failure')
    y=np.asarray([int(r['label']) for r in rows]);groups=np.asarray([r['group_id'] for r in rows])
    return x,y,groups,ids,names,rows
