"""Combine spectrally cheap lookup codes with rebuilt reachable-domain kernels."""
import json,math,time,argparse
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from post258_raw_parity_codes import poly,score,cells
from post258_two_stage_anf import ORDER,encode
from post221_lifted_relative import sparse_relative
from post224_relative_lookup import relative
from post258_kernel_schedule import synth
from distributed_frame_search import native
import two_stage_oracle as ts

def run(outdir,limit,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True);bags=[]
 for side,cls,mask in [('y',ts.ROWCLS,32),('x',ts.COLCLS,48)]:
  r=json.loads(Path(f'artifacts/post221_code_spectra_v1/{side}.json').read_text());bag=[]
  for total,*ids in r['triples'][:limit]:
   codes=[sum(r['options'][idx]['bits'][v]<<b for b,idx in enumerate(ids)) for v in range(len(r['keys']))]
   lab=dict(zip(map(tuple,r['keys']),codes));truth=np.array([r['options'][idx]['truth'] for idx in ids]);tab=math.pi*truth
   choices=[]
   for seed in range(seeds):
    for sparse in [True,False]:
     e=sparse_relative(tab,seed) if sparse else relative(tab,seed)[0]
     if side=='x':e.cx(5,4)
     choices.append((e.depth(),e.size(),seed,sparse,e))
   d,_,seed,sparse,e=min(choices,key=lambda v:v[:2]);bag.append(dict(lab=lab,table=tab,enc=e,depth=d,seed=seed,sparse=sparse,total=total,ids=ids))
  bags.append(bag);print(side,'encoders',len(bag),'best',min(b['depth'] for b in bag),flush=True)
 yc,xc=cells(ts.ROWCLS,32),cells(ts.COLCLS,48);pairs=[]
 for i,y in enumerate(bags[0]):
  for j,x in enumerate(bags[1]):
   sol=poly(y['lab'],x['lab'],yc,xc);cost=score(sol);terms=[m for k,m in enumerate(ORDER) if sol>>k&1]
   # Screen several tradeoffs between loader timing and kernel complexity.
   pairs.append(dict(y=i,x=j,cost=cost,terms=terms,estimate=2*max(y['depth'],x['depth'])+cost*.65))
 selected=[]
 for weight in [.25,.5,1,2]:
  for row in sorted(pairs,key=lambda r:2*max(bags[0][r['y']]['depth'],bags[1][r['x']]['depth'])+weight*r['cost'])[:6]:
   if row not in selected:selected.append(row)
 print('pairs',len(pairs),'selected',len(selected),'best_proxy',min(r['cost'] for r in pairs),flush=True)
 best=(9999,9999);rows=[]
 for row in selected:
  y,x=bags[0][row['y']],bags[1][row['x']];phases=math.pi*np.array([sum(m&~w==0 for m in row['terms']) for w in range(256)])
  enc=QuantumCircuit(18);enc.compose(y['enc'],ts.YW+ts.YA,inplace=True);enc.compose(x['enc'],ts.XW+ts.XA,inplace=True)
  ks=[native(synth(phases,seed)) for seed in range(seeds)];k=min(ks,key=lambda q:(q.depth(),q.size()))
  q=native(enc.compose(k,[11,12,13,14,4,15,16,17]).compose(enc.inverse()));sc=(q.depth(),q.count_ops().get('cx',0));row.update(depth=sc[0],cx=sc[1],y_depth=y['depth'],x_depth=x['depth'],kernel_depth=k.depth());rows.append(row)
  print(row,flush=True)
  if sc<best:
   best=sc;path=outdir/f'spectral_d{sc[0]}_cx{sc[1]}.qasm';path.write_text(qasm2.dumps(q));kpath=outdir/f'kernel_d{sc[0]}.qasm';kpath.write_text(qasm2.dumps(k))
   record=dict(ylab=encode(y['lab']),xlab=encode(x['lab']),ymask=32,xmask=48,terms=row['terms'],y_seed=y['seed'],x_seed=x['seed'],y_sparse=y['sparse'],x_sparse=x['sparse'])
   (outdir/f'codes_d{sc[0]}.json').write_text(json.dumps(record,indent=2)+'\n');row['path']=str(path)
   from exhaustive_verify import exhaustive
   exhaustive(path)
  (outdir/'report.json').write_text(json.dumps(dict(rows=rows,pairs=pairs),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--limit',type=int,default=20);p.add_argument('--seeds',type=int,default=12);a=p.parse_args();run(a.outdir,a.limit,a.seeds)
