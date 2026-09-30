"""Exact reschedule of real loader gates, retaining symbolic H/phase metadata."""
import json,pickle,time
from pathlib import Path
import numpy as np
from build import gate_matrix
from kdrv import full_gates,profile
from sim import check_loader2,symbolic_final
from postopt import depth
import smilp
OUT=Path('runs/loader_milp_0923'); OUT.mkdir(exist_ok=True)

def native_blocks(gates):
    pending={}; pairs=[]
    def flush(w):
        if w not in pending:return
        gs=pending.pop(w); U=np.eye(2,dtype=complex)
        for g in gs: U=gate_matrix(g[0])@U
        pairs.append((('u3',(w,),U),gs))
    for g in gates:
        if g[0][0]=='cx':
            flush(g[1]);flush(g[2]);pairs.append((('cx',(g[1],g[2]),None),[g]))
        else: pending.setdefault(g[1],[]).append(g)
    for w in list(pending):flush(w)
    return pairs

def run(path,target):
    D=pickle.load(open(path,'rb')); gates=full_gates(D); pairs=native_blocks(gates)
    ops=[o for o,g in pairs]; original={id(o):g for o,g in pairs}
    rec=dict(source=str(path),target=target,original_depth=depth(ops));print(rec,flush=True)
    start=time.monotonic(); result=smilp.solve(ops,target,tlim=30,verbose=True)
    rec.update(seconds=time.monotonic()-start,success=result is not None)
    tag=Path(path).stem+f'_t{target}'
    if result is not None:
        g=[op for o in result for op in original[id(o)]]
        chk=check_loader2(g,D['newcode']);assert chk['max_dev']<1e-9
        assert symbolic_final(g)==symbolic_final(gates)
        D=dict(D,gates=g,fix=[],depth=depth(result)); prof,_=profile(g)
        assert max(prof)==depth(result)
        rec.update(depth=max(prof),max_dev=chk['max_dev'])
        pickle.dump(D,open(OUT/(tag+'.pkl'),'wb'))
    (OUT/(tag+'.json')).write_text(json.dumps(rec,indent=2));print(rec,flush=True)
    return rec

if __name__=='__main__':
    paths=['runs/parity_0923/protect_y_w7000_d49_s4.pkl',
           'runs/partial_parity_0923/y_a32_b38_s1_w3000_d47_p2.pkl',
           'runs/partial_parity_0923/x_a16_b22_s2_w3000_d47_p2.pkl']
    for path in paths:
        run(path,45 if Path(path).name[0]=='x' else 46)
