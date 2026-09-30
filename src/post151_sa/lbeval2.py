"""Loader evaluation driver with optional 'free' kernel terms (rotations applied in the
forward loader only; the unload is the inverse of the loader WITHOUT them)."""
import pickle, subprocess, sys, os
from sim import check_loader2
from depth import gate_depth
from kdrv import CO, KTERMS
def load_beam(path):
    lines=open(path).read().split('\n'); d=int(lines[0].split()[0]); seq=[]
    for l in lines[1:d+1]:
        t=list(map(int,l.split()))
        for q in range(t[0]): seq.append((t[1+2*q],t[2+2*q]))
    return d,seq
def free_terms(D):
    """pure-side kernel terms as (loader_mask, angle) for this side"""
    side=D['side']; req=D['req']; out=[]
    for m in KTERMS:
        part = (m>>4) if side=='x' else (m&15)
        other = (m&15) if side=='x' else (m>>4)
        if other!=0 or part==0: continue
        v=0
        for k in range(4):
            if part>>k&1: v^=req[k]
        out.append((v, 2*CO[m], m))
    return out
def sa4(D,init,seed=1,iters=0,T0=0.5,T1=0.02,lam=4,mu=0.03,binary='./c/sa4f',tag='lb',free=None):
    targets=D['targets']; plist=[(m,i,a) for i in range(3) for m,a in targets[i].items()]
    fr = free if free is not None else []
    lines=[str(len(plist))]+[f"{m} {i}" for m,i,a in plist]+["0"]
    lines.append(str(len(fr)))
    lines+= [str(v) for v,a,mm in fr]
    lines+= [str(len(init))]+[f"{c} {t}" for c,t in init]
    out=f"runs/{tag}_{seed}.txt"
    r=subprocess.run([binary,str(seed),str(iters),str(T0),str(T1),str(lam),str(mu),out],input="\n".join(lines)+"\n",capture_output=True,text=True)
    txt=open(out).read().split("\n"); d,pen,L=map(int,txt[0].split()); gates=[]
    nP=len(plist)
    for line in txt[1:]:
        if not line: continue
        t=line.split()
        if t[0]=='H': gates.append((('h',),int(t[1])))
        elif t[0]=='R':
            idx=int(t[2])
            if idx<nP: gates.append((('rz',plist[idx][2]),int(t[1])))
            else: gates.append((('rzf',fr[idx-nP][1]),int(t[1])))
        else: gates.append((('cx',),int(t[1]),int(t[2])))
    return d,pen,gates
def strip_free(gates):
    return [g for g in gates if g[0][0]!='rzf']
