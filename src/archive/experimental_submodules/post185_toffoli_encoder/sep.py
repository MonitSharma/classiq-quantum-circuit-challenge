import numpy as np
from classes import ROWCLS, COLCLS

MASK64 = (1 << 64) - 1
XBITS = [sum(1 << x for x in range(64) if (x >> i) & 1) for i in range(6)]

def basis_reduce(funcs):
    """Return a basis (list of ints) of the GF(2) span of truth-table ints."""
    basis = []
    for f in funcs:
        for b in basis:
            f = min(f, f ^ b)
        if f:
            basis.append(f)
    return basis

def eval_vectors(basis):
    """For each x, the vector of basis function values as an int."""
    vec = [0] * 64
    for j, b in enumerate(basis):
        for x in range(64):
            if (b >> x) & 1:
                vec[x] |= 1 << j
    return vec

def bad_set(vec, cls):
    d = 0
    bad = set()
    for a in range(64):
        va = vec[a]; ca = cls[a]
        for b in range(a + 1, 64):
            if ca != cls[b]:
                bad.add(va ^ vec[b])
    return bad

def max_subspace(dim, bad, need=None):
    """Largest subspace of GF(2)^dim avoiding `bad` (except 0). Returns (dim, basis)."""
    full = 1 << dim
    good = [v for v in range(1, full) if v not in bad]
    goodset = set(good)
    best = [0, []]
    def rec(U, basis, cands):
        if len(basis) > best[0]:
            best[0] = len(basis); best[1] = list(basis)
            if need is not None and best[0] >= need:
                return True
        # bound
        if len(basis) + (len(cands).bit_length()) <= best[0]:
            pass
        for i, v in enumerate(cands):
            newU = U | {u ^ v for u in U}
            nc = [c for c in cands[i + 1:] if c not in newU and all((c ^ u) in goodset or (c ^ u) == 0 for u in newU if u != 0) ]
            # subspace closure: c must be good w.r.t. whole coset c+U'
            if len(basis) + 1 + (len(nc).bit_length()) <= best[0]:
                continue
            if rec(newU, basis + [v], nc):
                return True
        return False
    rec({0}, [], good)
    return best[0], best[1]

def code_size(funcs, cls, need=None):
    basis = basis_reduce(funcs)
    d = len(basis)
    vec = eval_vectors(basis)
    bad = bad_set(vec, cls)
    k, U = max_subspace(d, bad, need)
    return d - k, d, len(bad), basis
