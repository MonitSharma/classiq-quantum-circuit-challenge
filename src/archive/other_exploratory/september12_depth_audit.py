"""Read-only baseline audit and bounded alternative-loader diagnostic.

Writes a new JSON report only; never runs historical search entry points.
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import UCGate
from qiskit.quantum_info import Operator

from level_oracle import LEVEL, TRIPLE_DEFAULT, check_identity, code_of
from search import MASK


def fwht(values):
    a = np.asarray(values, dtype=np.int64).copy()
    h = 1
    while h < len(a):
        for start in range(0, len(a), 2 * h):
            lo = a[start:start+h].copy()
            hi = a[start+h:start+2*h].copy()
            a[start:start+h] = lo + hi
            a[start+h:start+2*h] = lo - hi
        h *= 2
    return a


def main(out):
    assert not out.exists(), 'Choose a new report filename'
    notebook_path = Path('classiq-challenge-baseline (1).ipynb')
    notebook = json.loads(notebook_path.read_text())
    # Extract only the pure local metric function, without executing SDK cells.
    metric_node = next(node for cell in notebook['cells'] if cell['cell_type'] == 'code'
                       for node in ast.parse(''.join(cell['source'])).body
                       if isinstance(node, ast.FunctionDef) and node.name == 'qasm_metrics')
    namespace = {'re': re}
    exec(compile(ast.Module(body=[metric_node], type_ignores=[]), '<notebook metrics>', 'exec'), namespace)
    pixel_node = next(node for cell in notebook['cells'] if cell['cell_type'] == 'code'
                      for node in ast.parse(''.join(cell['source'])).body
                      if isinstance(node, ast.FunctionDef) and node.name == 'logo_pixel')
    exec(compile(ast.Module(body=[pixel_node], type_ignores=[]), '<notebook predicate>', 'exec'), namespace)
    assert all(namespace['logo_pixel'](x, y) == bool(MASK[y, x])
               for y in range(64) for x in range(64))
    profiles = []
    for filename in ('artifacts/456/level_merged_456.qasm',
                     'artifacts/524/full_mux_feature_linear_tket_524.qasm'):
        path = Path(filename)
        source = path.read_text()
        circuit = qasm2.loads(source)
        report = json.loads(path.with_suffix('.exhaustive.json').read_text())
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha == report['sha256']
        assert namespace['qasm_metrics'](source) == (18, circuit.depth(), circuit.count_ops()['cx'])
        touches = [0] * 18
        cx_touches = [0] * 18
        for inst in circuit.data:
            for bit in inst.qubits:
                i = circuit.find_bit(bit).index
                touches[i] += 1
                cx_touches[i] += inst.operation.name == 'cx'
        profiles.append(dict(path=filename, sha256=sha, depth=circuit.depth(),
                             counts=dict(circuit.count_ops()), touches=touches,
                             cx_touches=cx_touches, fixed_gate_touch_floor=max(touches),
                             occupied_wire_slot_floor=math.ceil(sum(touches)/18),
                             matching_exhaustive_report=True, notebook_metrics_match=True))
    assert check_identity() == 0
    spectrum = fwht(MASK.ravel())
    assert MASK.sum() == 1097 and np.all(spectrum % 2 == 1)
    # Sample integer phase lifts as a regression for the parity argument, not
    # as its proof. The proof in the companion document covers every lift.
    rng = np.random.default_rng(12)
    for _ in range(20):
        assert np.all(fwht(MASK.ravel() + 2*rng.integers(-9, 10, 4096)) % 2 == 1)
    loaders = []
    for name, level in LEVEL.items():
        _, tables = code_of(TRIPLE_DEFAULT, level)
        for j, table in enumerate(tables):
            raw = QuantumCircuit(7)
            raw.append(UCGate([np.array([[0, 1], [1, 0]]) if table >> i & 1
                               else np.eye(2) for i in range(64)], up_to_diagonal=True),
                       [6, *range(6)])
            native = transpile(raw, basis_gates=['u3', 'cx'], optimization_level=3,
                               qubits_initially_zero=False, seed_transpiler=0)
            # Verify the serialized component on both output-bit values.
            serialized = qasm2.dumps(native)
            unitary = Operator(qasm2.loads(serialized)).data
            inputs = np.arange(128)
            expected = np.array([i ^ (((table >> (i & 63)) & 1) << 6) for i in inputs])
            amplitudes = unitary[expected, inputs]
            residual = unitary.copy()
            residual[expected, inputs] = 0
            error = max(float(np.max(np.abs(residual))),
                        float(np.max(np.abs(np.abs(amplitudes) - 1))))
            assert error < 1e-10
            loaders.append(dict(name=name, bit=j, depth=native.depth(),
                                counts=dict(native.count_ops()), monomial_error=error,
                                basis_inputs_checked=128))
    parity_terms = 4095
    cx_floor = parity_terms - 12
    result = dict(notebook_sha256=hashlib.sha256(notebook_path.read_bytes()).hexdigest(),
                  baselines=profiles, level_identity_mismatches=0, notebook_predicate_mismatches=0,
                  marked_points=int(MASK.sum()), boolean_walsh_support=int(np.count_nonzero(spectrum)),
                  affine_diagonal_model_bound=dict(nonconstant_rotation_floor=parity_terms,
                      cx_floor=cx_floor, width18_depth_floor=math.ceil((parity_terms+2*cx_floor)/18),
                      scope='X/CX/diagonal single-qubit gates, clean basis-state ancillas; excludes internal basis-changing gates'),
                  ucgate_default_code_components=loaders,
                  status='Analysis and verified component negative result; no new full oracle')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)
