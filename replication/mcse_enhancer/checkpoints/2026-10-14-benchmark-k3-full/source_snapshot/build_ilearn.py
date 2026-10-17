"""Recover remaining descriptors for all training rows; no model or test fitting."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from common import HERE, check_file, read_csv, sha256, write_json
from ilearn_features import METHODS, independent, load_reference, recover


def build(prepared, output):
    prepared, output = Path(prepared), Path(output)
    if output.exists():
        raise ValueError('Output must be a new directory')
    audit = json.loads((prepared/'data_audit.json').read_text())
    check_file(prepared/'train.csv', audit['output_sha256']['train.csv'])
    rows = read_csv(prepared/'train.csv')
    fastas = [[r['record_id'], r['sequence'], '0', 'training'] for r in rows]
    started = time.monotonic()
    arrays, names = recover(fastas)
    properties = load_reference()[1]
    selected = [0,1,741,742,1483,1484,2967]
    max_errors = {}
    for method in METHODS:
        errors=[]
        for i in selected:
            expected=independent(rows[i]['sequence'], method, properties)
            np.testing.assert_allclose(arrays[method][i],expected,rtol=1e-12,atol=1e-12)
            errors.append(float(np.max(np.abs(arrays[method][i]-expected))))
        max_errors[method]=max(errors)
    output.mkdir(parents=True)
    payload={**arrays,'record_ids':np.asarray([r['record_id'] for r in rows])}
    payload.update({f'names_{k}':np.asarray(v) for k,v in names.items()})
    np.savez_compressed(output/'ilearn_train.npz',**payload)
    record={'stage':'all five external descriptor families recovered plus explicit 3-mer alternative',
            'rows':len(rows),'widths':{k:v.shape[1] for k,v in arrays.items()},
            'inputs_sha256':{'train.csv':sha256(prepared/'train.csv')},
            'sources_sha256':{p.name:sha256(p) for p in [HERE/'ilearn_source_manifest.json',HERE/'ilearn_properties.json',HERE/'ilearn_features.py',HERE/'build_ilearn.py']},
            'outputs_sha256':{'ilearn_train.npz':sha256(output/'ilearn_train.npz')},
            'independent_formula_validation_rows':selected,'max_absolute_formula_errors':max_errors,
            'numeric_features_only':True,'actual_labels_passed_to_ilearn':False,'test_rows_processed':0,
            'kmer2_default_confirmed':True,'kmer3_is_explicit_alternative':True,
            'frequency_denominator':'L-k+1 overlapping windows (not L)',
            'property_values':'Pinned upstream pre-tabulated values; no across-sample normalization',
            'elapsed_seconds':time.monotonic()-started}
    write_json(output/'ilearn_audit.json',record)
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.prepared,a.output)
