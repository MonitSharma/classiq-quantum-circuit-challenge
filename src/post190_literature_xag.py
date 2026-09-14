"""Research-guided normal-form SAT search, separate from running old solvers.

Constant normalization, commutative operand order and nonsubset fanins follow
Soeken, arXiv:2005.01778, Sections I and III-B. Local degree-rank clauses apply
only to the protected multioutput functions whose projection has rank three.
Native solver calls must run through run_bounded.py for a wall-clock limit.
"""
import argparse,json,time,itertools
from pathlib import Path
from pysat.solvers import Cadical153
from post190_exact_xag import build as base_build,xor_chain
from post190_degree_rank_bound import targets,certificate
from post190_xag_inplace_lower import outputs


def lex_less(cnf,pool,a,b):
 eq=pool.id();cnf.append([eq])
 for x,y in reversed(list(zip(a,b))):
  cnf.append([-eq,-x,y])
  nxt=pool.id()
  cnf.extend([[-nxt,eq],[-nxt,-x,y],[-nxt,x,-y],[-eq,-x,-y,nxt],[-eq,x,y,nxt]])
  eq=nxt
 cnf.append([-eq])


def non_subset(cnf,pool,a,b):
 ds=[]
 for x,y in zip(a,b):
  d=pool.id();cnf.extend([[-d,x],[-d,-y],[d,-x,y]]);ds.append(d)
 cnf.append(ds)


def build(ts,k,depth=None):
 cnf,pool,aa,bb,oo=base_build(ts,k)
 for j,((a,ca),(b,cb)) in enumerate(zip(aa,bb)):
  cnf.extend([[-ca],[-cb]])
  lex_less(cnf,pool,a,b);non_subset(cnf,pool,a,b);non_subset(cnf,pool,b,a)
  users=[group[0][6+j] for pair in zip(aa[j+1:],bb[j+1:]) for group in pair]+[o[0][6+j] for o in oo]
  cnf.append(users)
 for t,(_,c) in zip(ts,oo):cnf.append([c] if t[0] else [-c])
 if len(ts)==3 and next(r for r in certificate(ts)['rows'] if r['min_degree']==5)['rank']==3:
  # No nonzero XOR of output rows may cancel all ANDs after the first three.
  for subset in range(1,8):
   differences=[]
   for j in range(3,k):
    kind,v=xor_chain(cnf,pool,[oo[b][0][6+j] for b in range(3) if subset>>b&1],False)
    assert kind=='lit';differences.append(v)
   cnf.append(differences)
 if depth is not None:
  levels=[[pool.id() for _ in range(depth)] for j in range(k)]
  for ls in levels:
   cnf.append(ls)
   for a,b in itertools.combinations(ls,2):cnf.append([-a,-b])
  for j in range(k):
   for prev in range(j):
    for sel in (aa[j][0][6+prev],bb[j][0][6+prev]):
     for pj in range(depth):
      for pp in range(pj,depth):cnf.append([-sel,-levels[j][pj],-levels[prev][pp]])
 return cnf,pool,aa,bb,oo


def solve(ts,k,depth=None):
 cnf,pool,aa,bb,oo=build(ts,k,depth);print('CNF',pool.top,len(cnf),flush=True);start=time.monotonic()
 with Cadical153(bootstrap_with=cnf) as s:
  status=s.solve();r=dict(status='SAT' if status else 'UNSAT_normal_form',seconds=time.monotonic()-start,variables=pool.top,clauses=len(cnf),and_nodes=k,and_depth_limit=depth)
  if status:
   model={v for v in s.get_model() if v>0}
   def dec(spec):return ([i for i,v in enumerate(spec[0]) if v in model],spec[1] in model)
   w=dict(k=k,gates=[dict(a=dec(a),b=dec(b)) for a,b in zip(aa,bb)],outs=[dec(o) for o in oo])
   assert all(outputs(w,x)==[t[x] for t in ts] for x in range(64)), 'invalid Boolean witness'
   r['witness']=w;r['checked_inputs']=64
 return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--k',type=int,required=True);p.add_argument('--depth',type=int);p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True)
 ts=targets()[a.side];r=solve(ts,a.k,a.depth);(a.outdir/'report.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='witness'},flush=True)
 if 'witness' in r:(a.outdir/'witness.json').write_text(json.dumps(r['witness'],indent=2))
