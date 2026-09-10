import pickle
from pathlib import Path
import xag
from formula import formula as original_formula
from xag_phase import *
cache=pickle.loads(Path('artifacts/affine_formulas.pkl').read_bytes())
xag.formula=lambda t,n:cache.get(t,original_formula(t,n))
if __name__=='__main__':
 ts=json.loads(Path('artifacts/rank_terms.json').read_text())
 q,ch=build_best(ts);qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 print('result',qc.depth(),qc.count_ops(),flush=True)
 Path('artifacts/xag_affine.qasm').write_text(qasm2.dumps(qc))
 Path('artifacts/xag_affine_choices.pkl').write_bytes(pickle.dumps(ch))
