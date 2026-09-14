import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post190_xag_register_schedule import search,lower,verify,basis
from post190_register_compose import validate_encoder

def test_gf2_rank_counterexample():
 assert len(basis([3,5,6]))==2

def test_four_internal_nodes_with_three_ancillas():
 w=json.loads(Path('artifacts/post190_register_schedule_four_internal/witness.json').read_text())
 r=search(w);assert r['status']=='found' and r['toggles']==8
 q=lower(w,r);report=verify(w,q)
 assert report['width']==9 and report['basis_inputs_checked']==64 and report['max_error']<1e-10
 with pytest.raises(AssertionError):validate_encoder(q,'y')

def test_model_exhaustion_is_not_a_depth_claim():
 w=json.loads(Path('artifacts/post190_register_schedule_toy7/witness.json').read_text())
 r=search(w);assert r['status']=='exhausted_restricted_model'
 assert 'depth' not in r
