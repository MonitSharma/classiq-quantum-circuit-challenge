"""Asymmetric FEM what-if: loader pair A at the start, unloader = mirror of pair B at the end.
usage: wimix.py XA YA XB YB T W seeds tag"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, subprocess, numpy as np
os.environ.update(STRICT='1',ZOCC='1',FUSE='1'); import paireval as P
XA,YA,XB,YB=[P.load(p,i) for p,i in zip(sys.argv[1:5],[0,1,0,1])]
T=int(sys.argv[5]); Wb=sys.argv[6]; seeds=sys.argv[7].split(','); tag=sys.argv[8]
co=np.load(f'{ROOT}/artifacts/116/recipes/kernel_co.npy'); terms=[int(m) for m in np.flatnonzero(abs(co)>1e-10) if m]
def side(DX,DY):
    pl,srdy=P.windows(DX,DY); seq,W8,ST,rdy,unl=pl
    hz=P.hz_times(DX,DY,W8); occ=P.occupancy(DX,DY,W8)
    zs=[(h-1 if h>0 else a) for a,h in zip(srdy,hz)]
    ze=[(h if h>0 else a+1) for a,h in zip(srdy,hz)]   # end side: rotations allowed up to T+1-h
    return dict(ST=list(ST),rdy=list(rdy),zs=zs,ze=ze,occ=occ)
A=side(XA,YA); B=side(XB,YB)
# map B to A's plan order by code value
idx=[B['ST'].index(c) for c in A['ST']]
Bm={k:[B[k][j] for j in idx] for k in ('rdy','ze','occ')}
ST=A['ST']; rs=A['rdy']; re=Bm['rdy']
ddl=[T-r for r in re]; zs=A['zs']; zd=[T+1-e for e in Bm['ze']]
zb=[]
for i in range(8):
    zb+=[f'{i},{l}' for l in A['occ'][i] if l>zs[i]]
    zb+=[f'{i},{T+1-l}' for l in Bm['occ'][i] if l>Bm['ze'][i]-1]
j=lambda v:','.join(map(str,v))
inp=f'{WK}/pe/mx_{tag}.in'
# .in rdy column is only used for ordering/meta; windows come from env
open(inp,'w').write('\n'.join([str(len(terms)),' '.join(map(str,terms))]+[f'{a} {b} {c}' for a,b,c in zip(ST,rs,ddl)])+'\n')
env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',LAW='0.3',ZS=j(zs),ZD=j(zd),XS=j(rs),XD=j(ddl),CS=j(rs),CD=j(ddl),ZBUSY=';'.join(zb))
print(tag,'ST',ST,'start',rs,'end',re,'zs',zs,'zd',zd,flush=True)
for s in seeds:
    r=subprocess.run([P.KB,Wb,'100',s,'0.02',f'{WK}/pe/mx_{tag}_s{s}.out','4','0'],stdin=open(inp),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,env=env)
    mind=min([int(l.split()[-1]) for l in r.stderr.split('\n') if l.startswith('depth') and l.split()[6]==str(len(terms))]+[99])
    print(tag,'seed',s,'rc',r.returncode,'mind',mind,flush=True)
