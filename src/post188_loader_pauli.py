"""Apply depth-weighted Pauli synthesis to 9-wire loaders and verify full operators."""
import argparse
import json
from pathlib import Path
import time

from qiskit import qasm2
from qiskit.quantum_info import Operator
from pytket.qasm import circuit_from_qasm, circuit_to_qasm
from pytket.passes import GreedyPauliSimp
from post188_phasepoly_probe import phasepoly_input
from post188_sparse_code_revisit import loader
from post188_joint_phase_loader import values_for
from post224_relative_lookup import relative
from distributed_frame_search import native
import math
import numpy as np


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    if a.family == 'protected':
        values = values_for(a.side)
        table = np.array([[math.pi*(v>>b&1) for v in values] for b in range(3)])
        original = relative(table,298 if a.side=='y' else 506)[0]
        if a.side == 'x': original.cx(5,4)
        meta = dict(depth=original.depth(),cx=original.count_ops().get('cx',0))
    else:
        row = json.loads(Path('artifacts/post196_frontier_v1/frontier.json').read_text())[2]
        original,meta = loader(row[a.side+'code'],32 if a.side=='y' else row['x_rho'],12)
    source = a.outdir/'source.qasm'
    source.write_text(qasm2.dumps(original))
    converted = a.outdir/'source_h_rz.qasm'
    converted.write_text(phasepoly_input(original))
    c = circuit_from_qasm(str(converted))
    started = time.monotonic()
    GreedyPauliSimp(depth_weight=a.weight,discount_rate=.7,max_lookahead=200,
                    max_tqe_candidates=100,seed=a.seed,thread_timeout=30,
                    only_reduce=False,trials=1).apply(c)
    c.replace_implicit_wire_swaps()
    assert all(k==v for k,v in c.implicit_qubit_permutation().items())
    path = a.outdir/'pauli.qasm'
    circuit_to_qasm(c,str(path))
    q = native(qasm2.load(path,custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS))
    out = a.outdir/f'loader_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm'
    out.write_text(qasm2.dumps(q))
    q = qasm2.load(out)
    aop,bop = Operator(original).data,Operator(q).data
    phase = np.vdot(aop,bop)
    error = float(np.max(abs(bop-phase/abs(phase)*aop)))
    assert error < 1e-10,error
    result = dict(family=a.family,side=a.side,weight=a.weight,seed=a.seed,original=meta,
                  depth=q.depth(),cx=q.count_ops().get('cx',0),error=error,path=str(out),
                  seconds=time.monotonic()-started)
    (a.outdir/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--family',choices=['protected','sparse'],default='protected')
    p.add_argument('--side',choices=['x','y'],required=True)
    p.add_argument('--weight',type=float,default=1.)
    p.add_argument('--seed',type=int,default=0)
    run(p.parse_args())
