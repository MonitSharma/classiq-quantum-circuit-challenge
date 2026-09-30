"""Bounded two-layer Boolean encoder search with first-layer group symmetry.
Requires three first-layer products. Canonical ordering removes permutation
copies within this restricted family; it is not a universal encoder model.
"""
import argparse,inspect
from pathlib import Path
import post221_layered_first_products as legacy
from post196_layered_cadical import solve_cnf
# Importing the adapter installs its solver; load original source from disk so
# the transformation is explicit and independent of inspect line metadata.
text=Path('src/post221_layered_first_products.py').read_text()
start=text.index('def solve(');end=text.index('\ndef run(',start)
source=text[start:end]
source=source.replace('status=s.check()','status,solved_model=solve_cnf(s)').replace('m=s.model()','m=solved_model')
needle='en=[z3.Bool(f\'en_{stage}_{g}\') for g in range(3)];enabled.append(en);regs=regs.copy()'
replacement=needle+'''
            if stage==0:
                s.add(en)
                groups=[z3.Concat(*[z3.If(z3.Or(a[3*g][j],a[3*g+1][j]),z3.BitVecVal(1,1),z3.BitVecVal(0,1)) for j in range(6)]) for g in range(3)]
                s.add(z3.UGT(groups[0],groups[1]),z3.UGT(groups[1],groups[2]))
'''
assert needle in source;source=source.replace(needle,replacement)
legacy.__dict__['solve_cnf']=solve_cnf;exec(compile(source,__file__,'exec'),legacy.__dict__)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--layers',type=int,default=2);a=p.parse_args();legacy.run(a.outdir,a.side,a.layers,0,8)
