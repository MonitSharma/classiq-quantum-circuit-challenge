"""Replay exactly the rotation/occupancy rules used by kbeam_t3."""
import numpy as np

def build_kernel(pl,path,co,env):
    seq,wires,home,_,_=pl
    assert not seq,'FEM occupancy must include any fixup sequence'
    read=lambda key:list(map(int,env[key].split(',')))
    zs,zd=read('ZS'),read('ZD');cs,cd=read('CS'),read('CD');xs,xd=read('XS'),read('XD')
    busy={tuple(map(int,x.split(','))) for x in env.get('ZBUSY','').split(';') if x}
    terms=set(map(int,np.flatnonzero(abs(co)>1e-10)));terms.discard(0)
    rows=list(home);done=set();pending={};body=[]
    for i,row in enumerate(rows):
        if row in terms and row not in done:done.add(row);pending[i]=row
    lines=open(path).read().splitlines();n,tau0=map(int,lines[0].split())
    for k in range(1,n+1):
        values=list(map(int,lines[k].split()));pairs=[tuple(values[1+2*j:3+2*j]) for j in range(values[0])]
        tau=tau0+k;used={w for p in pairs for w in p};assert len(used)==2*len(pairs)
        for w in list(pending):
            if w not in used and zs[w]<tau<=zd[w] and (w,tau) not in busy:
                body.append(('R',wires[w],2*co[pending.pop(w)]))
        for c,t in pairs:
            assert t not in pending
            assert cs[c]<tau<=cd[c] and xs[t]<tau<=xd[t]
            body.append(('C',wires[c],wires[t]))
        updates=[(t,rows[t]^rows[c]) for c,t in pairs]
        for t,v in updates:
            rows[t]=v
            if v in terms and v not in done:done.add(v);pending[t]=v
    assert not pending and done==terms and rows==list(home),(pending,len(done),rows)
    return [('S',list(range(18)))]+body
