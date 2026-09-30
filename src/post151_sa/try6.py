"""Rotation pull-in: kernel rotations may fire once the wire's VALUE is fixed (last CX target),
while CX still must wait for the loader's last touch.  Builds a complete circuit if feasible."""
import pickle, sys, os, subprocess
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
from kdrv import full_gates, CO

def valuestable(D):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return tgt

def build_kg_s(pl, beampath, svec):
    seq, W, ST, rdy, unl = pl
    L = open(beampath).read().split('\n'); d, tau0 = map(int, L[0].split())
    Tset = set(KTERMS); rows = list(ST); done = set(); pend = {}
    body = [('C', c, t) for c, t in seq]
    for i in range(8):
        if rows[i] in Tset and rows[i] not in done: done.add(rows[i]); pend[i] = rows[i]
    for k in range(1, d + 1):
        t = list(map(int, L[k].split())); layer = [(t[1+2*q], t[2+2*q]) for q in range(t[0])]
        tau = tau0 + k; used = {x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau > svec[i] and tau <= (T - unl[i]):
                body.append(('R', W[i], 2 * CO[pend.pop(i)]))
        for c, tt in layer:
            assert tt not in pend
            body.append(('C', W[c], W[tt]))
        for tt, v in [(tt, rows[tt] ^ rows[c]) for c, tt in layer]:
            rows[tt] = v
            if v in Tset and v not in done: done.add(v); pend[tt] = v
    for i, v in pend.items(): body.append(('R', W[i], 2 * CO[v]))
    assert done == Tset, (len(done), len(Tset))
    sigma = list(range(18)); used = set()
    for i in range(8):
        cand = [j for j in range(8) if rows[j] == ST[i] and j not in used]
        assert cand; sigma[W[i]] = W[cand[0]]; used.add(cand[0])
    return [('S', sigma)] + body + [('C', c, t) for c, t in reversed(seq)]

xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
svec = [(sx[w] if w < 9 else sy[w - 9]) for w in W]
svec = [s if s >= 0 else rdy[k] for k, s in enumerate(svec)]
_cl=int(os.environ.get('SRCLAMP','0'))
if _cl: svec=[max(v,_cl) for v in svec]
print('rdy', rdy); print('s  ', svec, flush=True)
env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
env['SRDY'] = ','.join(map(str, svec))
if env.get('CTRL_PULL'):
    # A trailing loader Rz on a code wire commutes through a kernel CX when
    # that wire is the CX control.  The target endpoint remains last-touch
    # constrained; kbeamS's CTRL_RDY applies this asymmetrically.
    env['CTRL_RDY'] = ','.join(map(str, svec))
md = max(T - 2 * min(min(svec), min(rdy)), 1)
for Wb in (16000, 40000, 100000):
    for seed in range(1, 13):
        out = f'runs/p6_{T}_{Wb}_{seed}.txt'
        p = subprocess.run([os.environ.get('BEAMBIN','./c/kbeamS8'), str(Wb), str(md), str(seed), '0.02', out, '4', '0'],
                           input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                           [f"{st} {r} {T-u}" for st, r, u in zip(ST, rdy, unl)]) + '\n',
                           capture_output=True, text=True, env=env)
        print(f'  W={Wb} s={seed} rc={p.returncode}', flush=True)
        if p.returncode == 0:
            kg = build_kg_s(pl, out, svec)
            r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
            print('BUILT', r, out, flush=True)
            pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
            sys.exit(0)
print('INFEASIBLE at T =', T, flush=True)
