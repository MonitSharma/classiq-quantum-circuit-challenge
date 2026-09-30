"""Refined per-wire necessary condition with rotation pull-in:
   T >= rdy + unl + cx_k        (CX need the wire after the loader's last touch)
   T >= s   + unl + touches_k   (all ops share the wire, rotations may start at the value-fixed time)
"""
import pickle, sys, collections, os
sys.path.insert(0, '.')
from kdrv import full_gates
exec(open('try2.py').read().split("xf, yf, T =")[0])

def valuestable(D):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return tgt

def measure(kg, W, rdy, unl, svec):
    rot = collections.Counter(); cxc = collections.Counter(); cxt = collections.Counter()
    for g in kg[1:]:
        if g[0] == 'C': cxc[g[1]] += 1; cxt[g[2]] += 1
        else: rot[g[1]] += 1
    out = []
    for k, w in enumerate(W):
        tc = rot[w] + cxc[w] + cxt[w]
        cx = cxc[w] + cxt[w]
        out.append((max(rdy[k] + unl[k] + cx, svec[k] + unl[k] + tc), rdy[k], svec[k], tc, cx))
    return out

pairs = [p.split('+') for p in sys.argv[1:]]
res = []
for xf, yf in pairs:
    DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
    sx = valuestable(DX); sy = valuestable(DY)
    pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
    svec = [(sx[w] if w < 9 else sy[w-9]) for w in W]
    svec = [s if s >= 0 else rdy[k] for k, s in enumerate(svec)]
    T = 118; ok = None
    for Wb in (6000, 16000):
        for seed in (1, 2, 3):
            out = f'runs/rf_{os.path.basename(xf)[:-4]}_{os.path.basename(yf)[:-4]}_{Wb}_{seed}.txt'
            env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
            p = subprocess.run(['./c/kbeamQ8', str(Wb), str(max(T - 2*min(rdy), 1)), str(seed), '0.02', out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                               capture_output=True, text=True, env=env)
            if p.returncode == 0:
                ok = build_kg_perm(pl, out); break
        if ok: break
    if ok is None:
        print(f'{os.path.basename(xf)}+{os.path.basename(yf)}: no T=118 schedule'); continue
    m = measure(ok, W, rdy, unl, svec)
    bound = max(v[0] for v in m)
    print(f'{os.path.basename(xf)}+{os.path.basename(yf)}: refined bound T >= {bound}   rdy {rdy} s {svec}', flush=True)
    print(f'    per wire (bound, rdy, s, touches, cx): {[v[0] for v in m]}', flush=True)
    res.append((bound, xf, yf))
res.sort()
print('BEST:', [(b, os.path.basename(x)) for b, x, y in res[:4]])
