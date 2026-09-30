"""Class-code oracle with Toffoli-corrected narrow-address loaders.

label_j(x) = U_j(z) XOR q_j(x), where q_j is a product of two affine forms
computed by one RCCX batch and U is a sparse uniformly-controlled Ry lookup.
The kernel is the integer-lifted ANF phase polynomial on eight code wires.
New experimental builder; it never writes into protected artifacts.
"""
import math, random, itertools
import numpy as np
from qiskit import QuantumCircuit, transpile
from distributed_ucry import structured_ucry, change_basis
from distributed_frame_search import native
from depth_parity_network import synth


def logo(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53) or (26 <= x <= 49 and 39 <= y <= 43)
            or (x - 55) ** 2 + (y - 41) ** 2 <= 42 or (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def par(t, m):
    return bin(t & m).count('1') & 1


def independent(rows):
    b = []
    for r in rows:
        v = r
        for q in b:
            v = min(v, v ^ q)
        if v == 0:
            return False
        b.append(v); b.sort(reverse=True)
    return True


def complete(rows):
    rows = list(rows)
    for e in [1 << i for i in range(6)] + list(range(1, 64)):
        if len(rows) == 6:
            break
        if independent(rows + [e]):
            rows.append(e)
    assert len(rows) == 6 and independent(rows)
    return rows


def apply_rows(rows, x):
    return sum(par(x, r) << i for i, r in enumerate(rows))


def side_loader(code, pmask, corr, addr_rows, seeds=range(6), highs=None):
    """code: 64 -> 3-bit label. corr: list of 3 items None or ((a,c),(b,d)).
    addr_rows: linear forms the lookup address is taken over (up to 6).
    Returns (circuit on 9 wires [6 data, 3 anc], parity wire index)."""
    ident = tuple(1 << i for i in range(6))
    q = QuantumCircuit(9)
    cur = ident
    # --- correction batch
    forms = []
    for c in corr:
        if c is None:
            continue
        for f, _ in c:
            if f and f not in forms:
                forms.append(f)
    if forms:
        rows = []
        for f in forms:
            if independent(rows + [f]):
                rows.append(f)
        assert len(rows) == len(forms), 'dependent correction forms'
        rows = complete(rows)
        q.compose(change_basis(cur, tuple(rows)), range(6), inplace=True)
        cur = tuple(rows)
        wire = {r: i for i, r in enumerate(rows)}
        const = set()
        for j, c in enumerate(corr):
            if c is None:
                continue
            (a, ca), (b, cb) = c
            ctl = []
            for f, cc in ((a, ca), (b, cb)):
                if f == 0:
                    ctl.append(None)
                else:
                    ctl.append(wire[f])
                    if cc:
                        const.add(wire[f])
            if None in ctl:
                raise ValueError('degenerate correction')
        for w in const:
            q.x(w)
        for j, c in enumerate(corr):
            if c is None:
                continue
            (a, ca), (b, cb) = c
            q.rccx(wire[a], wire[b], 6 + j)
        for w in const:
            q.x(w)
    Q = [0] * 64
    for j, c in enumerate(corr):
        if c is None:
            continue
        (a, ca), (b, cb) = c
        for x in range(64):
            Q[x] |= ((par(x, a) ^ ca) & (par(x, b) ^ cb)) << j
    resid = [code[x] ^ Q[x] for x in range(64)]
    # --- lookup in address frame
    arows = complete(addr_rows)
    if cur != tuple(arows):
        q.compose(change_basis(cur, tuple(arows)), range(6), inplace=True)
    cur = tuple(arows)
    inv = {}
    for x in range(64):
        inv[apply_rows(arows, x)] = x
    tab = np.array([[math.pi * ((resid[inv[z]] >> j) & 1) for z in range(64)] for j in range(3)])
    best = None
    highs = highs or list(itertools.combinations(range(6), 3))
    for high in highs:
        for seed in seeds:
            for kw in (dict(sparse=True), dict(open_walk=True)):
                raw = structured_ucry(tab, [6, 7, 8], list(range(6)), seed, high=list(high), **kw)
                if best is None or raw.depth() < best[0]:
                    best = (raw.depth(), raw)
    q.compose(best[1], range(9), inplace=True)
    # --- expose parity on a data wire
    if pmask in cur:
        pw = cur.index(pmask)
    else:
        rows = list(cur)
        for i in range(6):
            trial = rows[:i] + [pmask] + rows[i + 1:]
            if independent(trial):
                q.compose(change_basis(cur, tuple(trial)), range(6), inplace=True)
                cur = tuple(trial); pw = i
                break
    return q, pw


def kernel_terms(xcode, ycode):
    """Low-degree ANF over 8 bits: y code bits 0..3, x code bits 4..7."""
    order = sorted(range(256), key=lambda m: (m.bit_count(), m))
    ev = [sum(1 << i for i, m in enumerate(order) if m & ~w == 0) for w in range(256)]
    piv = {}
    pairs = {}
    for x in range(64):
        for y in range(64):
            w = ycode[y] | (xcode[x] << 4)
            v = int(logo(x, y))
            assert pairs.setdefault(w, v) == v, 'code does not determine phase'
    for w, rhs in pairs.items():
        row = ev[w]
        while row:
            i = (row & -row).bit_length() - 1
            if i in piv:
                a, b = piv[i]; row ^= a; rhs ^= b
            else:
                piv[i] = (row, rhs); break
        assert row or rhs == 0
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    return [order[i] for i in range(256) if sol >> i & 1]


def kernel_circuit(terms, seeds=range(12)):
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    best = None
    for s in seeds:
        k = native(synth(math.pi * lifted, 8, s))
        if best is None or (k.depth(), k.size()) < best[:2]:
            best = (k.depth(), k.size(), k)
    return best[2]


def assemble(yload, ypw, xload, xpw, terms):
    YW = list(range(6, 12)); YA = [12, 13, 14]; XW = list(range(6)); XA = [15, 16, 17]
    enc = QuantumCircuit(18)
    enc.compose(yload, YW + YA, inplace=True)
    enc.compose(xload, XW + XA, inplace=True)
    k = kernel_circuit(terms)
    q = enc.copy()
    q.compose(k, [YW[ypw]] + YA + [XW[xpw]] + XA, inplace=True)
    q.compose(enc.inverse(), inplace=True)
    return native(q), k
