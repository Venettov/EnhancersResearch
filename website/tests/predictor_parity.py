#!/usr/bin/env python3
"""Check real browser-engine inference against frozen Python models and responses.

Requires the existing research environment and a Node executable (no Node packages).
Writes a compact validation receipt only when explicitly given --output.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "replication/ienhancer_2l"))
from features import pseknc, property_table
from predict_svm import predict_records, DEFAULT_MODELS
from prepare_data import fasta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default='node')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = ROOT / 'website/data'
    manifest = json.loads((data / 'predictor_manifest.json').read_text())
    payload = (data / manifest['file']).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == manifest['sha256']
    exported = json.loads(gzip.decompress(payload))
    np.testing.assert_array_equal(exported['properties'], property_table())
    for relative, digest in manifest['source_models'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    # Check every exported support-vector value, not only prediction outcomes.
    for model in exported['layers']:
        with np.load(DEFAULT_MODELS / (model['name'] + '_final.npz'), allow_pickle=False) as original:
            restored = np.zeros_like(original['support_vectors'])
            for column in range(4096):
                start, end = model['columnOffsets'][column:column+2]
                restored[model['rowIndices'][start:end], column] = model['values'][start:end]
            restored[:,4096:] = np.asarray(model['structure']).reshape(-1,9)
            np.testing.assert_array_equal(restored, original['support_vectors'])
            np.testing.assert_array_equal(model['dual'], original['dual_coef'])
            assert model['gamma'] == float(original['gamma'])
            assert model['intercept'] == float(original['intercept'])
    records = fasta(data / 'ienhancer_2l_server_200_queries.fasta')
    rng = random.Random(20261027)
    edges = [(f'homopolymer_{base}', base * 200) for base in 'ACGT']
    edges += [('repeat_ACGT', 'ACGT' * 50), ('repeat_AT', 'AT' * 100)]
    edges += [(f'random_{i}', ''.join(rng.choices('ACGT', k=200))) for i in range(10)]
    records += edges
    expected = predict_records(records)
    script = r'''
const fs=require('node:fs'), zlib=require('node:zlib'), assert=require('node:assert/strict');
const engine=require(process.argv[1]);
const model=JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[2])));
const records=JSON.parse(fs.readFileSync(process.argv[3]));
const first=records[0][1];
assert.equal(engine.parseFasta('\ufeff>same\r\n'+first.slice(0,100).toLowerCase()+'\r\n'+first.slice(100)+'\r\n>same\n'+first).length,2);
for(const [input,code] of [['','empty'],[first,'format'],['>\n'+first,'header'],['>x\nACGT','length'],['>x\n'+first.slice(1)+'N','alphabet'],['>x\n'+first+'A','length'],[('>x\n'+first+'\n').repeat(1001),'tooMany'],['a'.repeat(1048577),'tooLarge']])
 assert.throws(()=>engine.parseFasta(input), e=>e.code===code,code);
const csv=engine.toCsv([{header:'=SUM(1,2)',enhancer_decision_score:-0.4}], 'v1');
assert(csv.includes('"\'=SUM(1,2)"'));assert(csv.includes('"-0.4"'));
const output=records.map(([header,sequence])=>({header,...engine.predict(sequence,model)}));
const featureRows=records.slice(-16).map(([,seq])=>{
 const p=engine.components(seq,model.properties);let total=0;
 for(const value of p.frequencies)total+=value;for(const value of p.theta)total+=0.1*value;
 return [...p.frequencies].map(v=>v/total).concat([...p.theta].map(v=>0.1*v/total));
});
process.stdout.write(JSON.stringify({output,featureRows}));
'''
    with tempfile.TemporaryDirectory() as temporary:
        fixture = Path(temporary) / 'records.json'
        fixture.write_text(json.dumps(records))
        result = subprocess.run([args.node, '-e', script, str(ROOT/'website/assets/predictor-engine.js'),
                                 str(data/manifest['file']), str(fixture)], check=True, capture_output=True, text=True)
    actual = json.loads(result.stdout)
    np.testing.assert_allclose(actual['featureRows'], [pseknc(sequence) for _, sequence in edges], atol=1e-14, rtol=0)
    maximum_error = 0.0
    for a,b in zip(actual['output'], expected, strict=True):
        assert a['predicted_class'] == b['predicted_class'], a['header']
        for key in ('enhancer_decision_score','strength_decision_score'):
            if b[key] == '':
                assert a[key] is None
            else:
                error = abs(a[key]-b[key]);maximum_error=max(maximum_error,error)
                assert error < 1e-6, (a['header'],key,error)
    saved = list(csv.DictReader((data/'ienhancer_2l_server_200_comparison.csv').open()))
    for actual_row, saved_row in zip(actual['output'][:200],saved,strict=True):
        assert actual_row['predicted_class'] == saved_row['local_class']
        assert abs(actual_row['enhancer_decision_score']-float(saved_row['local_enhancer_score']))<1e-6
        if saved_row['local_strength_score']:
            assert abs(actual_row['strength_decision_score']-float(saved_row['local_strength_score']))<1e-6
    author_matches=sum(a['predicted_class']==b['server_class'] for a,b in zip(actual['output'],saved))
    assert author_matches == 192
    reference=json.loads((data/'predictor_reference_200.json').read_text())
    for source,copy in zip(saved,reference,strict=True):
        assert all(copy[k]==source[k] for k in copy)
    receipt={'model_version':manifest['version'],'model_sha256':manifest['sha256'],
             'browser_engine_sha256':hashlib.sha256((ROOT/'website/assets/predictor-engine.js').read_bytes()).hexdigest(),
             'input_fasta_sha256':hashlib.sha256((data/'ienhancer_2l_server_200_queries.fasta').read_bytes()).hexdigest(),
             'comparison_records':200,'additional_edge_sequences':len(edges),
             'browser_engine_python_class_matches':len(records),'maximum_absolute_score_error':maximum_error,
             'score_tolerance':1e-6,'saved_author_class_matches':author_matches,
             'exported_weights_identical':True,'feature_vectors_checked':len(edges),
             'scope':'Software parity and saved-server agreement; no model fitting or biological accuracy evaluation.',
             'checks':['all exported weights and fixed properties','FASTA validation and limits',
                       'CSV formula protection','feature parity','cascade and blank strength scores',
                       '216 Python class/score comparisons','200 frozen result rows']}
    if args.output: args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__': main()
