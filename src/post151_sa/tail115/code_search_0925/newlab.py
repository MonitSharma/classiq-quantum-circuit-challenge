"""newlab.py joint.json outdir : materialize a labeling candidate.
Writes outdir/class_codes.json, loader frames outdir/{x,y}frame.{pkl,lb} (cond star, chosen cols),
and the best kernel phase array outdir/co.npy (several sparsification restarts)."""
import sys, os, json, math, pickle, subprocess
jp, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
J = json.load(open(jp))
base = json.load(open('/work/classiq/artifacts/185/class_codes.json'))
cc = dict(base); cc['xlab'] = J['xlab']; cc['ylab'] = J['ylab']
cpath = os.path.join(outdir, 'class_codes.json'); json.dump(cc, open(cpath, 'w'))
code = r'''
import sys, os, json, math, pickle, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
import gensup as G
from mkD3 import dump
import kgenco as KG
J=json.load(open(sys.argv[1])); out=sys.argv[2]
rng=np.random.default_rng(1)
for side in 'xy':
    m=tuple(J['info'][side]['m'])
    best=None
    for t in range(6):
        D=G.build(side,m,{0:[],1:[0],2:[0]},rng,jit=0.35)
        if D is None: continue
        n=sum(len(D['targets'][i]) for i in range(3))
        if best is None or n<best[0]: best=(n,D)
    D=best[1]
    pickle.dump(D,open(f'{out}/{side}frame.pkl','wb'))
    pl=[(mm,i) for i in range(3) for mm,a in D['targets'][i].items() if abs(a)>1e-12]
    open(f'{out}/{side}frame.lb','w').write('\n'.join([str(len(pl))]+[f'{mm} {i}' for mm,i in pl]+['4',' '.join(str(v) for v in D['req'])])+'\n')
    print(side,'cols',m,'sizes',[len(D['targets'][i]) for i in range(3)],'req',D['req'],flush=True)
bestk=None
for s in range(8):
    r=KG.solve(np.random.default_rng(s))
    if r is None: continue
    k,frac=r
    if KG.check(frac)>1e-9: continue
    if bestk is None or k<bestk[0]: bestk=(k,frac)
np.save(f'{out}/co.npy',bestk[1]*math.pi); print('kernel terms',bestk[0],flush=True)
'''
open(os.path.join(outdir, 'mk.py'), 'w').write(code)
env = dict(os.environ, CLASS_CODES=cpath, CLASSIQ_ROOT='/work/classiq')
r = subprocess.run([sys.executable, os.path.join(outdir, 'mk.py'), os.path.abspath(jp), os.path.abspath(outdir)], env=env, capture_output=True, text=True)
print(r.stdout, r.stderr[-2000:])
