#!/usr/bin/env python3
"""Local, prediction-free feasibility audit. Never certifies independence by itself.

Reads pinned metadata and sequence sources. It does not import a model, download
resources, fit, predict, or inspect any model/experimental-outcome association.
The output manifest is preliminary and must not be used as an evaluation set.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import html
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rc(s):
    return s.translate(str.maketrans('ACGT','TGCA'))[::-1]

def windows(length, width=200, stride=50):
    if length < width:
        raise ValueError('Short fragments must not be padded')
    return sorted(set(range(0, length-width+1, stride)) | {length-width})

def coordinate(value):
    m = re.fullmatch(r'(chr(?:[0-9]+|X|Y)):([0-9]+)-([0-9]+)', value)
    if not m or int(m[2]) < 1 or int(m[3]) < int(m[2]):
        raise ValueError('Expected a standard-chromosome, one-based inclusive VISTA interval')
    return m[1], int(m[2])-1, int(m[3])

def qc(row, beds):
    seq, ref = row['seq'].upper(), row['seq_hg38'].upper()
    if not seq or set(seq)-set('ACGT') or set(ref)-set('ACGT'):
        return 'ambiguous_or_missing_sequence'
    if len(seq) < 200:
        return 'shorter_than_200'
    if seq not in (ref, rc(ref)):
        return 'tested_reference_sequence_mismatch'
    try:
        interval = coordinate(row['coordinate_hg38'])
        original = coordinate(row['coord'])
    except ValueError:
        return 'unresolved_coordinate'
    if interval != original or interval[2]-interval[1] != len(ref):
        return 'coordinate_sequence_length_mismatch'
    if interval not in beds.get(row['vista_id'], set()):
        return 'coordinate_bed_mismatch'
    return None

def legacy_index(rows):
    index = defaultdict(set)
    for row in rows:
        s=row['sequence'].upper()
        if len(s)!=200 or set(s)-set('ACGT') or hashlib.sha256(s.encode()).hexdigest()!=row['sequence_sha256']:
            raise ValueError('Invalid legacy sequence/hash')
        rid=row['file']+':'+row['row_1_based']
        for key in (s,rc(s)):
            index[key].add(rid)
    return index

def exact_hits(sequence, index):
    # All possible positions, not just the future prediction-window stride.
    hits=set()
    for pos in range(len(sequence)-199):
        hits.update(index.get(sequence[pos:pos+200], ()))
    return sorted(hits)

def write_csv(path, fields, rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)

def run(output):
    protocol=json.loads((HERE/'protocol.json').read_text())
    for path, expected in protocol['input_sha256'].items():
        if sha(ROOT/path)!=expected:
            raise ValueError('Pinned input changed: '+path)
    # Verify old preparation receipts as well as the current design pin.
    prep=ROOT/'replication/ienhancer_2l/output/2026-10-13-preparation'
    receipt=json.loads((ROOT/'replication/ienhancer_2l/checkpoints/2026-10-13-data-preparation.json').read_text())
    legacy=[]
    for name,n in [('benchmark.csv',2968),('legacy_test_diagnostic_only.csv',400)]:
        if sha(prep/name)!=receipt['data_audit']['output_sha256'][name]:
            raise ValueError('Legacy preparation receipt mismatch')
        with (prep/name).open() as f:rows=list(csv.DictReader(f))
        if len(rows)!=n:raise ValueError('Legacy row count mismatch')
        legacy.extend(rows)
    index=legacy_index(legacy)
    vista=ROOT/'NEW_2026_DATA/04_VISTA'
    beds=defaultdict(set)
    with (vista/'locus_ucsc_hg38.bed').open() as f:
        for line in f:
            c,s,e,name,*_=line.rstrip('\n').split('\t');beds[name].add((c,int(s),int(e)))
    with gzip.open(vista/'experiments.tsv.gz','rt') as f:allrows=list(csv.DictReader(f,delimiter='\t'))
    current=allrows;flow=[]
    for field,value in protocol['candidate_source']['filters'].items():
        accepted=value if isinstance(value,list) else [value]
        previous=len(current);current=[r for r in current if r[field] in accepted]
        flow.append({'filter':field,'allowed':accepted,'before':previous,'after':len(current)})
    excluded=[];by_locus=defaultdict(list)
    for row in current:
        reason=qc(row,beds)
        if reason:excluded.append({'exp_hier':row['exp_hier'],'vista_id':row['vista_id'],'reason':reason,'legacy_matches':''})
        else:by_locus[row['vista_id']].append(row)
    candidates=[];collapsed=0
    for vid,rows in sorted(by_locus.items()):
        identities={(r['seq_hg38'].upper(),r['coordinate_hg38'],r['curation_status']) for r in rows}
        if len(identities)!=1:
            for r in rows:excluded.append({'exp_hier':r['exp_hier'],'vista_id':vid,'reason':'conflicting_reference_experiments','legacy_matches':''})
            continue
        row=min(rows,key=lambda r:r['exp_hier']);collapsed+=len(rows)-1
        s=row['seq_hg38'].upper();hits=exact_hits(s,index)
        if hits:
            excluded.append({'exp_hier':row['exp_hier'],'vista_id':vid,'reason':'exact_legacy_substring_either_strand','legacy_matches':';'.join(hits)})
            continue
        c,start,end=coordinate(row['coordinate_hg38'])
        candidates.append({'vista_id':vid,'exp_hier':row['exp_hier'],'source_experiments':';'.join(sorted(r['exp_hier'] for r in rows)),'chrom':c,'start_0based':start,'end_exclusive':end,'length':len(s),'windows_200_stride50':len(windows(len(s))),'sequence_sha256':hashlib.sha256(s.encode()).hexdigest(),'reference_orientation':'genomic_forward','source_assay_strand':row['strand'],'label':int(row['curation_status']=='positive'),'status':'preliminary_not_independence_certified'})
    counts=Counter(r['label'] for r in candidates)
    summary={
        'protocol_id':protocol['protocol_id'],'protocol_sha256':sha(HERE/'protocol.json'),'created_utc':datetime.now(timezone.utc).isoformat(),
        'status':'design_and_preliminary_metadata_audit_complete; independent_cohort_not_ready',
        'audit_scope':'Metadata, curated-label counts, source sequences and exact legacy overlaps only. No model scores or score/label associations. Labels were accessible; this is not blinded third-party validation.',
        'pinned_inputs_verified':len(protocol['input_sha256']),'source_rows':len(allrows),'filters':flow,
        'metadata_eligible_rows':len(current),'excluded_rows':len(excluded),'excluded_by_reason':dict(Counter(r['reason'] for r in excluded)),'agreeing_repeats_collapsed':collapsed,
        'preliminary_fragments':len(candidates),'preliminary_positive_fragments':counts[1],'preliminary_negative_fragments':counts[0],
        'preliminary_window_count':sum(r['windows_200_stride50'] for r in candidates),'fragment_length_range':[min(r['length'] for r in candidates),max(r['length'] for r in candidates)] if candidates else [],
        'legacy_records_screened':len(legacy),'exact_screen':'Every contiguous 200-base candidate substring against all legacy sequences and reverse complements; no near-sequence or cross-assembly claims.',
        'gates':{name:('passed_source_hashes' if name=='source_integrity' else 'preliminary_pass_for_listed_fragments' if name=='metadata_and_reference_sequence_qc' else 'partial_exact_only_near_screen_pending' if name=='exact_and_near_sequence_screen' else 'pending') for name in protocol['gates_required_before_scoring']},
        'independent_group_count':None,'precision_gate_passed':False,'final_model_available':False,'model_fits':0,'predictions':0,'external_metrics':None,'lentiMPRA_outcomes_read':False,
        'next_action':'Complete cross-assembly and near-sequence/family screening, plus the lentiMPRA design reserve, before freezing the external cohort. Do not train or score from this preliminary manifest.',
        'provenance_note':'Only current source-byte hashes and the already saved preparation receipts are rechecked here; this is not a full 109-resource re-audit.'
    }
    output.mkdir(parents=True,exist_ok=False)
    write_csv(output/'preliminary_candidates.csv',list(candidates[0]) if candidates else ['vista_id','status'],candidates)
    write_csv(output/'excluded_records.csv',['exp_hier','vista_id','reason','legacy_matches'],excluded)
    (output/'readiness.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    shutil_free_copy=(HERE/'protocol.json').read_bytes()
    (output/'protocol.json').write_bytes(shutil_free_copy)
    digest_files={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    (output/'manifest.json').write_text(json.dumps({'protocol_sha256':sha(HERE/'protocol.json'),'audit_source_sha256':sha(Path(__file__)),'files':digest_files},indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','preliminary_fragments','preliminary_positive_fragments','preliminary_negative_fragments','excluded_by_reason','model_fits','predictions','next_action']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
