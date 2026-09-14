"""Search and compile a raw-bit plus globally-labelled 3-bit descriptor.

The current loader assigns labels separately inside each raw-coordinate
half.  This experiment assigns one 3-bit label per equivalence class, while
retaining the raw bit as the fourth descriptor.  It is exact when classes
sharing a raw value receive different labels, and may lower synthesis cost.
"""
import argparse, json, math, random, time
from pathlib import Path
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import MCXGate
from two_stage_oracle import ROWCLS, COLCLS


def anf(vals):
    a=list(vals)
    for b in range(6):
        for m in range(64):
            if m>>b&1:a[m]^=a[m^(1<<b)]
    return [m for m,v in enumerate(a) if v]


def evaluate(labels, classes, raw):
    terms=[]
    for b in range(3): terms.append(anf([labels[c]>>b&1 for c in classes]))
    collisions=0
    seen={}
    for z,c in enumerate(classes):
        key=(((z>>raw)&1),labels[c])
        if key in seen and classes[seen[key]]!=c:collisions+=1
        seen[key]=z
    return collisions,terms


def compile_encoder(labels, classes, raw):
    q=QuantumCircuit(9)
    # q0..q5 are the dirty coordinate wires; q6..q8 are clean outputs.
    for bit,target in enumerate((6,7,8)):
        for mask in anf([labels[c]>>bit&1 for c in classes]):
            controls=[i for i in range(6) if mask>>i&1]
            if not controls:q.x(target)
            elif len(controls)==1:q.cx(controls[0],target)
            else:q.append(MCXGate(len(controls)),controls+[target])
    return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=0)


def run(outdir,side,seconds,seed):
    outdir.mkdir(parents=True,exist_ok=True); classes=ROWCLS if side=='y' else COLCLS; raw=5 if side=='y' else 4
    n=max(classes)+1; rng=random.Random(seed); labels=[rng.randrange(8) for _ in range(n)]
    # Start from a valid coloring of each raw half.
    for b in (0,1):
        used=set()
        for c in sorted(set(classes[z] for z in range(64) if ((z>>raw)&1)==b)):
            choices=[v for v in range(8) if v not in used]
            labels[c]=choices[0];used.add(labels[c])
    cur=evaluate(labels,classes,raw); score=cur[0]*100+sum(len(x) for x in cur[1]); best=(score,labels[:],cur); start=time.monotonic(); temp=20.; rec=[]
    for step in range(300000):
        if time.monotonic()-start>=seconds:break
        c=rng.randrange(n); old=labels[c]; labels[c]=rng.randrange(8)
        nxt=evaluate(labels,classes,raw); ns=nxt[0]*100+sum(len(x) for x in nxt[1])
        if ns<=score or rng.random()<math.exp((score-ns)/max(.1,temp)):
            score,cur=ns,nxt
        else: labels[c]=old
        temp*=.99995
        if score<best[0]:
            best=(score,labels[:],cur);row={'side':side,'step':step,'objective':score,'collisions':cur[0],'labels':labels[:],'anf_terms':cur[1]};rec.append(row);print(row,flush=True);(outdir/'best.json').write_text(json.dumps(row,indent=2)+'\n')
            if cur[0]==0:
                q=compile_encoder(labels,classes,raw);row.update(native_depth=q.depth(),cx=q.count_ops().get('cx',0));path=outdir/f'{side}_raw_global_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm';path.write_text(qasm2.dumps(q));(outdir/'best.json').write_text(json.dumps(row,indent=2)+'\n');print('compiled',row,flush=True)
    (outdir/'search.json').write_text(json.dumps({'side':side,'seconds':time.monotonic()-start,'records':rec},indent=2)+'\n');return best


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--seconds',type=float,default=60);p.add_argument('--seed',type=int,default=0);a=p.parse_args();run(a.outdir,a.side,a.seconds,a.seed)
