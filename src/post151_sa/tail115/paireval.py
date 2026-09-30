"""Loader pair -> plan -> calibrated kernel beam at T -> assemble -> canc -> exact MILP.
usage: paireval.py DX.pkl|champ DY.pkl|champ T W seeds [tag]"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, pickle, json, subprocess, time, numpy as np
os.chdir(PS)
os.environ.setdefault('CLASS_CODES',f'{ROOT}/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT',ROOT)
from kgen import plan
import ev116, kdrv, smilp
from postopt import parse_ops, fuse, depth, write
from canc import simplify
CH=pickle.load(open('sat116/champ117.pkl','rb'))
KB=f'{WK}/kbeam_t3'
def load(p,i): return CH[i] if p=='champ' else pickle.load(open(p,'rb'))
def lay(g,NV=9,withH=False):
    wt=[0]*NV; lu=[False]*NV; lt=[0]*NV; hz=[0]*NV
    for x in g:
        if x[0][0]=='cx':
            c,t=x[1],x[2]; l=max(wt[c],wt[t])+1; wt[c]=wt[t]=l; lu[c]=lu[t]=False; lt[t]=l
        else:
            w=x[1]
            if not lu[w]: wt[w]+=1; lu[w]=True
            if x[0][0]=="h" and wt[w]>1: hz[w]=wt[w]
    return (wt,lt,hz) if withH else (wt,lt)
def hz_times(DX,DY,W8):
    _,_,hx=lay(DX['gates']+[(('cx',),c,t) for c,t in DX.get('fix',[])],withH=True)
    _,_,hy=lay(DY['gates']+[(('cx',),c,t) for c,t in DY.get('fix',[])],withH=True)
    return [hy[W8[i]-9] if i<4 else hx[W8[i]] for i in range(8)]
def occupancy(DX,DY,W8):
    occ=[]
    for i in range(8):
        D,w=(DY,W8[i]-9) if i<4 else (DX,W8[i])
        g=D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
        NV=9; wt=[0]*NV; lu=[False]*NV; used=set()
        for x in g:
            if x[0][0]=='cx':
                c,t=x[1],x[2]; l=max(wt[c],wt[t])+1; wt[c]=wt[t]=l; lu[c]=lu[t]=False
                if w in (c,t): used.add(l)
            else:
                v=x[1]
                if not lu[v]: wt[v]+=1; lu[v]=True
                if v==w and not os.environ.get('FUSE'): used.add(wt[v])
        occ.append(sorted(used))
    return occ
def windows(DX,DY):
    pl=plan(DX,DY); seq,W8,ST,rdy,unl=pl
    wx,lx=lay(DX['gates']+[(('cx',),c,t) for c,t in DX.get('fix',[])])
    wy,ly=lay(DY['gates']+[(('cx',),c,t) for c,t in DY.get('fix',[])])
    srdy=[]; chk=[]
    for i in range(8):
        if i<4: w=W8[i]-9; srdy.append(ly[w]); chk.append(wy[w])
        else: w=W8[i]; srdy.append(lx[w]); chk.append(wx[w])
    assert chk==list(rdy), (chk,rdy)
    if os.environ.get('STXOR'):   # relabeled loaders (mkrelabel.py): kernel start/home rows ST[i] ^= mask
        ST=list(ST)
        for i,m in json.loads(os.environ['STXOR']).items(): ST[int(i)]^=m
        pl=(seq,W8,ST,rdy,unl)
    return pl,srdy
def run(DX,DY,T,Wb,seeds,tag,co_path=f'{ROOT}/artifacts/116/recipes/kernel_co.npy',milp=True):
    co=np.load(co_path); terms=[int(m) for m in np.flatnonzero(abs(co)>1e-10) if m]
    pl,srdy=windows(DX,DY); seq,W8,ST,rdy,unl=pl
    assert not seq
    zd=None
    if os.environ.get('STRICT'):
        hz=hz_times(DX,DY,W8)
        if os.environ.get('FUSE'):
            zs=[(h-1 if h>0 else a) for a,h in zip(srdy,hz)]
            zd=[(T+1-h if h>0 else T-a) for a,h in zip(srdy,hz)]
            srdy=zs
        else: srdy=[max(a,b) for a,b in zip(srdy,hz)]
    ddl=[T-r for r in rdy]
    inp=f'{WK}/pe/{tag}.in'; os.makedirs(f'{WK}/pe',exist_ok=True)
    open(inp,'w').write('\n'.join([str(len(terms)),' '.join(map(str,terms))]+[f'{a} {b} {c}' for a,b,c in zip(ST,rdy,ddl)])+'\n')
    j=lambda v:','.join(map(str,v))
    env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',LAW='0.3',ZS=j(srdy),ZD=j(zd if zd else ddl),XS=j(rdy),XD=j(ddl),CS=j(rdy),CD=j(ddl))
    if os.environ.get('ZOCC'):
        occ=occupancy(DX,DY,W8); zb=[]
        for i in range(8):
            for l in occ[i]:
                if l>srdy[i]: zb.append(f'{i},{l}'); zb.append(f'{i},{T+1-l}')
        print('ZS',srdy,'ZD',zd,flush=True)
        env['ZBUSY']=';'.join(zb); print('ZBUSY',env['ZBUSY'],flush=True)
    res=dict(tag=tag,T=T,rdy=rdy,srdy=srdy,ST=ST)
    for s in seeds:
        out=f'{WK}/pe/{tag}_s{s}.out'
        if os.path.exists(out): os.remove(out)
        r=subprocess.run([KB,str(Wb),'100',str(s),'0.02',out,'4','0'],stdin=open(inp),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,env=env)
        mind=min([int(l.split()[-1]) for l in r.stderr.split('\n') if l.startswith('depth') and l.split()[6]==str(len(terms))]+[99])
        res[f's{s}']=dict(rc=r.returncode,mind=mind)
        print(tag,'seed',s,'rc',r.returncode,'mind',mind,flush=True)
        if r.returncode==0 and milp:
            ev116.CO=co; ev116.KTERMS=terms; kdrv.CO=co
            kg=ev116.build_kg_s(pl,out,srdy,T)
            q=out.replace('.out','_asm.qasm'); d0,cx0=ev116.assemble(DX,DY,kg,q)
            ops=fuse(simplify(fuse(parse_ops(q)),verbose=False))
            for TT in (T,T+1):
                sol=smilp.solve(ops,TT,tlim=300,verbose=False)
                print(tag,'seed',s,'asm',d0,'cx',sum(1 for o in ops if o[0]=='cx'),'MILP',TT,sol is not None,flush=True)
                if sol is not None:
                    f=fuse(sol); path=out.replace('.out',f'_m{TT}.qasm'); write(f,path); res[f's{s}'][f'T{TT}']=path; break
    return res
if __name__=='__main__':
    dx,dy=sys.argv[1],sys.argv[2]; T=int(sys.argv[3]); Wb=int(sys.argv[4]); seeds=sys.argv[5].split(','); tag=sys.argv[6] if len(sys.argv)>6 else 'pair'
    DX=load(dx,0); DY=load(dy,1)
    print(json.dumps(run(DX,DY,T,Wb,seeds,tag)))
