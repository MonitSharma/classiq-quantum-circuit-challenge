"""Search single-RCCX conjugations of the exact 190 phase polynomial."""
import itertools, json, math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from build_two_stage_196 import encoders, KERNEL_WIRES
from distributed_frame_search import native
from post218_beam_phase import psynth
from depth_parity_network import walsh

def equiv(a,b):
    x,y=Operator(a).data,Operator(b).data
    if max(abs(x-y).flat) < 1e-12: return True
    i,j=divmod(abs(y).argmax(),y.shape[1])
    if abs(x[i,j]) < 1e-10: return False
    p=x[i,j]/y[i,j]
    return bool(max(abs(x-p*y).flat)<1e-8)

def run(out):
    assert not out.exists(); out.mkdir(parents=True)
    recipe=json.loads(Path('artifacts/193_cx853/phase_search_recipe.json').read_text())
    co=np.asarray(recipe['co'],float)*math.pi; phases=walsh(co)*len(co)
    # The shipped kernel exits in a physical ancilla permutation. A diagonal
    # candidate must be compared with the phase recipe, not that permutation.
    base=QuantumCircuit(8)
    from qiskit.circuit.library import DiagonalGate
    base.append(DiagonalGate(np.exp(1j*phases)),range(8))
    codes=json.loads(Path('artifacts/190/class_codes.json').read_text())
    enc=encoders(codes,298,506); best=(190,857); rows=[]
    cases=[]
    for a,b,t in itertools.permutations(range(8),3):
        if a>b: continue
        for oa,ob in itertools.product((0,1),repeat=2): cases.append((a,b,t,oa,ob))
    for index,(a,b,t,oa,ob) in enumerate(cases):
        c=QuantumCircuit(8)
        if oa:c.x(a)
        if ob:c.x(b)
        c.rccx(a,b,t)
        if ob:c.x(b)
        if oa:c.x(a)
        op=Operator(c).data; mapping=np.argmax(abs(op),axis=0)
        transformed=phases[mapping]; targets=walsh(transformed)
        if np.count_nonzero(abs(targets)>1e-10) > 64: continue
        k=psynth(8,{m:float(targets[m]) for m in range(1,256) if abs(targets[m])>1e-10},
                 global_phase=float(targets[0]),seed=index%8,beam=16,branch=8,alpha=5.0,timew=.35)
        qk=native(c.compose(k).compose(c.inverse()))
        if not equiv(qk,base): continue
        q=native(enc.compose(qk,KERNEL_WIRES).compose(enc.inverse()))
        score=(q.depth(),q.count_ops().get('cx',0)); row=dict(move=[a,b,t,oa,ob],kernel_depth=qk.depth(),kernel_cx=qk.count_ops().get('cx',0),depth=score[0],cx=score[1],equiv=True)
        rows.append(row)
        if score<best:
            p=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';p.write_text(qasm2.dumps(q))
            from exhaustive_verify import exhaustive
            exhaustive(p)
            best=score;row['path']=str(p);print('IMPROVEMENT',row,flush=True)
        if index%32==0: print('index',index,'best',best,'last',score,flush=True)
    (out/'report.json').write_text(json.dumps(dict(best=best,cases=len(cases),rows=rows),indent=2)+'\n'); print('done',best,flush=True)
if __name__=='__main__': run(Path('artifacts/post190_rccx_phase_v3'))
