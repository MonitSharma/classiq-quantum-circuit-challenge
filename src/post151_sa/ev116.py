"""Beam output -> kernel gates -> assembled circuit -> CX cancellation -> exact commutation MILP at target T."""
import pickle, sys, os
sys.path.insert(0, '.')
from kdrv import assemble, CO, KTERMS
from postopt import parse_ops, fuse, depth, write
from canc import simplify
import smilp
_here=os.path.dirname(os.path.abspath(__file__))
_cands=[os.environ.get('CHAMP_PKL',''),os.path.join(_here,'sat116','champ117.pkl'),os.path.join(_here,'../../../champ117.pkl')]
DX,DY,pl=pickle.load(open([c for c in _cands if c and os.path.exists(c)][0],'rb'))
def build_kg_s(pl, beampath, svec, T, relax=None):
    relax = relax or [0]*8
    seq, W, ST, rdy, unl = pl
    L = open(beampath).read().split('\n'); d, tau0 = map(int, L[0].split())
    Tset = set(KTERMS); rows = list(ST); done = set(); pend = {}
    body = [('C', c, t) for c, t in seq]
    for i in range(8):
        if rows[i] in Tset and rows[i] not in done: done.add(rows[i]); pend[i] = rows[i]
    for k in range(1, d + 1):
        t = list(map(int, L[k].split())); layer = [(t[1+2*q], t[2+2*q]) for q in range(t[0])]
        tau = tau0 + k; used = {x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau > svec[i] and tau <= (T - unl[i] + relax[i]):
                body.append(('R', W[i], 2 * CO[pend.pop(i)]))
        for c, tt in layer:
            assert tt not in pend
            body.append(('C', W[c], W[tt]))
        for tt, v in [(tt, rows[tt] ^ rows[c]) for c, tt in layer]:
            rows[tt] = v
            if v in Tset and v not in done: done.add(v); pend[tt] = v
    for i, v in pend.items(): body.append(('R', W[i], 2 * CO[v]))
    assert done == Tset, (len(done), len(Tset))
    sigma = list(range(18)); used = set()
    for i in range(8):
        cand = [j for j in range(8) if rows[j] == ST[i] and j not in used]
        assert cand; sigma[W[i]] = W[cand[0]]; used.add(cand[0])
    return [('S', sigma)] + body + [('C', c, t) for c, t in reversed(seq)]
def evaluate(beampath, svec, Tmodel, Ttarget=116, tlim=120, relax=None):
    kg=build_kg_s(pl, beampath, svec, Tmodel, relax)
    q=beampath.replace('.txt','_asm.qasm')
    d0,cx0=assemble(DX,DY,kg,q)
    ops=fuse(simplify(fuse(parse_ops(q)),verbose=False))
    ncx=sum(1 for o in ops if o[0]=='cx')
    res={'asm_depth':d0,'asm_cx':cx0,'simp_cx':ncx,'simp_depth':depth(ops)}
    for TT in (Ttarget,):
        out=smilp.solve(ops,TT,tlim=tlim,verbose=False)
        res['T%d'%TT]= out is not None
        if out is not None:
            f=fuse(out); res['sched_depth']=depth(f)
            path=beampath.replace('.txt',f'_m{TT}.qasm'); write(f,path); res['qasm']=path
    return res
if __name__=='__main__':
    import json
    svec=list(map(int,sys.argv[2].split(','))); Tm=int(sys.argv[3]); Tt=int(sys.argv[4]) if len(sys.argv)>4 else 116
    print(json.dumps(evaluate(sys.argv[1],svec,Tm,Tt)))

VFZ=[31,39,42,46,31,43,44,44]; XRDY=[34,39,41,46,35,43,44,42]
def typed_windows(T, dz=None, dx=None):
    dz=dz or [0]*8; dx=dx or [0]*8
    ZS=[v for v in VFZ]; XS=[v for v in XRDY]
    ZD=[T-v+a for v,a in zip(VFZ,dz)]; XD=[T-v+a for v,a in zip(XRDY,dx)]
    return ZS,XS,ZD,XD
def build_kg_typed(pl, beampath, ZS, ZD):
    seq, W, ST, rdy, unl = pl
    L = open(beampath).read().split('\n'); d, tau0 = map(int, L[0].split())
    Tset = set(KTERMS); rows = list(ST); done = set(); pend = {}
    body = [('C', c, t) for c, t in seq]
    for i in range(8):
        if rows[i] in Tset and rows[i] not in done: done.add(rows[i]); pend[i] = rows[i]
    for k in range(1, d + 1):
        t = list(map(int, L[k].split())); layer = [(t[1+2*q], t[2+2*q]) for q in range(t[0])]
        tau = tau0 + k; used = {x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau > ZS[i] and tau <= ZD[i]:
                body.append(('R', W[i], 2 * CO[pend.pop(i)]))
        for c, tt in layer:
            assert tt not in pend
            body.append(('C', W[c], W[tt]))
        for tt, v in [(tt, rows[tt] ^ rows[c]) for c, tt in layer]:
            rows[tt] = v
            if v in Tset and v not in done: done.add(v); pend[tt] = v
    for i, v in pend.items(): body.append(('R', W[i], 2 * CO[v]))
    assert done == Tset, (len(done), len(Tset))
    sigma = list(range(18)); used = set()
    for i in range(8):
        cand = [j for j in range(8) if rows[j] == ST[i] and j not in used]
        assert cand; sigma[W[i]] = W[cand[0]]; used.add(cand[0])
    return [('S', sigma)] + body + [('C', c, t) for c, t in reversed(seq)]
def evaluate_kg(kg, tag, Ttarget=116, tlim=90):
    q=tag+'_asm.qasm'
    d0,cx0=assemble(DX,DY,kg,q)
    ops=fuse(simplify(fuse(parse_ops(q)),verbose=False))
    res={'asm_depth':d0,'asm_cx':cx0,'simp_cx':sum(1 for o in ops if o[0]=='cx')}
    out=smilp.solve(ops,Ttarget,tlim=tlim,verbose=False)
    res['T%d'%Ttarget]= out is not None
    if out is not None:
        f=fuse(out); res['sched_depth']=depth(f); path=tag+f'_m{Ttarget}.qasm'; write(f,path); res['qasm']=path
    return res
