"""For every candidate y loader, compute the refined T bound against the champion x loader."""
import pickle, sys, glob, os, collections
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
from kdrv import full_gates

def valuestable(D):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return tgt

DX = rebuild('x_loader_d44', 'champ', 'tx')
sx = valuestable(DX)
files = sorted(set(f for p in sys.argv[1:] for f in glob.glob(p)))
res = []
for yf in files:
    try:
        DY = rebuild('y_loader_d46_blkw', yf, 'ty')
        pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
        sy = valuestable(DY)
        svec = [(sx[w] if w < 9 else sy[w-9]) for w in W]
        svec = [s if s >= 0 else rdy[k] for k, s in enumerate(svec)]
        T = 118; kg = None
        for Wb in (6000, 16000):
            for seed in (1, 2):
                out = f'runs/bs_{os.path.basename(yf)[:-4]}_{Wb}_{seed}.txt'
                env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
                p = subprocess.run(['./c/kbeamQ8', str(Wb), str(max(T-2*min(rdy), 1)), str(seed), '0.02', out, '4', '0'],
                                   input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                                   [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                                   capture_output=True, text=True, env=env)
                if p.returncode == 0: kg = build_kg_perm(pl, out); break
            if kg: break
        if kg is None: continue
        rot = collections.Counter(); cxc = collections.Counter(); cxt = collections.Counter()
        for g in kg[1:]:
            if g[0] == 'C': cxc[g[1]] += 1; cxt[g[2]] += 1
            else: rot[g[1]] += 1
        vals = []
        for k, w in enumerate(W):
            tc = rot[w]+cxc[w]+cxt[w]; cx = cxc[w]+cxt[w]
            vals.append(max(rdy[k]+unl[k]+cx, svec[k]+unl[k]+tc))
        b = max(vals)
        res.append((b, os.path.basename(yf), rdy, vals))
        print(f'bound {b}  {os.path.basename(yf)}  rdy {rdy}  vals {vals}', flush=True)
    except Exception as ex:
        print('ERR', os.path.basename(yf), repr(ex)[:80], flush=True)
res.sort()
print('--- best ---', flush=True)
for b, p, rdy, vals in res[:6]: print(f'  {b}  {p}  rdy {rdy}')
