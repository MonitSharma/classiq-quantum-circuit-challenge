"""Independent rank certificate for the kernel-cofactor SAT reduction."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from distributed_ucry import rank
from post224_nonlinear_tags import null_basis
from post258_two_stage_anf import decode


def test_projection_has_exact_annihilator_dimension():
    record=json.loads(Path('artifacts/221/class_codes.json').read_text())
    xl=decode(record['xlab'])
    for perm in [(0,1,2,3,4,5,6,7),(0,1,2,4,3,5,6,7)]:
        xs=[k[0]|perm[v]<<1 for k,v in xl.items()]
        n=len(xs)
        # Independent direct evaluation space of every <=4-degree monomial.
        evaluation=[]
        for mask in range(256):
            if mask.bit_count()>4:continue
            evaluation.append(sum(int(mask&~(y|(x<<4))==0)<<(y*n+i)
                                  for y in range(16) for i,x in enumerate(xs)))
        constraints=[]
        for ym in range(16):
            space=[sum(int(xm&~x==0)<<i for i,x in enumerate(xs))
                   for xm in range(16) if xm.bit_count()<=4-ym.bit_count()]
            for h in null_basis(space,n):
                constraints.append(sum(h<<(y*n) for y in range(16) if y&~ym==0))
        assert all((a&b).bit_count()%2==0 for a in constraints for b in evaluation)
        assert rank(constraints)+rank(evaluation)==16*n
