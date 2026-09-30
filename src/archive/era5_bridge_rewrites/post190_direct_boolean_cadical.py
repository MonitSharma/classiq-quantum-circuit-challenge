"""Direct global Boolean template using the validated full-CNF solver adapter.
Always execute under run_bounded.py; native SAT cannot honor Python timers.
"""
import argparse,inspect
from pathlib import Path
import post190_direct_boolean_template as direct
from post196_layered_cadical import solve_cnf
source=inspect.getsource(direct.solve).replace('status=solver.check()','status,solved_model=solve_cnf(solver)').replace('m=solver.model()','m=solved_model')
direct.__dict__['solve_cnf']=solve_cnf
exec(compile(source,__file__,'exec'),direct.__dict__)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--rounds',type=int,default=5);a=p.parse_args();direct.run(a.outdir,6,3,30,a.rounds)
