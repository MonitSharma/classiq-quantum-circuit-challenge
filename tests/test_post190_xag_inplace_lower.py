import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post190_xag_inplace_lower import check
from post190_degree_rank_bound import targets,certificate


def test_synthetic_witness_fits_nine_wires_and_uncomputes():
 w=json.loads(Path('artifacts/post190_inplace_xag_lower/synthetic_witness.json').read_text())
 r=check(w)
 assert r['width']==9 and r['encoder_depth']==24
 assert r['max_error']<1e-10 and r['basis_inputs_checked']==64


def test_protected_degree_rank_certificate():
 for t in targets().values():
  c=certificate(t)
  assert c['bound']==6
  assert next(r for r in c['rows'] if r['min_degree']==5)['rank']==3
  # Independently reconstruct each truth table from its ANF.
  for target,a in zip(t,c['anf']):
   assert all((sum(a[m] for m in range(64) if m&~x==0)%2)==target[x] for x in range(64))
  # Every nonzero XOR of outputs has degree >=5.
  for sel in range(1,8):
   a=[sum(c['anf'][b][m] for b in range(3) if sel>>b&1)%2 for m in range(64)]
   assert max(m.bit_count() for m,v in enumerate(a) if v)>=5
