"""Assemble a full oracle from CEGIS encoders + the recorded 218/196 kernel recipe.
Either side may be 'relative' to use the protected relative-phase QROM encoder."""
import json, sys, hashlib, math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import two_stage_oracle as ts
import build_two_stage_196 as b196
from distributed_frame_search import native

def cegis_circuit(rec):
    q = QuantumCircuit(9)
    for layer in rec['ops']:
        for op in layer:
            if op[0] == 'cx': q.cx(op[1], op[2])
            else:
                _, a, b, t, na, nb = op
                if na: q.x(a)
                if nb: q.x(b)
                q.rccx(a, b, t)
                if na: q.x(a)
                if nb: q.x(b)
    for j, w in enumerate(rec['code']):
        if rec['pol'][j]: q.x(w)
    return q, rec['code']

def relative_side(side, seed):
    rec = json.loads(Path('artifacts/218/class_codes.json').read_text())
    enc = b196.encoders(rec, seed, seed)  # builds both; extract the requested side
    return None

def side_block(side, spec):
    wires = (ts.YW + ts.YA) if side == 'y' else (ts.XW + ts.XA)
    if spec == 'relative':
        rec = json.loads(Path('artifacts/218/class_codes.json').read_text())
        seed = 99 if side == 'y' else 155
        full = b196.encoders(rec, seed, seed)
        sub = QuantumCircuit(18)
        for inst in full.data:
            qs = [full.find_bit(v).index for v in inst.qubits]
            if all(x in wires for x in qs): sub.append(inst.operation, qs)
        code = [wires.index(11 if side == 'y' else 4)] + [6, 7, 8]
        return sub, [wires[c] for c in code]
    q, code = cegis_circuit(json.load(open(spec)))
    sub = QuantumCircuit(18); sub.compose(q, wires, inplace=True)
    return sub, [wires[c] for c in code]

def build(yspec, xspec, outdir):
    recipe = json.loads(Path('artifacts/218/kernel_recipe.json').read_text())
    kern, _ = b196.kernel(recipe)
    ye, ycode = side_block('y', yspec); xe, xcode = side_block('x', xspec)
    enc = QuantumCircuit(18); enc.compose(ye, inplace=True); enc.compose(xe, inplace=True)
    q = native(enc.compose(kern, ycode + xcode).compose(enc.inverse()))
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    text = qasm2.dumps(q); path = out / f'oracle_d{q.depth()}.qasm'; path.write_text(text)
    info = dict(depth=q.depth(), cx=q.count_ops().get('cx', 0), kernel_depth=kern.depth(),
                y=yspec, x=xspec, sha256=hashlib.sha256(text.encode()).hexdigest())
    (out / 'manifest.json').write_text(json.dumps(info, indent=2)); print(json.dumps(info), flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)
    return path

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3])
