"""Check implicit dictionary orientation and a saved exact phase representation."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post196_quadratic_omp import fwht
from post196_quadratic_block_basis import S
from post196_quadratic_tensor import axis_apply
from two_stage_oracle import logo

def test_fwht_matches_explicit_sign_dictionary():
 v=np.random.default_rng(14).normal(size=64)
 expected=np.array([sum(x*(-1)**((m&w).bit_count()%2) for w,x in enumerate(v)) for m in range(64)])
 assert np.max(abs(fwht(v)-expected))<1e-12

def test_saved_coupled_basis_has_the_exact_logo_phase():
 r=json.loads(Path('artifacts/post196_block_basis/best.json').read_text());co=np.array(r['coefficients'])
 for axis,basis in enumerate(r['bases']):co=axis_apply(co,S[:,basis],axis)
 desired=np.zeros((16,)*3)
 for idx in np.ndindex(desired.shape):
  w=sum(((v>>i)&1)<<bit for v,group in zip(idx,r['groups']) for i,bit in enumerate(group));desired[idx]=logo(w&63,w>>6)
 diff=co-desired
 assert np.max(abs((diff-diff.flat[0]+1)%2-1))<1e-12
