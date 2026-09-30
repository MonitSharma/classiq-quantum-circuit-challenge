"""Adapt our exact oracle to the public PhasePoly cross-block optimizer.

The external optimizer is read from an explicit checkout. Only H/RZ/CX/X
conversion is performed locally; each U3 replacement is checked as a 2x2
operator. Every output is scored after safe native lowering and serialization.
"""
import argparse
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native


def phasepoly_input(q):
    result = QuantumCircuit(q.num_qubits)
    for inst in q.data:
        wires = [q.find_bit(w).index for w in inst.qubits]
        if inst.operation.name == 'cx':
            result.cx(*wires)
            continue
        assert inst.operation.name == 'u3'
        theta, phi, lam = map(float, inst.operation.params)
        one = QuantumCircuit(1)
        def rz(angle):
            angle = (angle + math.pi) % (2*math.pi) - math.pi
            if abs(angle) > 1e-12:
                one.rz(angle, 0)
        if abs(math.sin(theta/2)) < 1e-12:
            rz(phi+lam)
        else:
            if theta < 0:
                theta, phi, lam = -theta, phi+math.pi, lam+math.pi
            if abs(theta-math.pi/2) < 1e-12:
                rz(lam-math.pi)
                one.h(0)
                rz(phi)
            else:
                # U3 = Rz(phi) Ry(theta) Rz(lambda), up to global phase.
                # Ry(theta) = Rz(pi/2) H Rz(theta) H Rz(-pi/2).
                rz(lam-math.pi/2)
                one.h(0)
                rz(theta)
                one.h(0)
                rz(phi+math.pi/2)
        assert Operator(one).equiv(Operator(inst.operation), atol=1e-12, rtol=0)
        result.compose(one, wires, inplace=True)
    lines = ['OPENQASM 2.0;', 'include "qelib1.inc";', f'qreg q[{q.num_qubits}];']
    for inst in result.data:
        wires = [result.find_bit(w).index for w in inst.qubits]
        if inst.operation.name == 'cx':
            lines.append(f'cx q[{wires[0]}],q[{wires[1]}];')
        elif inst.operation.name == 'h':
            lines.append(f'h q[{wires[0]}];')
        else:
            angle = float(inst.operation.params[0])
            fraction = Fraction(angle/math.pi).limit_denominator(1024)
            expression = (f'{fraction.numerator}*pi/{fraction.denominator}'
                          if abs(float(fraction)*math.pi-angle) < 1e-12 else repr(angle))
            lines.append(f'rz({expression}) q[{wires[0]}];')
    return '\n'.join(lines)+'\n'


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    source = a.source.read_text()
    q = qasm2.loads(source)
    converted = phasepoly_input(q)
    input_path = a.outdir/'input.qasm'
    input_path.write_text(converted)
    back = native(qasm2.loads(converted))
    control = a.outdir/'conversion_control.qasm'
    control.write_text(qasm2.dumps(back))
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  repository=str(a.repo), commit=subprocess.check_output(['git','-C',str(a.repo),
                    'rev-parse','HEAD'],text=True).strip(), method=a.method, heap=a.heap,
                  ends=a.ends, group=a.group, conversion_depth=back.depth(),
                  conversion_cx=back.count_ops().get('cx',0))
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('conversion', back.depth(), back.count_ops(), flush=True)
    sys.path.insert(0, str(a.repo))
    from src.phasepoly import phasepoly_synthesize
    output = a.outdir/'phasepoly.qasm'
    outcome = phasepoly_synthesize(str(input_path.resolve()), str(output.resolve()),
                                  method=a.method, heap_size=a.heap, ends_checked=a.ends,
                                  group_size=a.group, circuit_name='classiq188')
    report['phasepoly'] = asdict(outcome)
    lowered = native(qasm2.load(output))
    path = a.outdir/f'candidate_d{lowered.depth()}_cx{lowered.count_ops().get("cx",0)}.qasm'
    path.write_text(qasm2.dumps(lowered))
    report['candidate'] = dict(depth=lowered.depth(), cx=lowered.count_ops().get('cx',0),
                                u3=lowered.count_ops().get('u3',0), path=str(path))
    (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('candidate', report['candidate'], flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/188/two_stage_188.qasm'))
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--method', default='row_heap')
    p.add_argument('--heap', type=int, default=32)
    p.add_argument('--ends', type=int, default=8)
    p.add_argument('--group', type=int, default=3)
    run(p.parse_args())
