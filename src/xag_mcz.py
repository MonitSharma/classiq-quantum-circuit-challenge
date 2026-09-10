import xag_phase
from mcz import phase_cube
xag_phase.phase_cube=phase_cube
from xag_affine import *
if __name__=='__main__':
 ts=json.loads(Path('artifacts/rank_terms.json').read_text())
 q,ch=build_best(ts);qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 if q.depth()<qc.depth():qc=q
 print('result',qc.depth(),qc.count_ops(),flush=True)
 Path('artifacts/xag_mcz.qasm').write_text(qasm2.dumps(qc));Path('artifacts/xag_mcz_choices.pkl').write_bytes(pickle.dumps(ch))
