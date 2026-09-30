"""gensupc.py side cols condspec n seed outprefix : support frames with a chosen conditioning (e.g. '0:;1:0;2:')"""
import sys, os, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
import gensup as G
from mkD3 import dump
side=sys.argv[1]; cols=tuple(int(c) for c in sys.argv[2].split(',')); cs=sys.argv[3]; n=int(sys.argv[4]); seed=int(sys.argv[5]); pref=sys.argv[6]
cond={}
for part in cs.split(';'):
    k,v=part.split(':'); cond[int(k)]=[int(x) for x in v.split(',') if x!='']
rng=np.random.default_rng(seed); seen=set(); best=None
for t in range(n):
    D=G.build(side,cols,cond,rng,jit=0.35)
    if D is None: continue
    key=tuple(sorted(m for i in range(3) for m in D['targets'][i]))
    if key in seen: continue
    seen.add(key)
    sz=[len(D['targets'][i]) for i in range(3)]
    tag=f'{pref}_{t}'; dump(D,tag); print(tag,'sizes',sz,'total',sum(sz),flush=True)
