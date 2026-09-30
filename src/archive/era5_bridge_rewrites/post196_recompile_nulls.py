"""Recompile distinct previously verified modular phase lifts with the new beam.
Never changes protected packages. Every improving complete oracle is verified.
"""
import argparse,json,math,time
from pathlib import Path
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from depth_parity_network import walsh
from distributed_frame_search import native
from post218_beam_phase import psynth
from build_two_stage_196 import encoders,KERNEL_WIRES
from exhaustive_verify import exhaustive
from post258_two_stage_anf import decode

def run(outdir,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True)
 codes=json.loads(Path('artifacts/196/class_codes.json').read_text())
 enc=encoders(codes,99,155)
 yl,xl=decode(codes['ylab']),decode(codes['xlab'])
 yr={k[0]|v<<1 for k,v in yl.items()};xr={k[0]|v<<1 for k,v in xl.items()}
 care=np.array([y|x<<4 for y in yr for x in xr])
 truth=np.array([sum(m&~w==0 for m in codes['terms'])%2 for w in range(256)])
 candidates={}
 for path in ['artifacts/post218_half_phase_nulls_v1/report.json','artifacts/post221_cube_nulls_v1/report.json']:
  r=json.loads(Path(path).read_text())
  for row in r['history']+r['rows']:
   candidates[tuple(row['co'])]=dict(source=path,co=row['co'])
 rows=[];best=(196,858);bestk=(43,89)
 for idx,row in enumerate(sorted(candidates.values(),key=lambda v:np.count_nonzero(v['co']))):
  phases=walsh(np.array(row['co'],float)/32)*256*math.pi
  coeff=walsh(phases);targets={m:float(coeff[m]) for m in range(1,256) if abs(coeff[m])>1e-12}
  for seed in range(seeds):
   k=native(psynth(8,targets,seed=seed,beam=24,branch=8,alpha=5.,timew=.35,global_phase=float(coeff[0])))
   score=(k.depth(),k.count_ops().get('cx',0))
   if score>bestk:continue
   op=Operator(qasm2.loads(qasm2.dumps(k))).data[:,care];want=np.diag(np.exp(1j*math.pi*truth))[:,care];p=np.vdot(want,op);err=float(np.max(abs(op-p/abs(p)*want)));assert err<1e-10
   q=native(enc.compose(k,KERNEL_WIRES).compose(enc.inverse()));sc=(q.depth(),q.count_ops().get('cx',0))
   result=dict(**row,index=idx,seed=seed,kernel_depth=score[0],kernel_cx=score[1],depth=sc[0],cx=sc[1],kernel_error=err)
   rows.append(result);bestk=min(bestk,score);print({a:b for a,b in result.items() if a!='co'},flush=True)
   if sc<best:
    path=outdir/f'oracle_d{sc[0]}_cx{sc[1]}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path);best=sc
    (outdir/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(k));result['qasm']=str(path)
   (outdir/'report.json').write_text(json.dumps(dict(candidates=len(candidates),seeds=seeds,rows=rows,best=best),indent=2))
  print('completed lift',idx+1,'of',len(candidates),flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(candidates=len(candidates),seeds=seeds,rows=rows,best=best),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=16);a=p.parse_args();run(a.outdir,a.seeds)
