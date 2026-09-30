import sys, time
from sep import *
from beam1 import span_elems, moves

def score(nb, cls):
    basis = basis_reduce(nb)
    d = len(basis)
    vec = eval_vectors(basis)
    bad = bad_set(vec, cls)
    good = (1 << d) - 1 - len(bad)
    return good, d, bad

def run(cls, beamw, steps, allow_inplace=True):
    beam = [(XBITS[:], [])]
    for step in range(steps):
        cand = {}
        t0 = time.time()
        for basis, hist in beam:
            for nb, desc in moves(basis):
                if not allow_inplace and desc[0] == 'inp':
                    continue
                key = frozenset(span_elems(nb))
                if key in cand: continue
                good, d, bad = score(nb, cls)
                cand[key] = (good, d, nb, hist + [desc], bad)
        # rank by good count per dimension-adjusted: prefer more good vectors, fewer dims
        ranked = sorted(cand.values(), key=lambda t: (-(t[0] + 1) / (1 << t[1]), t[1]))
        top = ranked[:beamw]
        beam = [(t[2], t[3]) for t in top]
        infos = []
        for t in top[:4]:
            k, U = max_subspace(t[1], t[4])
            infos.append((t[1], t[0], t[1] - k))
        print(f"step {step+1}: cands={len(cand)} (dim,good,codesize) top={infos} {time.time()-t0:.1f}s", flush=True)
    return beam

if __name__ == '__main__':
    side = sys.argv[1]
    cls = COLCLS if side == 'x' else ROWCLS
    b = run(cls, int(sys.argv[2]), int(sys.argv[3]), allow_inplace=(sys.argv[4] == '1'))
    print(b[0][1])
