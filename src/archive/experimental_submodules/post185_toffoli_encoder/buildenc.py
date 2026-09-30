"""Assemble a full oracle from x/y Toffoli encoders (annealer JSON) + phase kernel."""
import sys, json, math
import numpy as np
sys.path.insert(0, 'src')
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from kernelcost import anf_solution
from logo import M

XW = list(range(6)) + [15, 16, 17]
YW = list(range(6, 12)) + [12, 13, 14]

def enc_circuit(spec):
    q = QuantumCircuit(9)
    for st in spec['stages']:
        for layer in st['cx']:
            for c, t in layer:
                q.cx(c, t)
        # Toffolis in a batch act on disjoint wires, simultaneous semantics == sequential
        for c1, c2, t, n1, n2 in st['tof']:
            if n1: q.x(c1)
            if n2: q.x(c2)
            q.rccx(c1, c2, t)
            if n1: q.x(c1)
            if n2: q.x(c2)
    return q

def classical(spec):
    w = [sum(1 << x for x in range(64) if (x >> k) & 1) if k < 6 else 0 for k in range(9)]
    full = (1 << 64) - 1
    for st in spec['stages']:
        for layer in st['cx']:
            nw = w[:]
            for c, t in layer: nw[t] ^= w[c]
            w = nw
        nw = w[:]
        for c1, c2, t, n1, n2 in st['tof']:
            nw[t] ^= (w[c1] ^ (full if n1 else 0)) & (w[c2] ^ (full if n2 else 0))
        w = nw
    return w

def rref(G):
    rows = [g for g in G]; piv = []
    out = []
    for r in rows:
        for p, o in zip(piv, out):
            if (r >> p) & 1: r ^= o
        assert r, 'code rows dependent'
        p = (r & -r).bit_length() - 1
        # eliminate p from previous rows
        out = [o ^ r if (o >> p) & 1 else o for o in out]
        out.append(r); piv.append(p)
    return out, piv

def collapse(rows, piv):
    """CX list putting row r (mask over wires) onto wire piv[r]; rows reduced so pivots unique."""
    ops = []
    for r, p in zip(rows, piv):
        for j in range(9):
            if j != p and (r >> j) & 1:
                assert j not in piv
                ops.append((j, p))
    return ops

def side(spec):
    w = classical(spec)
    rows, piv = rref(spec['G'])
    code = [sum(((bin(r & sum(((w[j] >> x) & 1) << j for j in range(9))).count('1')) & 1) << i for i, r in enumerate(rows)) for x in range(64)]
    return w, rows, piv, code

def kernel_targets(ycode, xcode):
    terms = anf_solution(ycode, xcode)
    assert terms is not None
    F = np.array([sum(1 for m in terms if m & ~wd == 0) for wd in range(256)], float)
    phi = math.pi * F
    H = np.array([[(-1) ** bin(a & b).count('1') for b in range(256)] for a in range(256)])
    hat = H @ phi
    theta = -hat / 128.0
    targets = {}
    for S in range(1, 256):
        t = theta[S] % (2 * math.pi)
        if min(t, 2 * math.pi - t) > 1e-9:
            targets[S] = t
    return targets, terms

def assemble(xspec, yspec, beam=16, seed=0):
    from post218_beam_phase import psynth
    from distributed_frame_search import native
    wx, rx, px, xcode = side(xspec)
    wy, ry, py, ycode = side(yspec)
    targets, terms = kernel_targets(ycode, xcode)
    # psynth convention check
    kq = psynth(8, {m: -a / 2 for m, a in targets.items()}, seed=seed, beam=beam, branch=8)
    U = Operator(kq).data; d = np.diag(U)
    assert np.allclose(np.abs(d), 1)
    want = np.array([math.pi * sum(1 for m in terms if m & ~wd == 0) for wd in range(256)])
    ph = np.angle(d * np.exp(-1j * want)); ph -= ph[0]
    assert np.allclose(np.exp(1j * ph), 1, atol=1e-9), 'kernel convention mismatch'
    ex, ey = enc_circuit(xspec), enc_circuit(yspec)
    q = QuantumCircuit(18)
    q.compose(ex, XW, inplace=True); q.compose(ey, YW, inplace=True)
    colx = collapse(rx, px); coly = collapse(ry, py)
    C = QuantumCircuit(18)
    for c, t in colx: C.cx(XW[c], XW[t])
    for c, t in coly: C.cx(YW[c], YW[t])
    q.compose(C, inplace=True)
    kw = [YW[p] for p in py] + [XW[p] for p in px]   # kernel bit i: y bits 0-3, x bits 4-7
    q.compose(kq, kw, inplace=True)
    q.compose(C.inverse(), inplace=True)
    q.compose(ex.inverse(), XW, inplace=True); q.compose(ey.inverse(), YW, inplace=True)
    nq = native(q)
    return nq, dict(kernel_terms=len(targets), kernel_depth=kq.depth(), enc_x_depth=native(ex).depth(), enc_y_depth=native(ey).depth())

if __name__ == '__main__':
    xs = json.loads(open(sys.argv[1]).read()); ys = json.loads(open(sys.argv[2]).read())
    q, info = assemble(xs, ys)
    out = sys.argv[3]
    open(out, 'w').write(qasm2.dumps(q))
    print(info, 'depth', q.depth(), 'cx', q.count_ops().get('cx', 0), flush=True)
