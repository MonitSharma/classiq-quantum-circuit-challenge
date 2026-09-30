"""DIAGNOSTIC: run the kernel beam with RDY = the wire's value-fixed time (last CX target)
instead of its last touch.  A success means the 'rotation pull-in' schedule exists."""
import pickle, sys, os, subprocess
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
from kdrv import full_gates

def valuestable(D, off, os_):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return [tgt[w] for w in range(9)]

xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
sx = valuestable(DX, 0, 0); sy = valuestable(DY, 9, 9)
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
# plan wire order is Wy + Wx; build the value-fixed vector in the same order
svec = []
for k, w in enumerate(W):
    s = (sx[w] if w < 9 else sy[w - 9])
    svec.append(s if s >= 0 else rdy[k])
print('rdy ', rdy)
print('s   ', svec, flush=True)
inp = '\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                 [f"{st} {s} {T-u}" for st, s, u in zip(ST, svec, unl)]) + '\n'
for Wb in (16000, 40000):
    for seed in (1, 2, 3, 4):
        out = f'runs/p5_{T}_{Wb}_{seed}.txt'
        env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
        p = subprocess.run(['./c/kbeamQ8', str(Wb), str(max(T - 2*min(svec), 1)), str(seed), '0.02', out, '4', '0'],
                           input=inp, capture_output=True, text=True, env=env)
        print(f'  W={Wb} s={seed} rc={p.returncode}', flush=True)
        if p.returncode == 0:
            kg = build_kg_perm(pl, out)
            print('SCHEDULE EXISTS (diagnostic only, not a valid circuit)', out, flush=True)
            sys.exit(0)
print('no schedule even with pulled-in rotations', flush=True)
