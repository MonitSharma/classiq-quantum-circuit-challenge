import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post190_register_encoder import solve,verify

def test_nonlinear_nine_wire_positive_control():
 row,ops=solve('y',list(range(64)),stages=1,cx_layers=0,seconds=5,synthetic=True)
 assert row['status']=='sat'
 q,r=verify(ops,'y',synthetic=True)
 assert q.num_qubits==9 and r['basis_inputs_checked']==64 and r['max_error']<1e-10
 assert q.depth()<=row['depth_ceiling']
