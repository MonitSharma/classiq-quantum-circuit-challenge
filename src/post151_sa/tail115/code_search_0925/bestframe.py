"""bestframe.py labdir side cols tries : pick the best conditional frame (proxy pre/2.2+L/1.55) over many LP restarts."""
import sys, os, json, pickle, numpy as np, subprocess
d, side, cols, tries = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
code = r'''
import sys, os, pickle, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
import gensup as G
d,side,cols,tries=sys.argv[1],sys.argv[2],tuple(int(c) for c in sys.argv[3].split(',')),int(sys.argv[4])
best=None
for s in range(tries):
    rng=np.random.default_rng(100+s)
    D=G.build(side,cols,{0:[],1:[0],2:[0]},rng,jit=0.35)
    if D is None: continue
    sz=[len(D['targets'][i]) for i in range(3)]
    L=sum(1 for i in (1,2) for m in D['targets'][i] if m&64)
    pre=sum(sz)-L; sc=pre/2.2+L/1.55
    if best is None or sc<best[0]: best=(sc,D,sz,L,pre)
sc,D,sz,L,pre=best
pickle.dump(D,open(f'{d}/{side}frame.pkl','wb'))
pl=[(mm,i) for i in range(3) for mm,a in D['targets'][i].items() if abs(a)>1e-12]
open(f'{d}/{side}frame.lb','w').write('\n'.join([str(len(pl))]+[f'{mm} {i}' for mm,i in pl]+['4',' '.join(str(v) for v in D['req'])])+'\n')
print(side,cols,'sizes',sz,'L',L,'pre',pre,'proxy %.2f'%sc,'req',D['req'])
'''
env=dict(os.environ, CLASS_CODES=os.path.join(d,'class_codes.json'), CLASSIQ_ROOT='/work/classiq')
r=subprocess.run([sys.executable,'-c',code,d,side,cols,str(tries)],env=env,capture_output=True,text=True); print(r.stdout,r.stderr[-1500:])
