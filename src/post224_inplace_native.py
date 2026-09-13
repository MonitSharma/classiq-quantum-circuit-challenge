"""Compile saved two-in-place/two-ancilla witnesses, measuring full native depth."""
import argparse,itertools,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.circuit.library import UCRYGate
from qiskit.synthesis.linear import synth_cnot_count_full_pmh
from qiskit.quantum_info import Statevector
from distributed_ucry import coordinates,structured_ucry
from distributed_frame_search import native
from post258_kernel_schedule import synth
from post224_clean_parity import synth_clean
import two_stage_oracle as ts


def clean_ucry(tables,seeds=12):
    tables=np.array(tables,float);outputs,n=tables.shape;controls=(n-1).bit_length();logical=controls+outputs
    phases=np.array([-.5*sum(tables[b,w&(n-1)]*(-1)**(w>>(controls+b)&1) for b in range(outputs)) for w in range(1<<logical)])
    options=[]
    for seed in range(seeds):
        q=QuantumCircuit(logical+3)
        for b in range(controls,logical):q.rx(math.pi/2,b)
        q.compose(synth_clean(phases,3,seed),inplace=True)
        for b in range(controls,logical):q.rx(-math.pi/2,b)
        q=native(q);options.append(q)
    return min(options,key=lambda q:(q.depth(),q.size()))


def transform(side,use_clean=False):
    data=json.loads(Path(f'artifacts/inplace_v1/{side}_construction.json').read_text())
    if side=='x':data=data['x']
    basis=data['basis'];mapping=[coordinates(v,basis) for v in range(64)]
    matrix=np.array([[(mapping[1<<j]>>i)&1 for j in range(6)] for i in range(6)],dtype=bool)
    lin=min([synth_cnot_count_full_pmh(matrix,section_size=s) for s in [1,2,3]],key=lambda q:(q.depth(),q.size()))
    q=QuantumCircuit(9);q.compose(lin,range(6),inplace=True)
    if side=='y':
        for name,target,other,subset in [('g1',0,1,data['S']),('g2',1,0,data['T'])]:
            table=[int(data[name][f'{s},{v}']) for s in range(8) for v in range(2)]
            controls=[other]+[2+b for b in subset]
            if use_clean:
                helper=clean_ucry([[math.pi*b for b in table]])
                q.compose(helper,controls+[target,6,7,8],inplace=True)
            else:q.append(UCRYGate([math.pi*b for b in table]),[target]+controls)
            for i,z in enumerate(mapping):
                index=sum(((z>>b)&1)<<j for j,b in enumerate(controls))
                mapping[i]=z^(table[index]<<target)
    else:
        if use_clean:
            helper=clean_ucry([[math.pi*(s>>b&1) for s in data['shifts']] for b in range(2)])
            q.compose(helper,[2,3,4,5,0,1,6,7,8],inplace=True)
        for target in [0,1]:
            table=[s>>target&1 for s in data['shifts']]
            if not use_clean:q.append(UCRYGate([math.pi*b for b in table]),[target,2,3,4,5])
            mapping=[z^(table[z>>2]<<target) for z in mapping]
    assert len(set(mapping))==64
    q=native(q);cls=ts.ROWCLS if side=='y' else ts.COLCLS;cells={}
    for v,c in enumerate(cls):cells.setdefault((mapping[v]&3,c),[]).append(v)
    assert all(sum(k[0]==b for k in cells)==4 for b in range(4))
    return q,mapping,cells


def scalar_options(mapping,cells):
    groups=[[k for k in cells if k[0]==b] for b in range(4)];out=[]
    for halves in itertools.product(list(itertools.combinations(range(4),2)),repeat=4):
        labels={k:int(i in halves[b]) for b,keys in enumerate(groups) for i,k in enumerate(keys)}
        table=np.zeros(64,int)
        for k,values in cells.items():
            for v in values:table[mapping[v]]=labels[k]
        spec=table.astype(float)
        h=1
        while h<64:
            for i in range(0,64,2*h):a=spec[i:i+h].copy();b=spec[i+h:i+2*h].copy();spec[i:i+h]=a+b;spec[i+h:i+2*h]=a-b
            h*=2
        masks=np.flatnonzero(spec);piv={}
        for mask in masks:
            mask=int(mask)
            while mask:
                p=mask.bit_length()-1
                if p in piv:mask^=piv[p]
                else:piv[p]=mask;break
        out.append(dict(halves=halves,labels=labels,table=table,rank=len(piv),support=len(masks)))
    return out


def choose_labels(options,cells):
    best=None
    for i,a in enumerate(options):
        for b in options[:i]:
            if any(set(a['halves'][g])==set(b['halves'][g]) or set(a['halves'][g]).isdisjoint(b['halves'][g]) for g in range(4)):continue
            score=(2**a['rank']+2**b['rank'],a['support']+b['support'])
            if best is None or score<best[0]:best=(score,a,b)
    _,a,b=best;labels={k:a['labels'][k]|(b['labels'][k]<<1) for k in cells}
    return labels,dict(ranks=[a['rank'],b['rank']],supports=[a['support'],b['support']])


def run(outdir,seeds,use_clean=False):
    assert not outdir.exists();outdir.mkdir(parents=True);es=[];maps=[];labs=[];allcells=[];rows=[]
    for side in ['y','x']:
        change,mapping,cells=transform(side,use_clean);options=scalar_options(mapping,cells);lab,metric=choose_labels(options,cells)
        tables=np.zeros((3,64));codes=[0]*64
        for k,values in cells.items():
            for v in values:
                codes[v]=lab[k]
                for bit in range(2):tables[bit,mapping[v]]=math.pi*(lab[k]>>bit&1)
        choices=[]
        for seed in range(seeds):
            for sparse,opened in [(False,True),(True,False)]:
                q=structured_ucry(tables,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                choices.append((q.depth(),q.size(),seed,sparse,opened,q))
        candidates=[(native(c[-1]),c[2:5]) for c in sorted(choices,key=lambda t:t[:2])[:4]]
        loader,settings=min(candidates,key=lambda t:(t[0].depth(),t[0].size()));e=native(change.compose(loader))
        errors=[]
        for v in range(64):
            state=Statevector.from_int(v,512).evolve(e).data;w=mapping[v]|(codes[v]<<6);phase=state[w]/abs(state[w]);want=np.zeros(512,complex);want[w]=phase;errors.append(float(np.max(abs(state-want))))
        assert max(errors)<1e-10
        es.append(e);maps.append(mapping);labs.append(lab);allcells.append(cells)
        row=dict(side=side,change_depth=change.depth(),loader_depth=loader.depth(),encoder_depth=e.depth(),subspace_error=max(errors),settings=settings,code_metrics=metric,min_scalar_rank=min(o['rank'] for o in options))
        rows.append(row);print(row,flush=True);(outdir/f'encoder_{side}.qasm').write_text(qasm2.dumps(e))
    truth=np.zeros(256,int)
    for yk,ys in allcells[0].items():
        for xk,xs in allcells[1].items():
            w=yk[0]|(labs[0][yk]<<2)|(xk[0]<<4)|(labs[1][xk]<<6);truth[w]=int(ts.logo(xs[0],ys[0]))
    anf=truth.copy()
    for b in range(8):
        for m in range(256):
            if m>>b&1:anf[m]^=anf[m^(1<<b)]
    terms=np.flatnonzero(anf).tolist();phases=math.pi*np.array([sum(int(m&~w==0) for m in terms) for w in range(256)])
    kernels=[native(synth_clean(phases,2,s) if use_clean else synth(phases,s)) for s in range(seeds)];k=min(kernels,key=lambda q:(q.depth(),q.size()))
    enc=QuantumCircuit(18);enc.compose(es[0],ts.YW+ts.YA,inplace=True);enc.compose(es[1],ts.XW+ts.XA,inplace=True)
    kw=[6,7,12,13,0,1,15,16]+([14,17] if use_clean else [])
    q=native(enc.compose(k,kw).compose(enc.inverse()));path=outdir/f'inplace_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(encoders=rows,kernel_depth=k.depth(),kernel_terms=terms,depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path),labels=[{','.join(map(str,k)):v for k,v in lab.items()} for lab in labs]);print('full',q.depth(),q.count_ops(),flush=True)
    (outdir/'kernel.qasm').write_text(qasm2.dumps(k));(outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=16);p.add_argument('--clean',action='store_true');a=p.parse_args();run(a.outdir,a.seeds,a.clean)
