"""Search class codes assisted by a reversible parity of coordinate bits."""
import argparse,json,math,random,time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from distributed_ucry import structured_ucry,verify_component
from distributed_frame_search import native
from post258_kernel_schedule import synth
from post258_two_stage_anf import ORDER,EVAL,encode,decode
import two_stage_oracle as ts


def cells(cls,mask):
    result={}
    for x,c in enumerate(cls):result.setdefault(((x&mask).bit_count()%2,c),[]).append(x)
    assert max(sum(k[0]==b for k in result) for b in [0,1])<=8
    return result


def poly(yl,xl,ycell,xcell):
    piv={}
    for y,ys in ycell.items():
        for x,xs in xcell.items():
            w=y[0]|(yl[y]<<1)|(x[0]<<4)|(xl[x]<<5);row=EVAL[w];rhs=int(ts.logo(xs[0],ys[0]))
            while row:
                i=(row&-row).bit_length()-1
                if i in piv:a,b=piv[i];row^=a;rhs^=b
                else:piv[i]=(row,rhs);break
            assert row or rhs==0
    sol=0
    for i in sorted(piv,reverse=True):
        row,rhs=piv[i]
        if ((row&sol).bit_count()&1)^rhs:sol|=1<<i
    return sol


def score(sol):
    return sum([0,0.05,0.5,1,4,40,160,500,1000][m.bit_count()] for i,m in enumerate(ORDER) if sol>>i&1)


def search(outdir,mask,steps,seed,temperature=18,macros=False,start_record=None):
    assert not outdir.exists();outdir.mkdir(parents=True)
    yc,xc=cells(ts.ROWCLS,32),cells(ts.COLCLS,mask);rng=random.Random(seed)
    labs=[]
    for cc in [yc,xc]:
        lab={}
        for b in [0,1]:
            keys=[k for k in cc if k[0]==b];values=list(range(8));rng.shuffle(values)
            lab.update(zip(keys,values))
        labs.append(lab)
    if mask==16:
        rec=json.loads(Path('artifacts/243/class_codes.json').read_text());labs=[decode(rec['ylab']),decode(rec['xlab'])]
    if start_record is not None:
        rec=json.loads(start_record.read_text());assert rec['xmask']==mask
        labs=[decode(rec['ylab']),decode(rec['xlab'])]
    sol=poly(*labs,yc,xc);cur=score(sol);best=cur;start=time.monotonic()
    initial=dict(step=-1,seed=seed,temperature=temperature,macros=macros,xmask=mask,ymask=32,cost=cur,terms=[m for i,m in enumerate(ORDER) if sol>>i&1],ylab=encode(labs[0]),xlab=encode(labs[1]))
    (outdir/'best_initial.json').write_text(json.dumps(initial,indent=2)+'\n')
    for step in range(steps):
        lab=labs[rng.randrange(2)];previous=lab.copy();keys=list(lab)
        if macros and rng.random()<0.4:
            control,target=rng.sample(range(3),2);half=rng.choice([0,1,None]);kind=rng.randrange(2)
            for key in keys:
                if half is None or key[0]==half:
                    lab[key]^=(1 if kind==0 else lab[key]>>control&1)<<target
        else:
            a=rng.choice(keys);value=rng.randrange(8)
            other=next((k for k in keys if k[0]==a[0] and lab[k]==value),None)
            prev=lab[a];lab[a]=value
            if other is not None:lab[other]=prev
        ns=poly(*labs,yc,xc);cost=score(ns);temp=1+temperature*(1-(step%2000)/2000)**2
        if cost<=cur or rng.random()<math.exp(min(0,(cur-cost)/temp)):sol,cur=ns,cost
        else:
            lab.clear();lab.update(previous)
        if cur<best:
            best=cur;terms=[m for i,m in enumerate(ORDER) if sol>>i&1]
            row=dict(step=step,seed=seed,temperature=temperature,macros=macros,xmask=mask,ymask=32,cost=cur,terms=terms,ylab=encode(labs[0]),xlab=encode(labs[1]))
            (outdir/f'best_{step}.json').write_text(json.dumps(row,indent=2)+'\n')
            print('best',mask,step,cur,'degree',max(m.bit_count() for m in terms),flush=True)
    print('seconds',time.monotonic()-start,flush=True)


def build(record,outdir,seeds,kernel_file=None):
    assert not outdir.exists();outdir.mkdir(parents=True)
    r=json.loads(record.read_text());yl,xl=decode(r['ylab']),decode(r['xlab']);es=[];rows=[];rawbits=[]
    for cls,mask,lab in [(ts.ROWCLS,32,yl),(ts.COLCLS,r['xmask'],xl)]:
        cc=cells(cls,mask);codes=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
        tab=np.array([[math.pi*(code>>b&1) for code in codes] for b in range(3)])
        options=[]
        for seed in range(seeds):
            for sparse,opened in [(False,True),(True,False)]:
                q=structured_ucry(tab,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                options.append((q.depth(),q.size(),seed,sparse,opened,q))
        qs=[(native(t[-1]),t[2:5]) for t in sorted(options,key=lambda t:t[:2])[:4]]
        e,settings=min(qs,key=lambda t:(t[0].depth(),t[0].size()));err=verify_component(e,tab)
        raw=(mask&-mask).bit_length()-1;rawbits.append(raw)
        for b in range(6):
            if b!=raw and mask>>b&1:e.cx(b,raw)
        es.append(e);rows.append(dict(depth=e.depth(),settings=settings,error=err,raw=raw))
        (outdir/f'encoder_{len(es)-1}.qasm').write_text(qasm2.dumps(e))
    phases=math.pi*np.array([sum(int(m&~w==0) for m in r['terms']) for w in range(256)])
    kernels=[native(synth(phases,seed)) for seed in range(seeds)] if kernel_file is None else [qasm2.load(kernel_file)]
    k=min(kernels,key=lambda q:(q.depth(),q.size()));print('components',rows,'kernel',k.depth(),flush=True)
    from qiskit.quantum_info import Operator
    op=Operator(k).data;want=np.diag(np.exp(1j*phases));overlap=np.vdot(want,op)
    assert np.max(abs(op-overlap/abs(overlap)*want))<1e-10
    (outdir/'kernel.qasm').write_text(qasm2.dumps(k))
    enc=QuantumCircuit(18);enc.compose(es[0],ts.YW+ts.YA,inplace=True);enc.compose(es[1],ts.XW+ts.XA,inplace=True)
    q=native(enc.compose(k,[rawbits[0]+6]+ts.YA+[rawbits[1]]+ts.XA).compose(enc.inverse()))
    path=outdir/f'raw_parity_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(record=str(record),kernel_file=str(kernel_file) if kernel_file else None,components=rows,kernel_depth=k.depth(),depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path))
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--mask',type=int,default=48);p.add_argument('--steps',type=int,default=6000);p.add_argument('--seed',type=int,default=0);p.add_argument('--record',type=Path);p.add_argument('--seeds',type=int,default=24);p.add_argument('--temperature',type=float,default=18);p.add_argument('--macros',action='store_true');p.add_argument('--start',type=Path);p.add_argument('--kernel-file',type=Path);a=p.parse_args()
    if a.record:build(a.record,a.outdir,a.seeds,a.kernel_file)
    else:search(a.outdir,a.mask,a.steps,a.seed,a.temperature,a.macros,a.start)
