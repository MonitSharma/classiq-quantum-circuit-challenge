"""Eliminate kernel coefficients before solving bounded-degree class labels.

For fixed x labels, each y-ANF coefficient must lie in the evaluation span
of x monomials of the complementary degree. This avoids coefficient-label
products in the direct SAT formulation.
"""
import argparse,itertools,json,time
from functools import reduce
from pathlib import Path
import z3
from post224_nonlinear_tags import null_basis
from post258_two_stage_anf import encode,decode,ORDER
from post258_raw_parity_codes import cells,poly
import two_stage_oracle as ts

def run(degree,timeout):
 out=Path(f'artifacts/post221_cofactor_degree{degree}_cadical_v2');assert not out.exists();out.mkdir();r=json.loads(Path('artifacts/221/class_codes.json').read_text());xl=decode(r['xlab']);yc,xc=cells(ts.ROWCLS,32),cells(ts.COLCLS,48);xs=list(xc);xvalues=[k[0]|xl[k]<<1 for k in xs];n=len(xs);s=z3.Solver();s.set(timeout=timeout)
 B=[z3.BitVec(f'B{i}',n) for i in range(16)];assign={};yk=list(yc)
 for y in yk:
  bs=[z3.Bool(f'assign{yk.index(y)}_{code}') for code in range(8)];assign[y]=bs;s.add(z3.PbEq([(b,1) for b in bs],1));want=sum(int(ts.logo(xc[x][0],yc[y][0]))<<i for i,x in enumerate(xs))
  for code,b in enumerate(bs):s.add(z3.Implies(b,B[y[0]|code<<1]==want))
 for raw in [0,1]:
  keys=[k for k in yk if k[0]==raw]
  for code in range(8):s.add(z3.PbLe([(assign[k][code],1) for k in keys],1))
  s.add(assign[keys[0]][0])
  if raw==0:
   s.add(assign[keys[1]][1],assign[keys[2]][2])
 constraints=0
 for m in range(16):
  d=degree-m.bit_count()
  space=[sum(int(j&~v==0)<<i for i,v in enumerate(xvalues)) for j in range(16) if j.bit_count()<=d]
  nulls=null_basis(space,n);expr=reduce(lambda a,b:a^b,[B[v] for v in range(16) if v&~m==0])
  for h in nulls:
   bits=[z3.Extract(i,i,expr) for i in range(n) if h>>i&1];s.add(reduce(lambda a,b:a^b,bits)==0);constraints+=1
 (out/'problem.smt2').write_text(s.sexpr())
 start=time.monotonic()
 from pysat.solvers import Solver
 import threading
 goal=z3.Goal();goal.add(s.assertions());cnf=z3.Then('simplify',z3.With('card2bv',keep_cardinality_constraints=False),'bit-blast','tseitin-cnf')(goal)[0];names={};clauses=[]
 for expr in cnf:
  if z3.is_true(expr):continue
  literals=list(expr.children()) if z3.is_or(expr) else [expr];clause=[]
  for literal in literals:
   neg=z3.is_not(literal);atom=literal.arg(0) if neg else literal;assert z3.is_const(atom) and z3.is_bool(atom), atom;name=str(atom);var=names.setdefault(name,len(names)+1);clause.append(-var if neg else var)
  clauses.append(clause)
 with Solver(name='cadical195',bootstrap_with=clauses) as solver:
  timer=threading.Timer(timeout/1000,solver.interrupt);timer.start()
  try:ok=solver.solve_limited(expect_interrupt=True);solution=set(solver.get_model() or []) if ok else set()
  finally:timer.cancel()
 status='sat' if ok else 'unsat' if ok is False else 'unknown'
 row=dict(degree=degree,fixed='x',status=status,backend='cadical195',clauses=len(clauses),variables=len(names),constraints=constraints,seconds=time.monotonic()-start);print(row,flush=True)
 if ok:
  yl={k:next(i for i,b in enumerate(bs) if names[str(b)] in solution) for k,bs in assign.items()};sol=poly(yl,xl,yc,xc);terms=[m for i,m in enumerate(ORDER) if sol>>i&1];assert max(m.bit_count() for m in terms)<=degree
  for y in yc:
   for x in xc:
    w=y[0]|yl[y]<<1|x[0]<<4|xl[x]<<5;assert sum(m&~w==0 for m in terms)%2==ts.logo(xc[x][0],yc[y][0])
  row.update(ymask=32,xmask=48,ylab=encode(yl),xlab=encode(xl),terms=terms)
 (out/'report.json').write_text(json.dumps(row,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--degree',type=int,default=4);p.add_argument('--timeout-ms',type=int,default=55000);a=p.parse_args();run(a.degree,a.timeout_ms)
