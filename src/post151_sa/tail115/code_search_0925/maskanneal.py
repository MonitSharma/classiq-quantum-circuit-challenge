"""maskanneal.py xmask iters seed [wl] : anneal x labels under a different x parity mask (y fixed at current).
Objective = kernel terms + wl * x loader proxy (wl=0: kernel only)."""
import sys, os, json, math, random, numpy as np
sys.path.insert(0, '/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES', '/work/classiq/artifacts/185/class_codes.json')
from codes import COLCLS, ROWCLS, YL, H
from kterm import table, terms
from condlp import atoms_for
import gensup as G
xm = int(sys.argv[1]); iters = int(sys.argv[2]); seed = int(sys.argv[3]); wl = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
rnd = random.Random(seed); rng = np.random.default_rng(seed)
K = sorted({(bin(v & xm).count('1') % 2, COLCLS[v]) for v in range(64)})
yc = [(bin(v & 32).count('1') % 2) | (YL[(bin(v & 32).count('1') % 2, ROWCLS[v])] << 1) for v in range(64)]
def xcode(lab): return [lab[(bin(v & xm).count('1') % 2, COLCLS[v])] for v in range(64)]
def kt(lab):
    xc = [(bin(v & xm).count('1') % 2) | (xcode(lab)[v] << 1) for v in range(64)]
    T = table(xc, yc, 4, 4)
    if T is None: return 999
    return min(terms(T, 4, 4)[0] for _ in range(2))
def proxy(lab):
    code = xcode(lab); B = np.array([[(c >> b) & 1 for c in code] for b in range(3)])
    best = None
    for m0 in range(1, 8):
        f0 = np.array(sum(B[i] for i in range(3) if m0 >> i & 1) % 2)
        s = H @ (1 - 2 * f0.astype(float)); t0 = int(np.sum(np.abs(s[1:]) > 1e-9))
        cc = {}
        for m in range(1, 8):
            if m == m0: continue
            fb = np.array(sum(B[i] for i in range(3) if m >> i & 1) % 2)
            keys_, A = atoms_for(np.array([f0, fb, fb]), [0])
            out = G.sparse_rep_r(np.pi * fb.astype(float), A, rng, jit=0.35)
            if out is None: continue
            sup, sol = out; nL = sum(1 for k in sup if len(keys_[k][1])); cc[m] = (len(sup), nL)
        for m1 in cc:
            for m2 in cc:
                if m1 >= m2 or m1 ^ m2 == m0: continue
                n1, l1 = cc[m1]; n2, l2 = cc[m2]; pre = t0 + n1 - l1 + n2 - l2; L = l1 + l2
                sc = pre / 2.2 + L / 1.55
                if best is None or sc < best[0]: best = (sc, (m0, m1, m2), t0, n1, n2, L, pre)
    return best
def init():
    lab = {}
    for p in (0, 1):
        grp = [k for k in K if k[0] == p]; ls = rnd.sample(range(8), len(grp))
        for k, l in zip(grp, ls): lab[k] = l
    return lab
cur = init(); ck = kt(cur); cp = proxy(cur)[0] if wl else 0.0; cs = ck + wl * cp
best = (cs, dict(cur), ck, cp)
print('mask', xm, 'keys', len(K), 'start', cs, ck, flush=True)
for it in range(iters):
    new = dict(cur); p = rnd.choice([0, 1]); grp = [k for k in K if k[0] == p]
    if rnd.random() < 0.7 or len(grp) == 8:
        a, b = rnd.sample(grp, 2); new[a], new[b] = new[b], new[a]
    else:
        used = {new[k] for k in grp}; free = [l for l in range(8) if l not in used]
        new[rnd.choice(grp)] = rnd.choice(free)
    nk = kt(new); npx = proxy(new)[0] if wl else 0.0; ns = nk + wl * npx
    T = 3.0 * (1 - it / iters) + 0.2
    if ns < cs or rnd.random() < math.exp((cs - ns) / T):
        cur, cs, ck, cp = new, ns, nk, npx
        if ns < best[0]:
            best = (ns, dict(new), nk, npx); print('it', it, 'best', round(ns, 2), 'kt', nk, 'proxy', round(npx, 2), flush=True)
            json.dump({'xmask': xm, 'kt': nk, 'proxy': npx, 'xlab': {f'{k[0]},{k[1]}': v for k, v in new.items()}},
                      open(f'/work/k/mask_{xm}_{seed}_{wl}.json', 'w'))
pr = proxy(best[1]); print('done kt', best[2], 'proxy', pr, flush=True)
