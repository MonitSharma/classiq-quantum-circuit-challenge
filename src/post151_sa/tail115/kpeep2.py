"""kpeep.py X.pkl Y.pkl kernel.out co.npy T Wn tmo outprefix
Kernel CX peephole: re-synthesize interior windows of an FEM kernel schedule with the same layers,
the same start/end rows and the same rotations, but fewer CX (SAT, satwin3 with NV=8).
Accepts a change only if the assembled circuit still passes the exact MILP at T."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, numpy as np
os.environ.update(STRICT='1', ZOCC='1', FUSE='1')
import paireval as P
import satwin3 as S
import ev116, kdrv, smilp
from postopt import parse_ops, fuse, depth, write
from canc import simplify
S.NV = 8

xp, yp, outp, cop = sys.argv[1:5]; T = int(sys.argv[5]); WNS = [int(x) for x in sys.argv[6].split(",")]; tmo = int(sys.argv[7]); pref = sys.argv[8]
DX = P.load(xp, 0); DY = P.load(yp, 1)
co = np.load(cop); terms = [int(m) for m in np.flatnonzero(abs(co) > 1e-10) if m]
ev116.CO = co; ev116.KTERMS = terms; kdrv.CO = co
pl, srdy = P.windows(DX, DY); seq, W8, ST, rdy, unl = pl
hz = P.hz_times(DX, DY, W8); occ = P.occupancy(DX, DY, W8)
zs = [(h - 1 if h > 0 else a) for a, h in zip(srdy, hz)]
zd = [(T + 1 - h if h > 0 else T - a) for a, h in zip(srdy, hz)]
ddl = [T - r for r in rdy]
busy = set()
for i in range(8):
    for l in occ[i]:
        if l > zs[i]: busy |= {l, T + 1 - l}
EXPL = None
if outp.endswith('.json'):
    EXPL = json.load(open(outp)); d, tau0 = EXPL['d'], EXPL['tau0']
    CXL = [[tuple(p) for p in l] for l in EXPL['CXL']]
else:
    L = open(outp).read().split('\n'); d, tau0 = map(int, L[0].split())
    CXL = []
    for k in range(1, d + 1):
        t = list(map(int, L[k].split())); CXL.append([(t[1 + 2 * q], t[2 + 2 * q]) for q in range(t[0])])
TS = set(terms)

def simulate(CXL):
    """build_kg_s semantics -> rows before each layer, rotations per layer, tail rotations"""
    rows = list(ST); done = set(); pend = {}; rb = []; rot = [[] for _ in CXL]
    for i in range(8):
        if rows[i] in TS and rows[i] not in done: done.add(rows[i]); pend[i] = rows[i]
    for k, layer in enumerate(CXL):
        rb.append(list(rows)); tau = tau0 + k + 1; used = {x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau > zs[i] and tau <= T - unl[i]:
                rot[k].append((i, pend.pop(i)))
        for c, tt in layer: assert tt not in pend
        for c, tt in layer:
            rows[tt] ^= rows[c]
            if rows[tt] in TS and rows[tt] not in done: done.add(rows[tt]); pend[tt] = rows[tt]
    rb.append(list(rows))
    return rb, rot, dict(pend), done

if EXPL is None:
    rb, ROT, TAIL, done = simulate(CXL)
    assert done == TS
else:
    ROT = [[tuple(p) for p in l] for l in EXPL['ROT']]; TAIL = {int(k): v for k, v in EXPL['TAIL'].items()}
    rows = list(ST); rb = []
    for lay in CXL:
        rb.append(list(rows))
        for c, t in lay: rows[t] ^= rows[c]
    rb.append(list(rows))
def build(CXL, ROT, TAIL):
    rows = list(ST); body = []; seen = []
    for k, layer in enumerate(CXL):
        for i, m in ROT[k]:
            assert rows[i] == m, (k, i, m, rows[i]); body.append(('R', W8[i], 2 * co[m])); seen.append(m)
        for c, t in layer: body.append(('C', W8[c], W8[t]))
        for c, t in layer: rows[t] ^= rows[c]
    for i, m in TAIL.items():
        assert rows[i] == m; body.append(('R', W8[i], 2 * co[m])); seen.append(m)
    assert sorted(seen) == sorted(terms), 'rotation set changed'
    sigma = list(range(18)); used = set()
    for i in range(8):
        cand = [j for j in range(8) if rows[j] == ST[i] and j not in used]
        assert cand; sigma[W8[i]] = W8[cand[0]]; used.add(cand[0])
    return [('S', sigma)] + body

def evaluate(CXL, ROT, TAIL, tag):
    kg = build(CXL, ROT, TAIL); q = f'{WK}/kp/{tag}_asm.qasm'
    d0, cx0 = ev116.assemble(DX, DY, kg, q)
    ops = fuse(simplify(fuse(parse_ops(q)), verbose=False)); ncx = sum(1 for o in ops if o[0] == 'cx')
    sol = smilp.solve(ops, T, tlim=300, verbose=False)
    path = None
    if sol is not None:
        path = f'{WK}/kp/{tag}_m{T}.qasm'; write(fuse(sol), path)
    return d0, ncx, path


os.makedirs(f'{WK}/kp', exist_ok=True)
d0, cx0, p0 = evaluate(CXL, ROT, TAIL, pref + '_base')
print('base asm', d0, 'cx', cx0, 'kernel cx', sum(len(l) for l in CXL), 'MILP', p0 is not None, flush=True)
# per-wire availability (FEM)
zbw = [set() for _ in range(8)]
for i in range(8):
    for l in occ[i]:
        if l > zs[i]: zbw[i] |= {l, T + 1 - l}
def cx_ok(k, i): tau = tau0 + k + 1; return rdy[i] < tau <= ddl[i]
def rot_ok(k, i): tau = tau0 + k + 1; return zs[i] < tau <= zd[i] and tau not in zbw[i] and tau <= T - unl[i]
EXTRA = []
_orig_solve = S.CNF.solve
def _solve(self, timeout=60):
    for c in EXTRA: self.add(c)
    return _orig_solve(self, timeout)
S.CNF.solve = _solve
NV = 8
def window_constraints(a, Wn, nP):
    cl = []
    bX = (Wn + 1) * NV * NV; bR = bX + Wn * NV * (NV - 1)
    Xv = lambda k, c, t: bX + 1 + k * NV * (NV - 1) + c * (NV - 1) + (t if t < c else t - 1)
    Rv = lambda k, w, q: bR + 1 + (k * NV + w) * nP + q
    for j in range(Wn):
        for c in range(NV):
            for t in range(NV):
                if c != t and not (cx_ok(a + j, c) and cx_ok(a + j, t)): cl.append([-Xv(j, c, t)])
            if not rot_ok(a + j, c):
                for q in range(nP): cl.append([-Rv(j, c, q)])
    return cl
def save(tag, pth, ncx):
    json.dump(dict(qasm=pth, cx=ncx, d=d, tau0=tau0, CXL=CXL, ROT=ROT, TAIL={str(k): v for k, v in TAIL.items()}),
              open(f'{WK}/kp/{tag}_best.json', 'w'))
best = cx0; improved = 0
for Wn in WNS:
    a = 0
    while a + Wn <= d:
        cur = sum(len(CXL[k]) for k in range(a, a + Wn))
        if cur == 0: a += 1; continue
        req = [m for k in range(a, a + Wn) for (_, m) in ROT[k]]
        plS = [(m, 0, 0) for m in terms]; idx = {m: j for j, m in enumerate(terms)}
        Pw = sorted({idx[m] for m in req})
        EXTRA[:] = window_constraints(a, Wn, len(Pw))
        startS = (rb[a], {0, 1, 2}, set()); endS = (rb[a + Wn], {0, 1, 2}, set(Pw))
        res = S.solve_window(plS, startS, endS, [], Wn, final=False, timeout=tmo, max_cx=cur - 1)
        if res:
            C2 = [list(x) for x in CXL]; R2 = [list(x) for x in ROT]
            for j, lay in enumerate(res):
                C2[a + j] = [(o[1], o[2]) for o in lay if o[0] == 'C']
                R2[a + j] = [(o[1], plS[o[2]][0]) for o in lay if o[0] == 'R']
            try:
                dd, ncx, pth = evaluate(C2, R2, TAIL, f'{pref}_w{Wn}a{a}')
            except AssertionError as e:
                print('Wn', Wn, 'window', a, 'build failed', e, flush=True); a += 1; continue
            print('Wn', Wn, 'window', a, 'kernel cx', cur, '->', sum(len(C2[k]) for k in range(a, a + Wn)), 'asm', dd, 'cx', ncx, 'MILP', pth is not None, flush=True)
            if pth is not None and ncx < best:
                best = ncx; CXL, ROT = C2, R2; improved += 1
                rows = list(ST); rb = []
                for lay in CXL:
                    rb.append(list(rows))
                    for c, t in lay: rows[t] ^= rows[c]
                rb.append(list(rows))
                save(pref, pth, ncx)
                continue
        else:
            print('Wn', Wn, 'window', a, 'cur', cur, 'UNSAT' if res is False else 'TO', flush=True)
        a += 1
print('done best cx', best, 'improved', improved, flush=True)
