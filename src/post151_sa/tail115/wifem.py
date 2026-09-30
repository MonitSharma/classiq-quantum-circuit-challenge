"""What-if runs in the fused exact model (FEM) starting from an actual loader pair, with per-wire overrides.
usage: wifem.py DX DY T W seeds 'json overrides {i:{rdy:..,zs:..,zd:..,occmax:..}}' tag"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, subprocess, numpy as np
os.environ.update(STRICT='1',ZOCC='1',FUSE='1'); import paireval as P
DX=P.load(sys.argv[1],0); DY=P.load(sys.argv[2],1); T=int(sys.argv[3]); Wb=sys.argv[4]; seeds=sys.argv[5].split(',')
ov={int(k):v for k,v in json.loads(sys.argv[6]).items()}; tag=sys.argv[7]
co=np.load(f'{ROOT}/artifacts/116/recipes/kernel_co.npy'); terms=[int(m) for m in np.flatnonzero(abs(co)>1e-10) if m]
pl,srdy=P.windows(DX,DY); seq,W8,ST,rdy,unl=pl; rdy=list(rdy)
hz=P.hz_times(DX,DY,W8); occ=P.occupancy(DX,DY,W8)
zs=[(h-1 if h>0 else a) for a,h in zip(srdy,hz)]
zd=[(T+1-h if h>0 else T-a) for a,h in zip(srdy,hz)]
xsd={}; xdd={}
for i,o in ov.items():
    if 'xsdec' in o: xsd[i]=o['xsdec']; continue
    if 'xddec' in o: xdd[i]=o['xddec']; continue
    if 'dec' in o:
        k=o['dec']; o=dict(rdy=rdy[i]-k,zs=zs[i]-k,zd=zd[i]+k,occmax=rdy[i]-k)
    elif 'xdec' in o:
        k=o['xdec']; o=dict(rdy=rdy[i]-k)
    elif 'zdec' in o:
        k=o['zdec']; o=dict(zs=zs[i]-k,zd=zd[i]+k,occmax=rdy[i]-k)
    elif 'inc' in o:
        k=o['inc']; o=dict(rdy=rdy[i]+k,zs=zs[i]+k,zd=zd[i]-k)
    if 'rdy' in o: rdy[i]=o['rdy']
    if 'zs' in o: zs[i]=o['zs']
    if 'zd' in o: zd[i]=o['zd']
    if 'occmax' in o: occ[i]=[l for l in occ[i] if l<=o['occmax']]
ddl=[T-r for r in rdy]
xs=list(rdy)
for i,k in xsd.items(): xs[i]-=k
for i,k in xdd.items(): ddl[i]+=k
zb=[]
for i in range(8):
    for l in occ[i]:
        if l>zs[i]: zb+= [f'{i},{l}',f'{i},{T+1-l}']
j=lambda v:','.join(map(str,v))
inp=f'{WK}/pe/wi_{tag}.in'
open(inp,'w').write('\n'.join([str(len(terms)),' '.join(map(str,terms))]+[f'{a} {b} {c}' for a,b,c in zip(ST,rdy,ddl)])+'\n')
env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',LAW='0.3',ZS=j(zs),ZD=j(zd),XS=j(xs),XD=j(ddl),CS=j(xs),CD=j(ddl),ZBUSY=';'.join(zb))
print(tag,'rdy',rdy,'zs',zs,'zd',zd,flush=True)
for s in seeds:
    r=subprocess.run([P.KB,Wb,'100',s,'0.02',f'{WK}/pe/wi_{tag}_s{s}.out','4','0'],stdin=open(inp),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,env=env)
    mind=min([int(l.split()[-1]) for l in r.stderr.split('\n') if l.startswith('depth') and l.split()[6]==str(len(terms))]+[99])
    print(tag,'seed',s,'rc',r.returncode,'mind',mind,flush=True)
