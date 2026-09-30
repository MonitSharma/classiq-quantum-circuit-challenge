from search import *
from pebble import compile_smart

def independent(terms):
 # derive rank factorization by eliminating x vectors and tracking corresponding y patterns.
 pivots={}
 for x,y in terms:
  while x:
   p=x.bit_length()-1
   if p in pivots:
    bx,by=pivots[p];x^=bx
    # operation: (x xor bx)*y + bx*by = x*y + bx*(by xor y)
    pivots[p]=(bx,by^y)
   else:pivots[p]=(x,y);break
 return list(pivots.values())

@functools.lru_cache(None)
def complexity(t):
 return sum(max(0,2*m.bit_count()-3) for m,v in esop(t,6))

def score(ts):return sum(complexity(x)+complexity(y) for x,y in ts)

if __name__=='__main__':
 ts=independent(row_terms());check_terms(ts);print('rank',len(ts),'cost',score(ts),flush=True)
 best=999999
 for restart in range(20):
  rng=random.Random(restart);curr=ts.copy();s=score(curr)
  for step in range(500):
   i,j=rng.sample(range(len(curr)),2)
   cand=curr.copy();xi,yi=curr[i];xj,yj=curr[j]
   cand[i]=(xi^xj,yi);cand[j]=(xj,yi^yj)
   sc=score(cand)
   temp=max(.1,2*(1-step/500))
   if sc<s or rng.random()<np.exp(min(0,(s-sc)/temp)):curr=cand;s=sc
  check_terms(curr)
  q=compile_smart(curr)
  if q.depth()<best:
   best=q.depth();print(restart,s,best,q.count_ops(),flush=True)
   Path('artifacts/rank.qasm').write_text(qasm2.dumps(q));Path('artifacts/rank_terms.json').write_text(json.dumps(curr))
