"""Use fully expanded CNF and model conversion for the layered encoder search.
Run with run_bounded.py: the native solver may not release the Python GIL.
Witnesses undergo the original all-64 collision and native-state checks.
"""
import argparse,inspect,json,time
from pathlib import Path
import z3
from pysat.solvers import Solver
import post221_layered_first_products as legacy

def solve_cnf(s):
 goal=z3.Goal();goal.add(s.assertions())
 cnf=z3.Then(z3.With('simplify',blast_distinct=True),z3.With('card2bv',keep_cardinality_constraints=False),z3.With('bit-blast',blast_full=True),'tseitin-cnf')(goal)[0]
 atoms={};clauses=[]
 for expr in cnf:
  if z3.is_true(expr):continue
  if z3.is_false(expr):clauses.append([]);continue
  lits=list(expr.children()) if z3.is_or(expr) else [expr];clause=[]
  for lit in lits:
   neg=z3.is_not(lit);atom=lit.arg(0) if neg else lit
   assert z3.is_const(atom) and z3.is_bool(atom) and not (z3.is_true(atom) or z3.is_false(atom)),atom
   var=atoms.setdefault(str(atom),(len(atoms)+1,atom))[0];clause.append(-var if neg else var)
  clauses.append(clause)
 print('CNF',len(atoms),'variables',len(clauses),'clauses',flush=True)
 with Solver(name='cadical195',bootstrap_with=clauses) as solver:
  ok=solver.solve();solution=set(solver.get_model() or [])
 if not ok:return z3.unsat,None
 # Reconstruct against the original formula as well: the tactic converter
 # alone did not recover all bit-vector wire symbols in the positive control.
 reconstruction=z3.Solver();reconstruction.add(s.assertions())
 reconstruction.add([atom==(var in solution) for var,atom in atoms.values()])
 assert reconstruction.check()==z3.sat, 'SAT assignment cannot be lifted'
 model=reconstruction.model()
 assert all(z3.is_true(model.eval(a,model_completion=True)) for a in s.assertions()),'CNF model failed original constraints'
 return z3.sat,model

source=inspect.getsource(legacy.solve).replace('status=s.check()','status,solved_model=solve_cnf(s)').replace('m=s.model()','m=solved_model')
legacy.__dict__['solve_cnf']=solve_cnf
exec(compile(source,__file__,'exec'),legacy.__dict__)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],default='y');p.add_argument('--layers',type=int,default=2);p.add_argument('--positive-control',action='store_true');a=p.parse_args()
 if a.positive_control:
  row,bad=legacy.solve([v&15 for v in range(64)],1,0,list(range(64)));assert row['status']=='sat' and bad==[]
  a.outdir.mkdir(parents=True);(a.outdir/'positive.json').write_text(json.dumps(row,indent=2));print('positive control: all 64 inputs separate',flush=True)
 else:legacy.run(a.outdir,a.side,a.layers,0,8)
