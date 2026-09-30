"""Assemble a full oracle from two SAT-found axis encoders (post185_side_encoder_sat).

Each encoder JSON gives layered ops on 9 local wires (0-5 data, 6-8 clean ancilla)
and the 4 code wires. The kernel is the integer-lifted low-degree ANF on the
8 code wires, beam scheduled. Output is exhaustively verified.
"""
import json, math, sys, hashlib
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from depth_parity_network import walsh
from distributed_frame_search import native
from post218_beam_phase import psynth
from post185_side_encoder_sat import simulate, logo

def encoder_circuit(rec):
    q = QuantumCircuit(9)
    for layer in rec['ops']:
        for op in layer:
            if op[0] == 'cx':
                q.cx(op[1], op[2])
            else:
                _, a, b, t, na, nb = op
                if na: q.x(a)
                if nb: q.x(b)
                q.rccx(a, b, t)
                if na: q.x(a)
                if nb: q.x(b)
    return q

def codes(rec):
    fin = simulate(rec['ops'])
    return [sum(fin[p][w] << i for i, w in enumerate(rec['code'])) for p in range(64)]

def kernel_terms(xc, yc):
    order = sorted(range(256), key=lambda m: (m.bit_count(), m))
    ev = [sum(1 << i for i, m in enumerate(order) if m & ~w == 0) for w in range(256)]
    piv = {}; seen = {}
    for x in range(64):
        for y in range(64):
            w = yc[y] | (xc[x] << 4); v = int(logo(x, y))
            if w in seen:
                assert seen[w] == v; continue
            seen[w] = v; row, rhs = ev[w], v
            while row:
                i = (row & -row).bit_length() - 1
                if i in piv: a, b = piv[i]; row ^= a; rhs ^= b
                else: piv[i] = (row, rhs); break
            assert row or rhs == 0
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs: sol |= 1 << i
    return [order[i] for i in range(256) if sol >> i & 1]

def kernel(terms, seeds=(209, 1, 2, 3)):
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    co = walsh(math.pi * lifted)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for s in seeds:
        k = native(psynth(8, targets, global_phase=float(co[0]), seed=s, beam=64, branch=14, alpha=5.0, timew=0.35))
        if best is None or k.depth() < best.depth(): best = k
    return best

def build(xrec, yrec, outdir):
    xe, ye = encoder_circuit(xrec), encoder_circuit(yrec)
    XW, XA, YW, YA = list(range(6)), [15, 16, 17], list(range(6, 12)), [12, 13, 14]
    xmap, ymap = XW + XA, YW + YA
    terms = kernel_terms(codes(xrec), codes(yrec))
    k = kernel(terms)
    kw = [ymap[w] for w in yrec['code']] + [xmap[w] for w in xrec['code']]
    enc = QuantumCircuit(18)
    enc.compose(ye, ymap, inplace=True); enc.compose(xe, xmap, inplace=True)
    q = native(enc.compose(k, kw).compose(enc.inverse()))
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    text = qasm2.dumps(q); path = out / f'oracle_d{q.depth()}.qasm'; path.write_text(text)
    info = dict(depth=q.depth(), cx=q.count_ops().get('cx', 0), kernel_depth=k.depth(),
                kernel_terms=len(terms), x_encoder_depth=native(xe).depth(),
                y_encoder_depth=native(ye).depth(), sha256=hashlib.sha256(text.encode()).hexdigest())
    (out / 'manifest.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info), flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)
    return path

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3])
