"""Level/comparator architecture for the logo phase oracle.

Exact identity (checked over all 4096 points):

    logo(x, y) = [u1(y) + v1(x) >= 6]  XOR  [u2(y) + v2(x) >= 6]

where each level function counts how many of five nested sets contain the
coordinate.  Pass 1 is disk A; pass 2 is the square, the trimmed bar, and
disk B.  Each pass loads a 3-bit code of its level into three clean ancillas
on each side and applies a six-variable diagonal kernel.  Encoder networks are
relative-phase (RCCX) and always appear inside an exact compute/uncompute
sandwich, so their diagonal garbage cancels.
"""
import itertools, json
from pathlib import Path
from qiskit import QuantumCircuit, transpile

FULL = (1 << 64) - 1


def _rng(a, b):
    return set(range(a, b + 1))


NESTED = {
    'u1': [_rng(11, 27), _rng(12, 26), _rng(13, 25), _rng(15, 23), _rng(17, 21)],
    'v1': [_rng(32, 48), _rng(33, 47), _rng(34, 46), _rng(36, 44), _rng(38, 42)],
    'u2': [_rng(29, 53), _rng(35, 47), _rng(36, 46), _rng(37, 45), _rng(39, 43)],
    'v2': [_rng(2, 61), _rng(2, 26) | _rng(50, 60), _rng(2, 26) | _rng(51, 59),
           _rng(2, 26) | _rng(53, 57), _rng(2, 26)],
}
LEVEL = {k: [sum(1 for s in v if t in s) for t in range(64)] for k, v in NESTED.items()}


def logo(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53) or (26 <= x <= 49 and 39 <= y <= 43)
            or (x - 55) ** 2 + (y - 41) ** 2 <= 42 or (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def check_identity():
    bad = 0
    for y in range(64):
        for x in range(64):
            p = (LEVEL['u1'][y] + LEVEL['v1'][x] >= 6) ^ (LEVEL['u2'][y] + LEVEL['v2'][x] >= 6)
            bad += p != logo(x, y)
    return bad


# ---------------------------------------------------------------- linear algebra
def reduce_basis(vectors):
    piv = {}
    for v in vectors:
        for b in range(63, -1, -1):
            if v >> b & 1:
                if b in piv:
                    v ^= piv[b]
                else:
                    piv[b] = v
                    break
    return piv


def decompose(target, regs):
    """Return a subset of register indices whose XOR is `target`, or None.

    `regs` may include an implicit constant which is represented by index -1.
    """
    items = list(enumerate(regs)) + [(-1, FULL)]
    piv = {}
    for idx, v in items:
        cur, comb = v, frozenset([idx])
        for b in range(63, -1, -1):
            if cur >> b & 1:
                if b in piv:
                    pv, pc = piv[b]
                    cur ^= pv
                    comb = comb ^ pc
                else:
                    piv[b] = (cur, comb)
                    break
    cur, comb = target, frozenset()
    for b in range(63, -1, -1):
        if cur >> b & 1:
            if b not in piv:
                return None
            pv, pc = piv[b]
            cur ^= pv
            comb = comb ^ pc
    return comb if cur == 0 else None


# ---------------------------------------------------------------- kernel
COSTS = {0: 0, 1: 0.1, 2: 2.0, 3: 11.0, 4: 30.0, 5: 60.0, 6: 100.0}
MATRIX = [[1 if u + v >= 6 else 0 for v in range(6)] for u in range(6)]


def kernel_terms(alpha, beta):
    """Cheapest-first ANF of a 6-variable diagonal matching MATRIX on reachable codes."""
    order = sorted(range(64), key=lambda m: (COSTS[bin(m).count('1')], m))
    piv = {}
    for u in range(6):
        for v in range(6):
            w = alpha[u] | (beta[v] << 3)
            mask = 0
            for i, m in enumerate(order):
                if (m & ~w) == 0:
                    mask |= 1 << i
            rhs = MATRIX[u][v]
            for i in range(64):
                if mask >> i & 1:
                    if i in piv:
                        pm, pr = piv[i]
                        mask ^= pm
                        rhs ^= pr
                    else:
                        piv[i] = (mask, rhs)
                        break
    sol = [0] * 64
    for i in sorted(piv, reverse=True):
        mask, rhs = piv[i]
        val = rhs
        for j in range(i + 1, 64):
            if mask >> j & 1:
                val ^= sol[j]
        sol[i] = val
    return [order[i] for i in range(64) if sol[i]]


def kernel_cost(terms):
    return sum(COSTS[bin(t).count('1')] for t in terms)


def emit_kernel(qc, terms, ywires, xwires):
    wires = list(ywires) + list(xwires)
    for t in terms:
        qs = [wires[i] for i in range(6) if t >> i & 1]
        if not qs:
            continue
        if len(qs) == 1:
            qc.z(qs[0])
        elif len(qs) == 2:
            qc.cz(*qs)
        elif len(qs) == 3:
            qc.ccz(*qs)
        else:
            from qiskit.circuit.library import ZGate
            qc.append(ZGate().control(len(qs) - 1), qs)


# ---------------------------------------------------------------- encoder
def code_of(triple, level_table):
    """alpha[u] = 3-bit code of level u, and the three target truth tables."""
    alpha = []
    for u in range(6):
        alpha.append(sum(((s >> u) & 1) << j for j, s in enumerate(triple)))
    targets = [sum(1 << t for t in range(64) if (s >> level_table[t]) & 1) for s in triple]
    return alpha, targets


def small_decompose(value, regs, avoid=()):
    """Prefer short register combinations (the search only ever uses two)."""
    idx = [i for i in range(len(regs)) if i not in avoid]
    for const in (False, True):
        v = value ^ (FULL if const else 0)
        if v == 0:
            continue
        for i in idx:
            if regs[i] == v:
                return frozenset([i] + ([-1] if const else []))
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                if regs[idx[a]] ^ regs[idx[b]] == v:
                    return frozenset([idx[a], idx[b]] + ([-1] if const else []))
    return decompose(value, regs)


def emit_encoder(qc, hist, wires, targets):
    """Replay an AND network then place `targets` on the last three wires.

    `wires` lists the nine physical qubits for registers 0..8; registers 0..5
    start holding the six input bits and 6..8 start clean.
    """
    VARS = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]
    regs = VARS + [0, 0, 0]
    for a, b, k in hist:
        prep = []
        used = {k}
        for val in (a, b):
            comb = small_decompose(val, regs, avoid=used)
            assert comb is not None, 'AND operand outside register span'
            neg = -1 in comb
            idxs = sorted(i for i in comb if i != -1)
            assert idxs, 'AND operand is a constant'
            host = next((i for i in idxs if i not in used), None)
            assert host is not None, 'no free host wire for AND operand'
            used.add(host)
            rest = [i for i in idxs if i != host]
            for i in rest:
                qc.cx(wires[i], wires[host])
                regs[host] ^= regs[i]
            if neg:
                qc.x(wires[host])
                regs[host] ^= FULL
            prep.append((host, rest, neg))
        (ha, _, _), (hb, _, _) = prep
        qc.rccx(wires[ha], wires[hb], wires[k])
        regs[k] ^= regs[ha] & regs[hb]
        for host, rest, neg in reversed(prep):
            if neg:
                qc.x(wires[host])
                regs[host] ^= FULL
            for i in reversed(rest):
                qc.cx(wires[i], wires[host])
                regs[host] ^= regs[i]
    # place targets on registers 6,7,8
    for slot, tgt in zip((6, 7, 8), targets):
        comb = decompose(tgt ^ regs[slot], regs)
        assert comb is not None, "target not in register span"
        for i in sorted(comb):
            if i == -1:
                qc.x(wires[slot])
                regs[slot] ^= FULL
            else:
                assert i != slot, "self-reference in target placement"
                qc.cx(wires[i], wires[slot])
                regs[slot] ^= regs[i]
    for slot, tgt in zip((6, 7, 8), targets):
        assert regs[slot] == tgt, "encoder placement failed"
    return regs


YW = list(range(6, 12))
XW = list(range(6))
YA = [12, 13, 14]
XA = [15, 16, 17]


def mux_encoder(targets, wires, seed=0):
    """Fallback encoder: uniformly controlled Ry multiplexer (no scratch needed)."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from full_mux import multiplexer
    return multiplexer(list(targets), list(wires[6:]), list(wires[:6]), 'y', seed)


def ucry(angle_tables, outputs, controls, seed=0):
    """Uniformly controlled Ry with explicit per-output angle tables.

    Two such blocks with tables t1 and t2 compose exactly into one block with
    table t2 - t1, which is what lets the pass-1 unload and the pass-2 load
    collapse into a single multiplexer.
    """
    import random
    import numpy as np
    n = len(controls)
    N = 1 << n
    rng = random.Random(seed)
    base = list(range(n))
    rng.shuffle(base)
    shifts = list(range(n))
    rng.shuffle(shifts)
    orders = [base[s:] + base[:s] for s in shifts[:len(angle_tables)]]
    coeffs = []
    for table, order in zip(angle_tables, orders):
        a = np.array([table[sum(((k >> j) & 1) << v for j, v in enumerate(order))]
                      for k in range(N)], dtype=float)
        h = 1
        while h < N:
            for i in range(0, N, 2 * h):
                lo = a[i:i + h].copy()
                hi = a[i + h:i + 2 * h].copy()
                a[i:i + h] = lo + hi
                a[i + h:i + 2 * h] = lo - hi
            h *= 2
        coeffs.append(a / N)
    qc = QuantumCircuit(18)
    for j in range(N):
        for b, t in enumerate(outputs):
            angle = float(coeffs[b][j ^ (j >> 1)])
            if abs(angle) > 1e-14:
                qc.ry(angle, t)
        pos = ((j + 1) & -(j + 1)).bit_length() - 1 if j < N - 1 else n - 1
        for b, t in enumerate(outputs):
            qc.cx(controls[orders[b][pos]], t)
    return qc


def sparse_ucry(angle_tables, outputs, controls, seed=0):
    """Uniformly controlled Ry that visits only the nonzero Walsh masks.

    The dense block walks all 64 Gray masks, costing 128 layers.  A block whose
    angle table has a sparse Walsh spectrum only has to visit the masks with a
    nonzero coefficient, and the cost is then the length of a short closed walk
    through those masks.  The load and unload blocks gain nothing (an odd-size
    support forces a full spectrum) but the middle block is markedly sparser.
    """
    import numpy as np
    n = len(controls)
    N = 1 << n
    qc = QuantumCircuit(18)
    paths = []
    for table in angle_tables:
        a = np.array(table, dtype=float)
        h = 1
        while h < N:
            for i in range(0, N, 2 * h):
                lo = a[i:i + h].copy()
                hi = a[i + h:i + 2 * h].copy()
                a[i:i + h] = lo + hi
                a[i + h:i + 2 * h] = lo - hi
            h *= 2
        coeff = a / N
        masks = [m for m in range(N) if abs(coeff[m]) > 1e-14]
        if 0 not in masks:
            masks = [0] + masks
        # greedy nearest-neighbour closed walk from mask 0
        order = [0]
        rest = [m for m in masks if m != 0]
        cur = 0
        while rest:
            nxt = min(rest, key=lambda m: bin(m ^ cur).count('1'))
            order.append(nxt)
            rest.remove(nxt)
            cur = nxt
        paths.append((order, coeff))
    steps = max(len(o) for o, _ in paths)
    for idx in range(steps):
        for b, t in enumerate(outputs):
            order, coeff = paths[b]
            if idx < len(order):
                ang = float(coeff[order[idx]])
                if abs(ang) > 1e-14:
                    qc.ry(ang, t)
        for b, t in enumerate(outputs):
            order, _ = paths[b]
            if idx < len(order):
                cur = order[idx]
                nxt = order[idx + 1] if idx + 1 < len(order) else 0
                for bit in range(n):
                    if (cur ^ nxt) >> bit & 1:
                        qc.cx(controls[bit], t)
    return qc


def angle_table(targets):
    """pi * bit value, per output, indexed by the 6-bit control value."""
    import math
    return [[math.pi * ((t >> i) & 1) for i in range(64)] for t in targets]


def build_merged(seed=0, opt=3, ytrip=None, xtrip=None, sparse=None):
    """Two passes sharing one middle multiplexer: load, K1, re-encode, K2, unload."""
    import numpy as np
    ytrip = ytrip or TRIPLE_DEFAULT
    xtrip = xtrip or TRIPLE_DEFAULT
    tabs = {}
    for name, trip in (('u1', ytrip), ('u2', ytrip), ('v1', xtrip), ('v2', xtrip)):
        _, targets = code_of(trip, LEVEL[name])
        tabs[name] = np.array(angle_table(targets))
    alpha, _ = code_of(ytrip, LEVEL['u1'])
    beta, _ = code_of(xtrip, LEVEL['v1'])
    k1 = k2 = kernel_terms(alpha, beta)
    qc = QuantumCircuit(18)
    mid = sparse if sparse else ucry
    qc.compose(ucry(tabs['u1'], YA, YW, seed), inplace=True)
    qc.compose(ucry(tabs['v1'], XA, XW, seed + 7), inplace=True)
    emit_kernel(qc, k1, YA, XA)
    qc.compose(mid(tabs['u2'] - tabs['u1'], YA, YW, seed + 1), inplace=True)
    qc.compose(mid(tabs['v2'] - tabs['v1'], XA, XW, seed + 8), inplace=True)
    emit_kernel(qc, k2, YA, XA)
    qc.compose(ucry(-tabs['u2'], YA, YW, seed + 2), inplace=True)
    qc.compose(ucry(-tabs['v2'], XA, XW, seed + 9), inplace=True)
    return transpile(qc, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                     optimization_level=opt, seed_transpiler=seed)


TRIPLE_DEFAULT = (0b110000, 0b111100, 0b101010)


def build_pass(nets, pass_id):
    """nets: dict name -> (hist, triple)."""
    yname, xname = ('u1', 'v1') if pass_id == 1 else ('u2', 'v2')
    yhist, ytrip = nets[yname]
    xhist, xtrip = nets[xname]
    alpha, ytargets = code_of(ytrip, LEVEL[yname])
    beta, xtargets = code_of(xtrip, LEVEL[xname])
    terms = kernel_terms(alpha, beta)
    enc = QuantumCircuit(18)
    if yhist is None:
        enc.compose(mux_encoder(ytargets, YW + YA, seed=pass_id), inplace=True)
    else:
        emit_encoder(enc, yhist, YW + YA, ytargets)
    if xhist is None:
        enc.compose(mux_encoder(xtargets, XW + XA, seed=100 + pass_id), inplace=True)
    else:
        emit_encoder(enc, xhist, XW + XA, xtargets)
    qc = QuantumCircuit(18)
    qc.compose(enc, inplace=True)
    emit_kernel(qc, terms, YA, XA)
    qc.compose(enc.inverse(), inplace=True)
    return qc, terms


def build(nets, seed=0, opt=3):
    qc = QuantumCircuit(18)
    info = {}
    for p in (1, 2):
        sub, terms = build_pass(nets, p)
        qc.compose(sub, inplace=True)
        info[f'pass{p}_kernel_terms'] = [bin(t)[2:].zfill(6) for t in terms]
    return transpile(qc, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                     optimization_level=opt, seed_transpiler=seed), info


def _final_regs(hist):
    VARS = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]
    regs = VARS + [0, 0, 0]
    for a, b, k in hist:
        regs[k] ^= a & b
    return regs


def available_triples(hist, level_table):
    """All level-separating 3-bit codes whose bit functions lie in the register span."""
    regs = _final_regs(hist)
    piv = reduce_basis(regs + [FULL])
    ok = []
    for sub in range(64):
        f = sum(1 << t for t in range(64) if (sub >> level_table[t]) & 1)
        v = f
        for b in range(63, -1, -1):
            if v >> b & 1 and b in piv:
                v ^= piv[b]
        if v == 0:
            ok.append(sub)
    out = []
    for trio in itertools.combinations(ok, 3):
        sig = {tuple((s >> u) & 1 for s in trio) for u in range(6)}
        if len(sig) == 6:
            out.append(trio)
    return out


def refine_triples(nets, pass_id):
    """Pick the y/x code pair with the cheapest kernel among those available."""
    yname, xname = ('u1', 'v1') if pass_id == 1 else ('u2', 'v2')
    yhist, ytrip = nets[yname]
    xhist, xtrip = nets[xname]
    ycands = available_triples(yhist, LEVEL[yname]) if yhist is not None else [ytrip]
    xcands = available_triples(xhist, LEVEL[xname]) if xhist is not None else [xtrip]
    best = None
    for yt in ycands[:400]:
        alpha, _ = code_of(yt, LEVEL[yname])
        for xt in xcands[:400]:
            beta, _ = code_of(xt, LEVEL[xname])
            c = kernel_cost(kernel_terms(alpha, beta))
            if best is None or c < best[0]:
                best = (c, yt, xt)
    return best


def load_nets(directory):
    nets = {}
    for name in ('u1', 'v1', 'u2', 'v2'):
        best = None
        for path in Path(directory).glob(f'net_{name}_*.json'):
            d = json.loads(path.read_text())
            if best is None or d['ands'] < best['ands']:
                best = d
        if best is None:
            raise SystemExit(f'no network found for {name} in {directory}')
        nets[name] = ([tuple(h) for h in best['hist']], best['triple'])
    return nets


if __name__ == '__main__':
    import sys
    print('identity mismatches:', check_identity())
    if len(sys.argv) > 1:
        nets = load_nets(sys.argv[1])
        qc, info = build(nets)
        print('depth', qc.depth(), qc.count_ops())
        from qiskit import qasm2
        out = sys.argv[2] if len(sys.argv) > 2 else 'artifacts/level_oracle.qasm'
        Path(out).write_text(qasm2.dumps(qc))
        print('wrote', out)
