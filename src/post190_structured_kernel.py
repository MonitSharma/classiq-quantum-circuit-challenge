"""Care-set phase synthesis audit for the structured four-bit coordinates."""
import argparse, itertools, json, math, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Statevector

from post190_nonlinear_care import solve_phase
from post218_beam_phase import psynth
from distributed_frame_search import native

Y=[0,1,2,3,4,5,9,10,11,12,13]; X=[0,5,8,9,10,11,12,13,2,3,4]
def words(): return np.array(sorted({Y[__import__('two_stage_oracle').ROWCLS[y]] | (X[__import__('two_stage_oracle').COLCLS[x]]<<4) for y in range(64) for x in range(64)}),dtype=int)
def care():
 from two_stage_oracle import logo,ROWCLS,COLCLS
 yi={v:i for i,v in enumerate(Y)}; xi={v:i for i,v in enumerate(X)}
 return words(), np.array([float(logo(next(x for x,c in enumerate(COLCLS) if c==xi[w>>4]),next(y for y,c in enumerate(ROWCLS) if c==yi[w&15]))) for w in words()])
def Hmat(ws): return np.array([[1-2*((w&m).bit_count()%2) for m in range(256)] for w in ws],float)
def move_words(ws,move):
 if move is None:return ws.copy()
 a,b,t,oa,ob=move; return ws ^ (((((ws>>a)&1)^oa)&(((ws>>b)&1)^ob))<<t)
def moves():
 return [None]+[(a,b,t,oa,ob) for a,b in itertools.combinations(range(8),2) for t in range(8) if t not in (a,b) for oa,ob in itertools.product((0,1),repeat=2)]
def conjugator(move):
 q=QuantumCircuit(8)
 if move is None:return q
 a,b,t,oa,ob=move
 if oa:q.x(a)
 if ob:q.x(b)
 q.rccx(a,b,t)
 if ob:q.x(b)
 if oa:q.x(a)
 return q
def compile_kernel(co, move=None, initial=None, final=None):
 phase=psynth(8,{m:float(co[m])*math.pi for m in range(1,256) if abs(co[m])>1e-9},global_phase=float(co[0])*math.pi,seed=190915,beam=96,branch=22,alpha=6,timew=1.4,horizon=1.5,fill=2,initial_times=initial,final_times=final)
 c=conjugator(move); return native(c.compose(phase).compose(c.inverse()))
def verify(k,ws,truth):
 err=0.; phase=None
 for w,t in zip(ws,truth):
  s=Statevector.from_int(int(w),256).evolve(k).data; out=int(abs(s).argmax()); assert out==w
  ratio=s[out]/np.exp(1j*math.pi*t)
  if phase is None:phase=ratio
  err=max(err,abs(ratio-phase))
 return err
def run(out,iterations=2,seeds=64):
 out.mkdir(parents=True,exist_ok=True); ws,truth=care(); H=Hmat(ws); rng=np.random.default_rng(190915); plain=[]
 for i in range(seeds):
  support,co=solve_phase(H,truth,rng,iterations); plain.append({'seed':i,'support':support,'coeff':co.tolist()})
 plain.sort(key=lambda r:r['support']); (out/'plain_solutions.json').write_text(json.dumps(plain,indent=2))
 screen=[]
 for mi,move in enumerate(moves()):
  support,co=solve_phase(Hmat(move_words(ws,move)),truth,rng,1); screen.append({'move':move,'support':support,'coeff':co.tolist()})
  if mi%64==0: print('screen',mi,'best',min(x['support'] for x in screen),flush=True)
 screen.sort(key=lambda r:r['support']); (out/'conjugator_screen.json').write_text(json.dumps(screen,indent=2))
 bests=[]
 for row in plain[:4]+screen[:8]:
  co=np.array(row['coeff']); k=compile_kernel(co,row.get('move')); err=verify(k,ws,truth)
  bests.append({'move':row.get('move'),'support':row['support'],'kernel_depth':k.depth(),'kernel_cx':k.count_ops().get('cx',0),'kernel_u3':k.count_ops().get('u3',0),'care_error':err})
 (out/'compiled.json').write_text(json.dumps(bests,indent=2)); report={'care_words':len(ws),'plain_best':plain[0]['support'],'screen_best':screen[0]['support'],'compiled':bests}; (out/'report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=Path('artifacts/post190_structured_kernel'));p.add_argument('--iterations',type=int,default=2);p.add_argument('--seeds',type=int,default=64);a=p.parse_args();run(a.outdir,a.iterations,a.seeds)
