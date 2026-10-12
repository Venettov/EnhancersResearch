#!/usr/bin/env python3
"""Read-only folder audit for EnhancersResearch.

Requires Python 3.10+, numpy, pandas and openpyxl. Reads original inputs,
streams archive metadata without extracting full archives, and hashes about
51 GB. Temporary dataframes are removed at exit. The only persistent output
is the explicitly requested JSON file. Does not download data or run models.

Run from the project root:
  python3 reports/assets/audit_workspace.py --output /tmp/workspace_audit.json
"""
from pathlib import Path
import argparse, collections, csv, gzip, hashlib, importlib.util, io, json, platform, sys, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'NEW_2026_DATA'
OUT = None  # Set to a temporary directory by main().

def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, default=lambda x: x.item() if hasattr(x, 'item') else str(x), allow_nan=False)+'\n')

def integrity():
    audit=json.loads((DATA/'DOWNLOAD_LOGS/download_audit.json').read_text())
    receipts={r['relative_path']: r for r in json.loads((DATA/'DOWNLOAD_LOGS/publication_receipts.json').read_text())['files']}
    def check(row):
        p=ROOT/row['path']; expected=row.get('expected_checksum',''); receipt=receipts.get(str(p.relative_to(DATA)))
        size=p.stat().st_size if p.is_file() else None
        alg='sha256' if receipt else ('md5' if len(expected.removeprefix('md5:'))==32 else 'sha256')
        digest=None
        if size is not None:
            h=hashlib.new(alg)
            with p.open('rb') as f:
                for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
            digest=h.hexdigest()
        ref=receipt['actual_sha256'] if receipt else expected.removeprefix('md5:').removeprefix('sha256:')
        status=('missing' if size is None else 'receipt_match' if receipt and digest==ref else 'reference_checksum_match' if expected and digest==ref and size==row['expected_bytes'] else 'size_match_new_local_hash' if not expected and size==row['expected_bytes'] else 'mismatch')
        return dict(path=row['path'],bytes=size,algorithm=alg,digest=digest,status=status,historical_manifest_match=False if receipt else status=='reference_checksum_match')
    with ThreadPoolExecutor(max_workers=3) as pool: files=list(pool.map(check,audit['files']))
    write('integrity.json',dict(files=files,summary=dict(resources=len(files),bytes=sum(r['bytes'] or 0 for r in files),counts=dict(collections.Counter(r['status'] for r in files))),partial_files=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*.part')]))

def legacy():
    sets={}; result={}
    for fn in ['enhancer.cv.txt','non.cv.txt','enhancer.ind.txt','non.ind.txt']:
        headers=[]; seqs=[]
        for line in (ROOT/fn).read_text().splitlines():
            if line.startswith('>'): headers.append(line[1:]); seqs.append('')
            elif line.strip(): seqs[-1]+=line.strip().upper()
        sets[fn]=seqs
        uni=fn.replace('non.','non_enhancer.').replace('.txt','.unigram.txt')
        unigram=[''.join(s.split()).upper() for s in (ROOT/uni).read_text().splitlines() if s.strip()]
        result[fn]=dict(rows=len(seqs),lengths=dict(collections.Counter(map(len,seqs))),unique_sequences=len(set(seqs)),unique_headers=len(set(headers)),non_acgt=sum(bool(set(s)-set('ACGT')) for s in seqs),unigram_rows=len(unigram),unigram_exact_order_match=seqs==unigram,gc_mean=float(np.mean([(s.count('G')+s.count('C'))/len(s) for s in seqs])))
    rc=lambda s:s.translate(str.maketrans('ACGT','TGCA'))[::-1]
    result['pairwise']=[]
    for i,(a,sa) in enumerate(sets.items()):
        for b,sb in list(sets.items())[i+1:]:
            result['pairwise'].append(dict(a=a,b=b,exact_overlap=len(set(sa)&set(sb)),reverse_complement_canonical_overlap=len({min(s,rc(s)) for s in sa}&{min(s,rc(s)) for s in sb})))
    write('legacy.json',result)

def structural():
    bed=DATA/'01_ENCODE4_SCREEN/GRCh38-cCREs.ELS.bed'
    c=collections.Counter(); widths=[]; seen=set(); invalid=duplicate=0
    for line in bed.open():
        r=line.rstrip('\n').split('\t'); c[r[-1]]+=1; a,b=int(r[1]),int(r[2]); widths.append(b-a); invalid+=a<0 or b<=a
        k=tuple(r[:3]); duplicate+=k in seen; seen.add(k)
    screen=dict(rows=len(widths),classes=dict(c),invalid_intervals=invalid,duplicate_intervals=duplicate,width_quantiles=dict(zip(['min','p25','median','p75','max'],map(float,np.quantile(widths,[0,.25,.5,.75,1])))))
    exp=pd.read_csv(DATA/'04_VISTA/experiments.tsv.gz',sep='\t',keep_default_na=False)
    loc=pd.read_csv(DATA/'04_VISTA/locus.tsv.gz',sep='\t',keep_default_na=False)
    absent=exp[~exp.vista_id.isin(loc.vista_id)]
    vista=dict(experiment_rows=len(exp),locus_rows=len(loc),experiment_ids=exp.vista_id.nunique(),duplicate_exp_hier=int(exp.exp_hier.duplicated().sum()),duplicate_locus_ids=int(loc.vista_id.duplicated().sum()),experiment_status=exp.curation_status.value_counts().to_dict(),missing_locus_ids=sorted(set(exp.vista_id)-set(loc.vista_id)),missing_locus_rows=len(absent),missing_locus_status=absent.curation_status.value_counts().to_dict(),loci_without_experiment=sorted(set(loc.vista_id)-set(exp.vista_id)),organisms=exp.organism.value_counts().to_dict(),assemblies=exp.assembly.value_counts().to_dict())
    write('structural.json',dict(screen=screen,vista=vista))

def lenti():
    cols=['condition','replicate','name','dna_count','rna_count','ratio','log2','n_obs_bc']; entries=[]; frames={}
    for p in sorted((DATA/'02_LENTIMPRA_ENCODE_2025').glob('ENCSR*/*.tsv')):
        with p.open() as f: header=f.readline().startswith('condition\t')
        d=pd.read_csv(p,sep='\t',header=0 if header else None,names=cols)
        frames[str(p.relative_to(DATA))]=d
        numeric=d[cols[3:]].apply(pd.to_numeric,errors='coerce')
        entries.append(dict(path=str(p.relative_to(DATA)),header=header,rows=len(d),conditions=d.condition.value_counts().to_dict(),replicates=d.replicate.value_counts().to_dict(),unique_names=d.name.nunique(),duplicate_keys=int(d.duplicated(['condition','replicate','name']).sum()),missing_numeric=numeric.isna().sum().to_dict(),nonfinite_numeric=(~np.isfinite(numeric)).sum().to_dict(),barcode_quantiles=dict(zip(['min','median','max'],map(float,numeric.n_obs_bc.quantile([0,.5,1]))))))
    pd.to_pickle(frames,OUT/'lenti_frames.pkl')
    summaries=[]
    for acc in sorted({Path(k).parts[1] for k in frames}):
        f=[(k,d) for k,d in frames.items() if Path(k).parts[1]==acc]
        merged=pd.concat([d for k,d in f]); independent=merged.drop_duplicates()
        replicate_sets={str(r):set(g.name) for r,g in independent.groupby('replicate')}
        summaries.append(dict(accession=acc,cells=sorted(merged.condition.unique()),total_rows=len(merged),unique_full_rows=len(independent),duplicated_full_rows=int(merged.duplicated().sum()),unique_names=merged.name.nunique(),replicate_rows=independent.replicate.value_counts().to_dict(),all_replicates_names=len(set.intersection(*replicate_sets.values()))))
    write('lenti.json',dict(files=entries,experiments=summaries))

def joint():
    p=DATA/'02_LENTIMPRA_ENCODE_2025/SUPPLEMENTARY/lentiMPRA_supplementary_tables_1-13.zip'
    with zipfile.ZipFile(p) as z:
        design_n=next(n for n in z.namelist() if 'Table S10 ' in n)
        activity_n=next(n for n in z.namelist() if 'Table S11 ' in n)
        design=pd.read_excel(io.BytesIO(z.read(design_n)),header=1,keep_default_na=False)
        activity=pd.read_excel(io.BytesIO(z.read(activity_n)),sheet_name=None)
    pd.to_pickle(dict(design=design,activity=activity),OUT/'joint_frames.pkl')
    seq=design.iloc[:,-1]; inserts=seq.str[15:-15]; rc=lambda s:s.translate(str.maketrans('ACGT','TGCA'))[::-1]
    canon=inserts.map(lambda s:min(s,rc(s)))
    result=dict(design=dict(rows=len(design),duplicate_names=int(design.name.duplicated().sum()),categories=design.category.value_counts().to_dict(),sequence_lengths=seq.str.len().value_counts().to_dict(),insert_lengths=inserts.str.len().value_counts().to_dict(),duplicate_insert_excess=int(inserts.duplicated().sum()),duplicate_canonical_insert_excess=int(canon.duplicated().sum()),non_acgt=int(inserts.str.contains('[^ACGT]').sum()),prefixes=seq.str[:15].value_counts().to_dict(),suffixes=seq.str[-15:].value_counts().to_dict()),sheets={})
    for n,d in activity.items():
        result['sheets'][n]=dict(rows=len(d),columns=list(d.columns),unique_names=d.name.nunique(),duplicate_names=int(d.name.duplicated().sum()),unmatched_design_names=sorted(set(d.name)-set(design.name)),missing_by_column=d.isna().sum().to_dict())
    summary=activity['all_cell_types_summary']; ess=activity['all_cell_types_ESS']
    result['joint_summary']=dict(missing_values=summary.isna().sum().to_dict(),complete_three_cells=int(summary.iloc[:,1:].notna().all(axis=1).sum()),missing_design_count=len(set(design.name)-set(summary.name)),missing_categories=design[~design.name.isin(summary.name)].category.value_counts().to_dict(),included_categories=design[design.name.isin(summary.name)].category.value_counts().to_dict(),pearson=summary.iloc[:,1:].corr().to_dict(),ess_not_summary=len(set(ess.name)-set(summary.name)),summary_not_ess=len(set(summary.name)-set(ess.name)),summary_not_ess_categories=design[design.name.isin(set(summary.name)-set(ess.name))].category.value_counts().to_dict(),ess_types=ess.type.value_counts().to_dict())
    result['cell_qc']={}
    for cell in ['HepG2','K562','WTC11']:
        r=activity[cell+'_replicate_level'].iloc[:,:7]; s=activity[cell+'_summary_data']
        r.columns=['replicate','name','dna','rna','ratio','log2','barcodes']
        matrix=r.pivot(index='name',columns='replicate',values='log2')
        means=matrix.mean(axis=1); check=s.set_index('name')['mean']-means
        summary_vs_cell=summary.set_index('name')[cell+' [log2(rna/dna)]']-s.set_index('name')['mean']
        result['cell_qc'][cell]=dict(rows=len(r),duplicate_keys=int(r.duplicated(['replicate','name']).sum()),per_replicate=r.replicate.value_counts().to_dict(),names_in_all_three=int(matrix.notna().all(axis=1).sum()),names_one_or_two=int((matrix.notna().sum(axis=1)<3).sum()),replicate_correlations=matrix.corr().to_dict(),barcodes_quantiles=dict(zip(['min','p05','median','max'],map(float,r.barcodes.quantile([0,.05,.5,1])))),missing_numeric=r.iloc[:,2:].isna().sum().to_dict(),mean_max_absolute_difference=float(check.abs().max()),joint_vs_cell_max_absolute_difference=float(summary_vs_cell.abs().max()),joint_vs_cell_common_rows=int(summary_vs_cell.notna().sum()))
    write('joint.json',result)

def refined():
    j=pd.read_pickle(OUT/'joint_frames.pkl'); d=j['design']; a=j['activity']; frames=pd.read_pickle(OUT/'lenti_frames.pkl')
    aliases={
        'R:FOXA1_FOXA2-ChMod_chr1:38000211-38000353__chr1:38000196-38000367_:099':'R:FOXA1_FOXA2-ChMod_chr1:38000211-38000353_[chr1:38000196-38000367]:099',
        'R:FOXA2-ChMod_chr6:53480537-53480650__chr6:53480508-53480679_:033':'R:FOXA2-ChMod_chr6:53480537-53480650_[chr6:53480508-53480679]:033',
    }
    summary=a['all_cell_types_summary']; ess=a['all_cell_types_ESS']; corrected=summary.name.replace(aliases)
    result=dict(aliases=aliases,alias_note='Proposed explicit crosswalk based on otherwise identical coordinate-bearing names; confirm original design FASTA before sequence-dependent analysis.',joint_after_aliases=dict(matched=int(corrected.isin(d.name).sum()),unmatched=sorted(set(corrected)-set(d.name)),absent_design_count=len(set(d.name)-set(corrected))),encode_vs_supplement={},barcode_rules={})
    passing={}
    for acc,cell in [('ENCSR405QCT','HepG2'),('ENCSR203UFY','K562'),('ENCSR336MKI','WTC11')]:
        enc=pd.concat([v for k,v in frames.items() if acc in k]).drop_duplicates().drop(columns='condition')
        raw=a[cell+'_replicate_level'].iloc[:,:7].copy();raw.columns=['replicate','name','dna_count','rna_count','ratio','log2','n_obs_bc']
        joined=enc.merge(raw,on=['replicate','name'],suffixes=('_enc','_sup'),how='outer',indicator=True,validate='one_to_one')
        result['encode_vs_supplement'][cell]=dict(accession=acc,join_counts=joined['_merge'].value_counts().to_dict(),encode_only=joined.loc[joined['_merge']=='left_only',['replicate','name']].to_dict('records'),max_absolute_numeric_differences={c:float((joined[c+'_enc']-joined[c+'_sup']).abs().max()) for c in ['dna_count','rna_count','ratio','log2','n_obs_bc']})
        bc=raw.pivot(index='name',columns='replicate',values='n_obs_bc')
        passing[cell]={'any_replicate_ge10':set(bc.index[bc.ge(10).any(axis=1)]),'all_three_replicates_ge10':set(bc.index[bc.ge(10).all(axis=1)])}
        result['barcode_rules'][cell]={k:len(v) for k,v in passing[cell].items()}
    result['barcode_intersections']={}
    for rule in passing['HepG2']:
        names=set.intersection(*(x[rule] for x in passing.values()))
        result['barcode_intersections'][rule]=dict(rows=len(names),not_in_ess=len(names-set(ess.name)),ess_not_in_rule=len(set(ess.name)-names))
    E=ess.set_index('name').iloc[:,1:]; S=summary.set_index('name').reindex(E.index);S.columns=E.columns
    z=(S-S.mean())/S.std(ddof=1);candidate=z.sub(z.mean(axis=1),axis=0)
    result['ess_simple_reconstruction']=dict(method='Restrict rounded S11 per-cell means to ESS IDs, column z-score with sample SD, then subtract each row mean.',rmse=float(np.sqrt(((candidate-E)**2).to_numpy().mean())),max_absolute_difference=float((candidate-E).abs().to_numpy().max()),note='Diagnostic only; numerical specificity-score reproduction remains unresolved.')
    inserts=d.iloc[:,-1].str[15:-15];canonical=inserts.map(lambda s:min(s,s.translate(str.maketrans('ACGT','TGCA'))[::-1]))
    result['canonical_sequence_groups']=canonical.value_counts().value_counts().to_dict()
    def fasta(p):
        rows=[]
        for record in p.read_text().split('>')[1:]:
            h,*body=record.splitlines();rows.append((h,''.join(body).replace(' ','').upper()))
        return rows
    cv=fasta(ROOT/'enhancer.cv.txt');ind=fasta(ROOT/'enhancer.ind.txt');lookup={s:(i,h) for i,(h,s) in enumerate(cv,1)}
    result['legacy_exact_matches']=[dict(ind_record=j,ind_header=h,cv_record=lookup[s][0],cv_header=lookup[s][1],sequence_sha256=hashlib.sha256(s.encode()).hexdigest()) for j,(h,s) in enumerate(ind,1) if s in lookup]
    result['duplicate_non_ind_headers']=[h for h,n in collections.Counter(h for h,s in fasta(ROOT/'non.ind.txt')).items() if n>1]
    write('refined.json',result)

def archive_inspection():
    import tarfile
    result={'complete_tar_listings':{},'partial_tar_listings':{},'code':{}}
    folder=DATA/'03_MPRA_STARR_CROSS_ASSAY_2025'
    for fn in ['lab_reported_data.tar.gz','raw_data.tar.gz','qc.tar.gz','output.tar.gz']:
        entries=[]
        with tarfile.open(folder/fn,'r|gz') as archive:
            for m in archive:
                if m.isfile():entries.append(dict(name=m.name,bytes=m.size))
        result['complete_tar_listings'][fn]=dict(files=len(entries),expanded_bytes=sum(x['bytes'] for x in entries),members=entries)
    for p in [folder/'uniform_processed_data.tar.gz',folder/'reference.tar.gz',DATA/'06_DNABERT_ENHANCER_2026/MODEL_WEIGHTS/DNABERT-Enhancer-models.tar.gz']:
        entries=[]
        with tarfile.open(p,'r|gz') as archive:
            for m in archive:
                entries.append(dict(name=m.name,bytes=m.size))
                if len(entries)>=20 or m.size>500000000:break
        result['partial_tar_listings'][p.name]=dict(scope='First 20 entries or until first member larger than 500 MB; no full archive enumeration.',members=entries)
    for p in DATA.glob('*/CODE/*.zip'):
        with zipfile.ZipFile(p) as z:
            names=z.namelist();r=dict(members=len(names),expanded_bytes=sum(x.file_size for x in z.infolist()))
            if 'DNABERT' in p.name:
                launcher=z.read('DNABERT-Enhancer-main/src/prediction/Predict.sh').decode()
                r['prediction_launcher_calls_missing_file']='run_finetune_WANDB_rekha.py' in launcher and not any(n.endswith('run_finetune_WANDB_rekha.py') for n in names)
                r['available_training_entrypoint']='DNABERT-Enhancer-main/src/training/run_finetune_WANDB.py' in names
            result['code'][str(p.relative_to(DATA))]=r
    write('archives.json',result)

def provenance():
    import importlib.util
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('enhancer_downloader',DATA/'download_project_resources.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    failures=[];targets=set()
    for row in m.rows_from(m.DATA_MANIFEST):
        relative=m.data_path(row)
        if relative:targets.add(str(m.safe_destination(relative).relative_to(ROOT)))
    for row in m.rows_from(m.PAPER_MANIFEST):
        if row.get('category')=='MODEL_WEIGHTS':continue
        p=m.safe_destination('/'.join(row[k] for k in ['study_folder','category','filename']));targets.add(str(p.relative_to(ROOT)))
        ok,reason=m.verify(p,row['size_bytes'],row['sha256'])
        if not ok:failures.append(dict(path=str(p.relative_to(ROOT)),reason=reason))
    audited={r['path'] for r in json.loads((DATA/'DOWNLOAD_LOGS/download_audit.json').read_text())['files']}
    write('provenance.json',dict(downloader_read_only_verification_failures=failures,manifest_mapped_resources=len(targets),current_manifest_not_in_previous_audit=sorted(targets-audited),previous_audit_not_in_current_manifest=sorted(audited-targets)))



def main():
    global ROOT, DATA, OUT
    import tempfile
    from datetime import datetime, timezone
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    ROOT=args.root.resolve(); DATA=ROOT/'NEW_2026_DATA'
    metadata=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,openpyxl=openpyxl.__version__,root=str(ROOT),scope='File integrity, structural QC, exact legacy sequence overlap, lentiMPRA joins, source code and archive inventory; no model execution or biological hypothesis test.')
    sections=[integrity,legacy,structural,lenti,joint,refined,archive_inspection,provenance]
    with tempfile.TemporaryDirectory(prefix='enhancers-audit-') as tmp:
        OUT=Path(tmp)
        for section in sections:
            print('Inspecting '+section.__name__,flush=True)
            section()
        result={'metadata':metadata}
        for name in ['integrity','legacy','structural','lenti','joint','refined','archives','provenance']:
            result[name]=json.loads((OUT/(name+'.json')).read_text())
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Saved '+str(args.output))

if __name__=='__main__':
    main()
