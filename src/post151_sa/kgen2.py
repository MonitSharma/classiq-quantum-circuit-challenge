"""Permutation-aware kernel pipeline: the kernel may end in a permutation of
the 8 code positions, and the literal inverse is remapped accordingly (the same
mechanism the 185 kernel uses).  kbeamP.c already implements the end condition
(MODE 4 + PERMSET); kgen.build_kg assumed identity, so the relaxation was never
usable.  This adds the extraction and the correct sigma.
"""
import pickle, sys, os, subprocess
sys.path.insert(0, '.')
from kdrv import full_gates, profile, KTERMS, CO, assemble, code_vectors
from kgen import plan


def run_beam_perm(pl, T, Wb, mu, seed, out, permset=None, binary='./c/kbeamP8', maxdepth=None):
    seq, W, ST, rdy, unl = pl
    inp = [str(len(KTERMS)), ' '.join(map(str, KTERMS))] + \
          [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]
    env = dict(os.environ); env['SINGLES_PENDING'] = '1'
    if permset is not None:
        env['PERMSET'] = str(permset)
    md = maxdepth if maxdepth is not None else max(T - 2*min(rdy), 1)
    p = subprocess.run([binary, str(Wb), str(md), str(seed), str(mu), out, "4", "0"],
                       input="\n".join(inp) + "\n", capture_output=True, text=True, env=env)
    return p.returncode


def build_kg_perm(pl, beampath, T=None):
    seq, W, ST, rdy, unl = pl
    if T is None:
        T = None
    ddl = [None if T is None else T - u for u in unl]
    L = open(beampath).read().split('\n'); d, tau0 = map(int, L[0].split())
    Tset = set(KTERMS); rows = list(ST); done = set(); pend = {}
    body = [('C', c, t) for c, t in seq]
    for i in range(8):
        if rows[i] in Tset and rows[i] not in done:
            done.add(rows[i]); pend[i] = rows[i]
    for k in range(1, d + 1):
        t = list(map(int, L[k].split())); layer = [(t[1+2*q], t[2+2*q]) for q in range(t[0])]
        tau = tau0 + k
        used = {x for p in layer for x in p}
        for i in list(pend):
            # fire only inside the wire's allowed window, exactly as the beam does
            if i not in used and tau > rdy[i] and (ddl[i] is None or tau <= ddl[i]):
                body.append(('R', W[i], 2 * CO[pend.pop(i)]))
        for c, tt in layer:
            assert tt not in pend
            body.append(('C', W[c], W[tt]))
        new = [(tt, rows[tt] ^ rows[c]) for c, tt in layer]
        for tt, v in new:
            rows[tt] = v
            if v in Tset and v not in done:
                done.add(v); pend[tt] = v
    for i, v in pend.items():
        body.append(('R', W[i], 2 * CO[v]))
    assert done == Tset, (len(done), len(Tset))
    sigma = list(range(18)); used = set()
    for i in range(8):
        cand = [j for j in range(8) if rows[j] == ST[i] and j not in used]
        assert cand, ('no end position for code', i, rows, ST)
        sigma[W[i]] = W[cand[0]]; used.add(cand[0])
    kg = [('S', sigma)] + body + [('C', c, t) for c, t in reversed(seq)]
    return kg
