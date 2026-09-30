"""Assemble each (x,y) loader pair at T=118 and report the measured per-wire 2*ready+touches."""
import pickle, sys, os, subprocess, collections, itertools
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])

def measure(kg, W, rdy):
    rot = collections.Counter(); cxc = collections.Counter(); cxt = collections.Counter()
    for g in kg[1:]:
        if g[0] == 'C': cxc[g[1]] += 1; cxt[g[2]] += 1
        else: rot[g[1]] += 1
    vals = []
    for k, w in enumerate(W):
        tc = rot[w] + cxc[w] + cxt[w]
        vals.append((2 * rdy[k] + tc, rdy[k], tc, w))
    return vals

pairs = []
for spec in sys.argv[1:]:
    xf, yf = spec.split('+')
    pairs.append((xf, yf))
res = []
for xf, yf in pairs:
    DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
    pl = plan(DX, DY)
    seq_, W, ST, rdy, unl = pl
    T = 118
    ok = None
    for Wb in (6000, 16000):
        for seed in (1, 2):
            out = f'runs/sp_{os.path.basename(xf)[:-4]}_{os.path.basename(yf)[:-4]}_{Wb}_{seed}.txt'
            env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
            md = max(T - 2 * min(rdy), 1)
            p = subprocess.run(['./c/kbeamQ8', str(Wb), str(md), str(seed), '0.02', out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                               capture_output=True, text=True, env=env)
            if p.returncode == 0:
                kg = build_kg_perm(pl, out); ok = kg; break
        if ok: break
    if ok is None:
        print(f'{xf} + {yf}: no T=118 schedule', flush=True); continue
    vals = measure(ok, W, rdy)
    mx = max(v[0] for v in vals)
    over = sum(1 for v in vals if v[0] > 117)
    print(f'{os.path.basename(xf)} + {os.path.basename(yf)}: rdy {rdy} MAX {mx} over117 {over} vals {[v[0] for v in vals]}', flush=True)
    res.append((mx, over, xf, yf))
    if mx <= 115:
        pickle.dump((pl, ok), open(f'runs/PAIR_{os.path.basename(xf)[:-4]}_{os.path.basename(yf)[:-4]}.pkl', 'wb'))
res.sort()
print('BEST:', res[:4], flush=True)
