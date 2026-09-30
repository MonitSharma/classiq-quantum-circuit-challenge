# Joint T-search with EXPLICIT support paths for either side (try8 hard-codes the champion supports).
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

def load_side(supp_path, loader_path, tag):
    D0 = pickle.load(open(supp_path, 'rb'))
    if loader_path == 'champ':
        return D0
    bd, seq = load_beam(loader_path)
    d, pen, g = sa4(D0, seq, tag=tag, binary='./c/sa4')
    chk = check_loader2(g, D0['newcode'])
    assert pen == 0 and chk['max_dev'] < 1e-9, (loader_path, pen, chk['max_dev'])
    D = dict(D0); D['gates'] = g; D['fix'] = []; D['depth'] = max(profile(g)[0])
    return D

def build_kg_s(pl, beampath, svec, T):
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

xs, xl, ys, yl, T = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
DX = load_side(xs, xl, 'tx'); DY = load_side(ys, yl, 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w-9]) if (sx[w] if w < 9 else sy[w-9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
print('rdy', rdy); print('s  ', svec, flush=True)
env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
env['SRDY'] = ','.join(map(str, svec))
md = max(T - min(rdy) - min(min(svec), min(rdy)), 1)
for Wb in (16000, 40000):
    for seed in range(1, 9):
        out = 'runs/p9_%d_%d_%d.txt' % (T, Wb, seed)
        p = subprocess.run(['./c/kbeamS8', str(Wb), str(md), str(seed), '0.02', out, '4', '0'],
                           input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                           [f"{st} {r} {T-u}" for st, r, u in zip(ST, rdy, unl)]) + '\n',
                           capture_output=True, text=True, env=env)
        print('  W=%d s=%d rc=%d' % (Wb, seed, p.returncode), flush=True)
        if p.returncode == 0:
            kg = build_kg_s(pl, out, svec, T)
            r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
            print('BUILT', r, out, flush=True)
            pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
            sys.exit(0)
print('INFEASIBLE at T =', T, flush=True)
