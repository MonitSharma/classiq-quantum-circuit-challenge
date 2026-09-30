"""Anneal a loader (sa4) so that the 4 code-span wires meet sorted caps, letting junk wires finish late.
usage: spanload.py side src spancaps iters seed [T0] [mu]"""
import pickle, sys, os, subprocess
sys.path.insert(0,'.')
from lbeval2 import load_beam
from sim import check_loader2, symbolic_final
from kdrv import profile
from kgen import span_map
R='../../artifacts/118/recipes/'
BASE={'x':'x_loader_d44','y':'y_loader_d46_blkw'}
side,src,caps,iters,seed=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5])
T0=float(sys.argv[6]) if len(sys.argv)>6 else 0.5; mu=float(sys.argv[7]) if len(sys.argv)>7 else 0.0
D=pickle.load(open(R+BASE[side]+'.pkl','rb'))
if src=='champ': g1=D['gates']
else:
    from lbeval2 import sa4
    bd,seq=load_beam(src); d,pen,g1=sa4(D,seq,tag='sl1',binary=os.environ.get('SA4BIN','./c/sa4'))
init=[(g[1],g[2]) for g in g1 if g[0][0]=='cx']
targets=D['targets']; plist=[(m,i,a) for i in range(3) for m,a in targets[i].items()]
lines=[str(len(plist))]+[f"{m} {i}" for m,i,a in plist]+["0","0",str(len(init))]+[f"{c} {t}" for c,t in init]
env=dict(os.environ); env['SPANREQ']=','.join(map(str,D['req'])); env['SPANCAPS']=caps; env['SPANCAP']=caps.split(',')[0]
env.setdefault('DEPW','0'); env.setdefault('SOFTW','3'); env.setdefault('CAPS',','.join(['58']*9))
out=f'runs/sl_{side}_{seed}.txt'
r=subprocess.run([os.environ.get('SA4BIN','./c/sa4'),str(seed),str(iters),str(T0),'0.02','4',str(mu),out],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=env)
txt=open(out).read().split('\n'); d,pen,L=map(int,txt[0].split()); gates=[]
for line in txt[1:]:
    if not line: continue
    t=line.split()
    if t[0]=='H': gates.append((('h',),int(t[1])))
    elif t[0]=='R': gates.append((('rz',plist[int(t[2])][2]),int(t[1])))
    else: gates.append((('cx',),int(t[1]),int(t[2])))
e,_=profile(gates); rows=symbolic_final(gates); sm=span_map(D['req'])
code=sorted((e[w],sm[rows[w]],w) for w in range(9) if rows[w] in sm)
print('pen',pen,'depth',d,'prof',e,'code(t,span,w)',code, 'ncx',L)
if pen==0 and check_loader2(gates,D['newcode'])['max_dev']<1e-9:
    D2=dict(D); D2['gates']=gates; D2['fix']=[]
    pickle.dump(D2,open(f'runs/sl_{side}_{seed}.pkl','wb')); print('saved')
