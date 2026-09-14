import sys,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pysat.formula import IDPool
from pysat.solvers import Cadical153
from post190_literature_xag import lex_less,solve

def test_lex_order_exhaustive():
 p=IDPool();a=[p.id() for _ in range(4)];b=[p.id() for _ in range(4)];c=[];lex_less(c,p,a,b)
 with Cadical153(bootstrap_with=c) as s:
  for x in range(16):
   for y in range(16):
    assumptions=[v if z>>i&1 else -v for group,z in [(a,x),(b,y)] for i,v in enumerate(group)]
    assert s.solve(assumptions=assumptions)==(x<y)

def test_normalization_and_nonlinear_known_functions():
 functions=[lambda x:sum((x>>i)&1 for i in range(3))>=2,lambda x: not(sum((x>>i)&1 for i in range(3))>=2)]
 for f in functions:
  t=[int(f(x)) for x in range(64)];r=solve([t],1)
  assert r['status']=='SAT' and r['checked_inputs']==64
 t=[int(x&7==7) for x in range(64)]
 assert solve([t],1)['status']=='UNSAT_normal_form'
 assert solve([t],2)['status']=='SAT'
