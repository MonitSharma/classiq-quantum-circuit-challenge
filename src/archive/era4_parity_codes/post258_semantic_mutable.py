"""Measure a reversible mutable-coordinate semantic encoder, preserving prior artifacts."""
import argparse, json, math, random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import RC3XGate
from distributed_frame_search import native
from distributed_ucry import structured_ucry, verify_component
from post258_kernel_schedule import synth
from level_oracle import LEVEL, logo


def semantic():
    ym=[a+b for a,b in zip(LEVEL['u1'],LEVEL['u2'])]
    yf=[int(LEVEL['u2'][y]>0) if ym[y] else y>>5 for y in range(64)]
    xf=[int(27<=x<=49) for x in range(64)]
    xm=[LEVEL['v1'][x] if xf[x] else LEVEL['v2'][x] for x in range(64)]
    assert all((((yf[y]^xf[x]) and ym[y]+xm[x]>=6) ^ (yf[y] and xf[x] and ym[y]>=5))==logo(x,y) for y in range(64) for x in range(64))
    return (ym,yf),(xm,xf)


def solve(care,n,seed=0):
    rng=random.Random(seed)
    order=sorted(range(1<<n),key=lambda m:(m.bit_count(),rng.random()))
    piv={}
    for w,rhs in care.items():
        row=sum(1<<j for j,m in enumerate(order) if m&~w==0)
        while row:
            i=(row&-row).bit_length()-1
            if i in piv:
                a,b=piv[i];row^=a;rhs^=b
            else:piv[i]=(row,rhs);break
        assert row or rhs==0
    sol=0
    for i in sorted(piv,reverse=True):
        row,rhs=piv[i]
        if ((row&sol).bit_count()&1)^rhs:sol|=1<<i
    return [m for i,m in enumerate(order) if sol>>i&1]


def flag_circuit(terms):
    q=QuantumCircuit(9);wires=[0,1,2,3,4,6,7,8]
    for m in terms:
        c=[wires[i] for i in range(8) if m>>i&1]
        if len(c)==0:q.x(5)
        elif len(c)==1:q.cx(c[0],5)
        elif len(c)==2:q.rccx(*c,5)
        elif len(c)==3:q.append(RC3XGate(),c+[5])
        else:q.mcx(c,5)
    return native(q)


def run(outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True)
    sides=semantic();codes=[[0,4,6,1,3,7],[0,2,1,4,5,6]]
    es=[];records=[]
    for side,((levels,flags),code) in enumerate(zip(sides,codes)):
        table=np.array([[math.pi*((code[v]>>b)&1) for v in levels] for b in range(3)])
        choices=[]
        for seed in range(seeds):
            for sparse,opened in [(False,True),(True,False)]:
                q=structured_ucry(table,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                choices.append((q.depth(),q.size(),seed,sparse,opened,q))
        compiled=[(native(t[-1]),t[2:5]) for t in sorted(choices,key=lambda t:t[:2])[:4]]
        loader,settings=min(compiled,key=lambda t:(t[0].depth(),t[0].size()))
        error=verify_component(loader,table)
        care={}
        for v in range(64):
            w=(v&31)|(code[levels[v]]<<5);rhs=(v>>5)^flags[v]
            assert w not in care or care[w]==rhs
            care[w]=rhs
        polynomials=[solve(care,8,seed) for seed in range(100)]
        polynomials.sort(key=lambda ts:sum([1,1,7,18,50,100,200,400,800][t.bit_count()] for t in ts))
        fs=[(flag_circuit(ts),ts) for ts in polynomials[:10]]
        flag,terms=min(fs,key=lambda t:(t[0].depth(),t[0].size()))
        e=native(loader.compose(flag));es.append(e)
        row=dict(side=side,loader_depth=loader.depth(),flag_depth=flag.depth(),encoder_depth=e.depth(),terms=terms,settings=settings,loader_error=error)
        records.append(row);print(row,flush=True)
        (outdir/f'encoder_{side}.qasm').write_text(qasm2.dumps(e))
    # Full reachable kernel, use the same arbitrary-input-safe phase scheduler.
    care={}
    for y in range(64):
        for x in range(64):
            w=sides[0][1][y]|(codes[0][sides[0][0][y]]<<1)|(sides[1][1][x]<<4)|(codes[1][sides[1][0][x]]<<5)
            assert w not in care or care[w]==int(logo(x,y))
            care[w]=int(logo(x,y))
    polys=[solve(care,8,seed) for seed in range(50)]
    polys.sort(key=lambda ts:sum(2**t.bit_count() for t in ts))
    kernels=[]
    for ts in polys[:3]:
        phases=math.pi*np.array([sum(int(m&~w==0) for m in ts) for w in range(256)],float)
        for seed in range(seeds):
            k=native(synth(phases,seed));kernels.append((k.depth(),k.size(),k,ts))
    _,_,k,terms=min(kernels,key=lambda t:t[:2]);print('kernel',k.depth(),k.count_ops(),flush=True)
    e=QuantumCircuit(18);e.compose(es[0],list(range(6,12))+[12,13,14],inplace=True);e.compose(es[1],list(range(6))+[15,16,17],inplace=True)
    q=native(e.compose(k,[11,12,13,14,5,15,16,17]).compose(e.inverse()))
    path=outdir/f'mutable_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(encoders=records,kernel_depth=k.depth(),kernel_terms=terms,depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path))
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=16);a=p.parse_args();run(a.outdir,a.seeds)
