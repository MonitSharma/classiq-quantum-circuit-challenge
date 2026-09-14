"""Exact directed-matching beam with timing Pareto states.

Unlike the earlier matching prototype, this enumerates every disjoint CX
matching on eight wires (sizes 1..4), keeps nondominated timing profiles for a
logical state, and continues expanding incomplete states after a complete one
has entered the beam.
"""
import itertools,json,math,random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native
from post196_free_ancilla_order import finish
from post218_beam_phase import _State,_coords_matrix,_flush,_legal,_potential,_estimate,_circuit
from post258_joint_encoder_schedule import touches

def all_matchings(n=8):
    out=[]
    edges=[(a,b) for a in range(n) for b in range(n) if a!=b]
    for r in range(1,n//2+1):
        for combo in itertools.combinations(edges,r):
            wires=[w for e in combo for w in e]
            if len(set(wires))==2*r:out.append(combo)
    assert len(out)==5936
    return out

MATCHINGS=all_matchings()

def apply(st,layer,targets):
    basis=list(st.basis);inv=list(st.inv);times=list(st.times);ops=st.ops
    for a,b in layer:
        basis[b]^=basis[a];inv[a]^=inv[b];moment=max(times[a],times[b])+1;times[a]=times[b]=moment;ops=ops+(('cx',a,b),)
    nxt=_State(tuple(basis),tuple(inv),st.remaining,ops,tuple(times));_flush(nxt,targets);return nxt

def pareto(pool,cap=4):
    groups={}
    for st in pool:groups.setdefault((st.basis,st.remaining),[]).append(st)
    out=[]
    for vals in groups.values():
        keep=[]
        for st in sorted(vals,key=lambda s:(max(s.times),sum(s.times),len(s.ops))):
            if any(all(a<=b for a,b in zip(x.times,st.times)) for x in keep):continue
            keep=[x for x in keep if not all(a<=b for a,b in zip(st.times,x.times))]
            keep.append(st)
        out.extend(sorted(keep,key=lambda s:(max(s.times),sum(s.times),len(s.ops)))[:cap])
    return out

def psynth(targets,seed,finalize,beam=24,branch=32,alpha=6.0,timew=1.2,horizon=1.5,guard=0,fill=4,max_rounds=100):
    rng=random.Random(seed);start=_State(tuple(1<<w for w in range(8)),tuple(1<<w for w in range(8)),frozenset(targets),(),(0,)*8);_flush(start,targets);states=[start];best=None;complete_round=None
    rounds=0
    while rounds<max_rounds:
        rounds+=1;pool=[]
        for st in states:
            if not st.remaining:pool.append(st);continue
            masks=sorted(st.remaining);c=_coords_matrix(st.inv,masks);counts=c.sum(axis=0);coincide=c.T@c;low=min(st.times);scored=[]
            for li,layer in enumerate(MATCHINGS):
                # Check each target wire after sequentially applying the matching.
                basis=list(st.basis);legal=True
                for a,b in layer:
                    new=basis[a]^basis[b]
                    if not _legal(new,guard):legal=False;break
                    basis[b]=new
                if not legal:continue
                hit=sum(1 for m in st.remaining if m in basis);pot=sum(bin(m).count('1') for m in st.remaining)
                score=alpha*hit-pot/max(1,8)-timew*(max(max(st.times[a],st.times[b])+1 for a,b in layer)-low)+rng.random()*.01
                scored.append((score,layer))
            scored.sort(reverse=True)
            for _,layer in scored[:branch]:pool.append(apply(st,layer,targets))
        if not pool:break
        states=pareto(pool,4)
        complete=[s for s in states if not s.remaining]
        if complete:
            for st in complete:
                score,q=finalize(_circuit(8,st.ops),list(st.basis))
                if best is None or score<best[0]:best=(score,q)
            if complete_round is None:complete_round=rounds
        incomplete=[s for s in states if s.remaining]
        if best is not None:
            incomplete=[s for s in incomplete if max(s.times)+horizon*_estimate(s,8)<best[0][0]]
        if not incomplete:break
        incomplete.sort(key=lambda s:(max(s.times)+horizon*_estimate(s,8),len(s.remaining),_potential(s)))
        states=incomplete[:beam]
    if best is None:raise RuntimeError('no complete state')
    return best,dict(rounds=rounds,complete_round=complete_round,states=len(states))

def run(out,seeds=12):
    assert not out.exists();out.mkdir(parents=True);rec=json.loads(Path('artifacts/193_cx853/phase_search_recipe.json').read_text());co=np.asarray(rec['co'])*math.pi;targets={m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-10};codes=json.loads(Path('artifacts/190/class_codes.json').read_text());enc=encoders(codes,298,506);arrival=[touches(enc)[w] for w in KERNEL_WIRES];best=(190,857);rows=[]
    for seed in range(seeds):
        rng=random.Random(seed+901)
        def finalize(q,basis):
            initial=touches(q,arrival);win=None
            for sample in range(120):
                ops,perm,times=finish(basis,initial,rng,sample);score=(max(times[w]+arrival[col] for w,col in enumerate(perm)),len(ops)+q.size())
                if win is None or score<win[0]:win=(score,ops)
            score,ops=win;r=q.copy()
            for a,b in ops:r.cx(a,b)
            return score,r
        (score,q),meta=psynth(targets,seed,finalize);q=native(enc.compose(q,KERNEL_WIRES).compose(enc.inverse(),list(range(18))));score=(q.depth(),q.count_ops().get('cx',0));row=dict(seed=seed,depth=score[0],cx=score[1],meta=meta);rows.append(row)
        if score<best:best=score;p=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';p.write_text(qasm2.dumps(q));row['path']=str(p);print('IMPROVEMENT',row,flush=True)
        print('seed',seed,'score',score,'best',best,'meta',meta,flush=True);(out/'report.json').write_text(json.dumps(dict(best=best,rows=rows),indent=2))
    print('done',best,flush=True)
if __name__=='__main__':run(Path('artifacts/post190_exact_matching_v1'))
