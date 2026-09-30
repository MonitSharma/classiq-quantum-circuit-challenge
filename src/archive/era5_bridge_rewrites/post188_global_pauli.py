"""Depth-weighted whole-oracle Pauli resynthesis with restored wire identities.

Prior saved whole-circuit passes omitted GreedyPauliSimp. Use complete oracle
verification, never a dense 18-qubit Operator allocation, for every contender.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from qiskit import qasm2
from pytket.qasm import circuit_from_qasm, circuit_to_qasm
from pytket.passes import GreedyPauliSimp, PauliSimp, FullPeepholeOptimise, CliffordSimp, OptimisePhaseGadgets
from pytket.transform import PauliSynthStrat, CXConfigType
from distributed_frame_search import native
from post188_phasepoly_probe import phasepoly_input


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    start = time.monotonic()
    converted = a.outdir/'input_h_rz.qasm'
    converted.write_text(phasepoly_input(qasm2.load(a.source)))
    circuit = circuit_from_qasm(str(converted))
    config = dict(discount_rate=a.discount,depth_weight=a.depth_weight,
                  max_lookahead=a.lookahead,max_tqe_candidates=a.candidates,
                  seed=a.seed,allow_zzphase=False,thread_timeout=a.seconds,
                  only_reduce=False,trials=1)
    print('Pauli config',config,flush=True)
    if a.method == 'greedy':
        compiler_pass = GreedyPauliSimp(**config)
    elif a.method == 'pauli_sets':
        compiler_pass = PauliSimp(PauliSynthStrat.Sets, CXConfigType.Tree)
    elif a.method == 'pauli_pairs':
        compiler_pass = PauliSimp(PauliSynthStrat.Pairwise, CXConfigType.Tree)
    elif a.method == 'peephole':
        compiler_pass = FullPeepholeOptimise(allow_swaps=False)
    elif a.method == 'clifford':
        compiler_pass = CliffordSimp(allow_swaps=False)
    else:
        compiler_pass = OptimisePhaseGadgets(CXConfigType.Tree)
    compiler_pass.apply(circuit)
    permutation = {str(k):str(v) for k,v in circuit.implicit_qubit_permutation().items()}
    circuit.replace_implicit_wire_swaps()
    assert all(k==v for k,v in circuit.implicit_qubit_permutation().items())
    raw = a.outdir/'pauli.qasm'
    circuit_to_qasm(circuit,str(raw))
    q = native(qasm2.load(raw, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS))
    text = qasm2.dumps(q)
    q = qasm2.loads(text)
    path = a.outdir/f'oracle_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm'
    path.write_text(text)
    report = dict(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  config=config,method=a.method,implicit_permutation_materialized=permutation,
                  depth=q.depth(),cx=q.count_ops().get('cx',0),u3=q.count_ops().get('u3',0),
                  width=q.num_qubits,path=str(path),seconds=time.monotonic()-start)
    (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report,flush=True)
    # Deep regressions are measurements only. Verify every contender on the
    # full promised input domain, without allocating an 18-qubit Operator.
    if q.depth() <= 200:
        from exhaustive_verify import exhaustive
        exhaustive(path)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=Path('artifacts/188/two_stage_188.qasm'))
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--depth-weight',type=float,default=1.)
    p.add_argument('--discount',type=float,default=.7)
    p.add_argument('--seconds',type=int,default=20)
    p.add_argument('--lookahead',type=int,default=200)
    p.add_argument('--candidates',type=int,default=100)
    p.add_argument('--method',choices=['greedy','pauli_sets','pauli_pairs','peephole','clifford','gadgets'],default='greedy')
    run(p.parse_args())
