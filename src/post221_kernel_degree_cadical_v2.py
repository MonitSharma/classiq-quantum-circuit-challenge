"""Joint class labels and bounded-degree kernel, with exact reachable constraints."""
import argparse,json,time
from functools import reduce
from pathlib import Path
import z3
from post258_raw_parity_codes import cells
from post258_two_stage_anf import decode,encode
import two_stage_oracle as ts

def run(degree,fixed,timeout):
 out=Path(f'artifacts/post221_kernel_degree{degree}_{fixed}_cadical_v2');assert not out.exists();out.mkdir();base=json.loads(Path('artifacts/221/class_codes.json').read_text());yc,xc=cells(ts.ROWCLS,32),cells(ts.COLCLS,48);s=z3.Solver();s.set(timeout=timeout);labs=[]
 for side,cc in [('y',yc),('x',xc)]:
  lab={k:z3.Concat(*[z3.If(z3.Bool(f'label_{side}_{i}_{b}'),z3.BitVecVal(1,1),z3.BitVecVal(0,1)) for b in reversed(range(3))]) for i,k in enumerate(cc)};labs.append(lab)
  for bit in [0,1]:
   keys=[k for k in cc if k[0]==bit];s.add(z3.Distinct(*[lab[k] for k in keys]))
  if fixed==side:
   known=decode(base[f'{side}lab']);s.add([lab[k]==known[k] for k in cc])
  else:
   # Conditional XOR by raw bit is affine, preserving kernel degree.
   for bit in [0,1]:s.add(lab[next(k for k in cc if k[0]==bit)]==0)
 pairs=[(y,x) for y in yc for x in xc];n=len(pairs);zero=z3.BitVecVal(0,n)
 wires=[]
 for side in [0,1]:
  wires.append(z3.BitVecVal(sum(k[side][0]<<i for i,k in enumerate(pairs)),n))
  for bit in range(3):
   parts=[]
   for key,value in labs[side].items():
    mask=sum(1<<i for i,pair in enumerate(pairs) if pair[side]==key);parts.append(z3.If(z3.Extract(bit,bit,value)==1,z3.BitVecVal(mask,n),zero))
   wires.append(reduce(lambda a,b:a|b,parts))
 terms=[m for m in range(256) if m.bit_count()<=degree];coeff=[z3.Bool(f'coef{m}') for m in terms];expr=zero
 for m,on in zip(terms,coeff):
  product=reduce(lambda a,b:a&b,[wires[b] for b in range(8) if m>>b&1],z3.BitVecVal((1<<n)-1,n));expr=expr^z3.If(on,product,zero)
 want=sum(int(ts.logo(xc[x][0],yc[y][0]))<<i for i,(y,x) in enumerate(pairs));s.add(expr==z3.BitVecVal(want,n))
 (out/'problem.smt2').write_text(s.sexpr());start=time.monotonic()
 from pysat.solvers import Solver
 import threading
 goal=z3.Goal();goal.add(s.assertions());cnf=z3.Then(z3.With('simplify',blast_distinct=True),z3.With('card2bv',keep_cardinality_constraints=False),z3.With('bit-blast',blast_full=True),'tseitin-cnf')(goal)[0];names={};clauses=[]
 for expr in cnf:
  if z3.is_true(expr):continue
  if z3.is_false(expr):clauses.append([]);continue
  literals=list(expr.children()) if z3.is_or(expr) else [expr];clause=[]
  for literal in literals:
   neg=z3.is_not(literal);atom=literal.arg(0) if neg else literal
   assert z3.is_const(atom) and z3.is_bool(atom) and not (z3.is_true(atom) or z3.is_false(atom)),atom
   var=names.setdefault(str(atom),len(names)+1);clause.append(-var if neg else var)
  clauses.append(clause)
 with Solver(name='cadical195',bootstrap_with=clauses) as solver:
  timer=threading.Timer(timeout/1000,solver.interrupt);timer.start()
  try:ok=solver.solve_limited(expect_interrupt=True);solution=set(solver.get_model() or []) if ok else set()
  finally:timer.cancel()
 status='sat' if ok else 'unsat' if ok is False else 'unknown';row=dict(degree=degree,fixed=fixed,status=status,backend='cadical195',clauses=len(clauses),variables=len(names),seconds=time.monotonic()-start);print(row,flush=True)
 if ok:
  labels=[{k:sum(int(names.get(f'label_{side}_{i}_{b}',-1) in solution)<<b for b in range(3)) for i,k in enumerate(cc)} for side,cc in [('y',yc),('x',xc)]]
  selected=[m for m,c in zip(terms,coeff) if names.get(str(c),-1) in solution]
  for y,x in pairs:
   w=y[0]|labels[0][y]<<1|x[0]<<4|labels[1][x]<<5;assert sum(m&~w==0 for m in selected)%2==ts.logo(xc[x][0],yc[y][0])
  row.update(ymask=32,xmask=48,ylab=encode(labels[0]),xlab=encode(labels[1]),terms=selected)
 (out/'report.json').write_text(json.dumps(row,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--degree',type=int,default=3);p.add_argument('--fixed',choices=['x','y','none'],default='none');p.add_argument('--timeout-ms',type=int,default=55000);a=p.parse_args();run(a.degree,a.fixed,a.timeout_ms)
