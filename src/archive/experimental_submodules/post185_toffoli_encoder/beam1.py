import sys, time, itertools, random
from sep import *

def span_elems(basis):
    el = [0]
    for b in basis:
        el += [e ^ b for e in el]
    return el[1:]

def nbad(funcs, cls):
    basis = basis_reduce(funcs)
    vec = eval_vectors(basis)
    return len(bad_set(vec, cls)), len(basis)

def moves(basis):
    """Yield (newbasis, desc) for ancilla-AND (if dim<9) and in-place updates."""
    d = len(basis)
    el = span_elems(basis)
    prods = {}
    for i in range(len(el)):
        for j in range(i + 1, len(el)):
            p = el[i] & el[j]
            if p and p not in prods:
                prods[p] = (el[i], el[j])
    if d < 9:
        for p, ab in prods.items():
            nb = basis_reduce(basis + [p])
            if len(nb) > d:
                yield nb, ('anc', ab)
    # in-place: hyperplane H = span of basis minus one element, after change of basis.
    # enumerate hyperplanes via dual vectors mu (nonzero), H = {w: mu(w)=0}
    for mu in range(1, 1 << d):
        H = [basis[j] for j in range(d)]  # construct basis of H
        # pick pivot index with mu bit set
        piv = (mu & -mu).bit_length() - 1
        Hb = [basis[j] ^ (basis[piv] if (mu >> j) & 1 else 0) for j in range(d) if j != piv]
        t = basis[piv]
        Hel = span_elems(Hb)
        seen = set()
        for i in range(len(Hel)):
            for j in range(i + 1, len(Hel)):
                p = Hel[i] & Hel[j]
                if p and p not in seen:
                    seen.add(p)
                    nb = basis_reduce(Hb + [t ^ p])
                    if len(nb) == d:
                        yield nb, ('inp', mu, Hel[i], Hel[j])

def run(cls, beamw=8, steps=6, seed=0):
    random.seed(seed)
    beam = [(XBITS[:], [])]
    for step in range(steps):
        cand = {}
        for basis, hist in beam:
            for nb, desc in moves(basis):
                key = tuple(sorted(span_elems(nb)))[:4] + (len(nb),)
                nbd, d = nbad(nb, cls)
                k = frozenset(nb)
                sc = (nbd, d)
                if k not in cand or cand[k][0] > sc:
                    cand[k] = (sc, nb, hist + [desc])
        ranked = sorted(cand.values(), key=lambda t: t[0])
        # dedupe by span
        seen = set(); newbeam = []
        for sc, nb, hist in ranked:
            key = frozenset(span_elems(nb))
            if key in seen: continue
            seen.add(key); newbeam.append((sc, nb, hist))
            if len(newbeam) >= beamw: break
        beam = [(nb, hist) for sc, nb, hist in newbeam]
        best = newbeam[0]
        ks = [code_size(nb, cls)[0] for sc, nb, hist in newbeam[:3]]
        print(f"step {step+1}: best nbad={best[0]} dims={[len(b) for b,_ in beam][:5]} codesize(top3)={ks}", flush=True)
    return beam

if __name__ == '__main__':
    side = sys.argv[1]
    cls = COLCLS if side == 'x' else ROWCLS
    run(cls, beamw=int(sys.argv[2]), steps=int(sys.argv[3]))
