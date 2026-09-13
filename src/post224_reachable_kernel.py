"""Fit diagonal ANF on all 4096 encoded states, using all 18 features."""
import argparse,itertools,json,math,random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from distributed_frame_search import native
from distributed_ucry import structured_ucry
from post258_two_stage_anf import decode
from post258_kernel_schedule import synth
import two_stage_oracle as ts


def encoding():
    r=json.loads(Path('artifacts/224/class_codes.json').read_text());yl,xl=decode(r['ylab']),decode(r['xlab'])
    yc=[yl[(y>>5,ts.ROWCLS[y])] for y in range(64)]
    xc=[xl[((x&48).bit_count()%2,ts.COLCLS[x])] for x in range(64)]
    states=[(x^(((x>>5)&1)<<4))|(y<<6)|(yc[y]<<12)|(xc[x]<<15) for y in range(64) for x in range(64)]
    enc=QuantumCircuit(18)
    for code,seed,wires in [(yc,11,ts.YW+ts.YA),(xc,3,ts.XW+ts.XA)]:
        tab=np.array([[math.pi*(c>>b&1) for c in code] for b in range(3)])
        q=native(structured_ucry(tab,[6,7,8],list(range(6)),seed,sparse=False,open_walk=True))
        enc.compose(q,wires,inplace=True)
    enc.cx(5,4)
    return states,enc


def solve(states,max_degree,seed):
    rng=random.Random(seed);allones=(1<<4096)-1
    features=[sum(1<<i for i,s in enumerate(states) if s>>b&1) for b in range(18)]
    target=sum(1<<(y*64+x) for y in range(64) for x in range(64) if ts.logo(x,y))
    piv={};masks=[];stats=[]
    for degree in range(max_degree+1):
        combinations=list(itertools.combinations(range(18),degree));rng.shuffle(combinations)
        for bits in combinations:
            row=allones;mask=0
            for b in bits:row&=features[b];mask|=1<<b
            idx=len(masks);masks.append(mask);combo=1<<idx
            while row:
                p=row.bit_length()-1
                if p in piv:r,c=piv[p];row^=r;combo^=c
                else:piv[p]=(row,combo);break
        rem=target;combo=0
        while rem:
            p=rem.bit_length()-1
            if p not in piv:break
            row,c=piv[p];rem^=row;combo^=c
        stats.append(dict(degree=degree,columns=len(masks),rank=len(piv),solved=not bool(rem)))
        print(stats[-1],flush=True)
        if not rem:
            terms=[m for i,m in enumerate(masks) if combo>>i&1]
            assert all(sum(int(m&~s==0) for m in terms)%2==int(ts.logo(i%64,i//64)) for i,s in enumerate(states))
            return terms,stats
    return None,stats


def phase_vector(terms):
    # The integer ANF lift has sparse Walsh coefficients; inverse Walsh builds
    # a representative equivalent on the promised states, up to global phase.
    co=np.zeros(1<<18)
    for m in terms:
        sub=m;v=math.pi/(1<<m.bit_count())
        while True:
            co[sub]+=v*(-1)**sub.bit_count()
            if not sub:break
            sub=(sub-1)&m
    # Rz angles are periodic up to shared global phase.
    co=(co+math.pi/2)%math.pi-math.pi/2
    a=co.copy();h=1
    while h<len(a):
        block=a.reshape(-1,2*h);lo=block[:,:h].copy();hi=block[:,h:].copy();block[:,:h]=lo+hi;block[:,h:]=lo-hi;h*=2
    return a,int(np.count_nonzero(abs(co[1:])>1e-10))


def run(outdir,degree,seed,compile_seeds):
    assert not outdir.exists();outdir.mkdir(parents=True)
    states,enc=encoding();terms,stats=solve(states,degree,seed)
    report=dict(seed=seed,stats=stats,terms=terms)
    if terms is None:
        (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n');return
    phases,count=phase_vector(terms);report.update(parity_terms=count,anf_terms=len(terms))
    print('support',len(terms),count,flush=True)
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    best=(99999,99999)
    for sd in range(compile_seeds):
        k=native(synth(phases,sd));q=native(enc.compose(k).compose(enc.inverse()));score=(q.depth(),q.count_ops().get('cx',0))
        print('candidate',sd,'kernel',k.depth(),'full',score,flush=True)
        if score<best:
            best=score;path=outdir/f'full_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q))
            report.update(path=str(path),depth=score[0],cx=score[1],kernel_depth=k.depth(),kernel_seed=sd)
            from exhaustive_verify import exhaustive
            exhaustive(path)
            (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--degree',type=int,default=5);p.add_argument('--seed',type=int,default=0);p.add_argument('--compile-seeds',type=int,default=2);a=p.parse_args();run(a.outdir,a.degree,a.seed,a.compile_seeds)
