from formula import *
import pickle

def substitute(e,rows):
 if isinstance(e,int):return e
 if e[0]=='v':
  out=0
  for b in range(6):
   if rows[e[1]]>>b&1:out=Xor(out,('v',b))
  return out
 if e[0]=='not':return Not(substitute(e[1],rows))
 return (e[0],substitute(e[1],rows),substitute(e[2],rows))

def transform(t,a,b):
 return sum(((t>>(i^(((i>>a)&1)<<b)))&1)<<i for i in range(64))

def optimize(t,steps=80):
 best=formula(t,6);bs=(cost(best),size(best));rng=random.Random(t)
 cur=t;rows=[1<<i for i in range(6)];cs=bs
 for i in range(steps):
  a,b=rng.sample(range(6),2);tt=transform(cur,a,b);rr=rows.copy();rr[b]^=rr[a]
  e=formula(tt,6);s=(cost(e),size(e))
  temp=.6*(1-i/steps)
  if s<cs or rng.random()<np.exp(min(0,(cs[0]-s[0])/max(.1,temp)))*.3:
   cur=tt;rows=rr;cs=s
  if s<bs:
   bs=s;best=substitute(e,rr)
 return best

if __name__=='__main__':
 ts=json.loads(Path('artifacts/rank_terms.json').read_text())
 cache={}
 for t in dict.fromkeys([z for pair in ts for z in pair]):
  e=optimize(t,120);print('cost',cost(formula(t,6)),'->',cost(e),flush=True);cache[t]=e
 Path('artifacts/affine_formulas.pkl').write_bytes(pickle.dumps(cache))
