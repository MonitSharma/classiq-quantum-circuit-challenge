"""labanneal.py side iters seed : anneal class labels for the conditional-loader frame proxy depth."""
import sys, json, math, random, numpy as np
sys.path.insert(0,'/work/k'); import labeval as E
side=sys.argv[1]; iters=int(sys.argv[2]); seed=int(sys.argv[3])
rnd=random.Random(seed); rng=np.random.default_rng(seed)
cur={k:v for k,v in (E.XL if side=='x' else E.YL).items()}
K=E.keys(side)
def score(lab):
    r=E.frame_cost(side,lab,rng,reps=1)
    best=min(r,key=lambda d: d['pre']/2.2+d['L']/1.55+0.01*d['total'])
    return best['pre']/2.2+best['L']/1.55+0.01*best['total'], best
cs,cb=score(cur); best=(cs,dict(cur),cb); T=1.0
print('start',round(cs,2),cb,flush=True)
for it in range(iters):
    new=dict(cur)
    p=rnd.choice([0,1]); grp=[k for k in K if k[0]==p]
    if rnd.random()<0.7:
        a,b=rnd.sample(grp,2); new[a],new[b]=new[b],new[a]
    else:
        used={new[k] for k in grp}; free=[l for l in range(8) if l not in used]
        a=rnd.choice(grp); new[a]=rnd.choice(free)
    s,b=score(new); T=1.0*(1-it/iters)+0.05
    if s<cs or rnd.random()<math.exp((cs-s)/T):
        cur,cs,cb=new,s,b
        if s<best[0]:
            best=(s,dict(new),b); print('it',it,'best',round(s,2),b,flush=True)
            json.dump({'side':side,'score':s,'frame':b,'lab':{f'{k[0]},{k[1]}':v for k,v in new.items()}},open(f'/work/k/lab_{side}_{seed}.json','w'))
print('done',best[0],best[2])
