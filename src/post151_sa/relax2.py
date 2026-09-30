"""Decisive diagnostic.  Base target Tb=117 (known feasible).  Tighten exactly ONE wire to
Tb-1 = 116's deadline.  If every such tightening is feasible, the model is consistent and
T=116 is genuinely an all-wires-tight problem; if some tightening is infeasible, the model
over-constrains that wire."""
import pickle, sys, os, subprocess
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

xf, yf = sys.argv[1], sys.argv[2]
TB = int(sys.argv[3]) if len(sys.argv) > 3 else 117
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w-9]) if (sx[w] if w < 9 else sy[w-9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
env['SRDY'] = ','.join(map(str, svec))
print('rdy', rdy, 's', svec, flush=True)
for tight in range(8):
    ddl = [TB - unl[i] - (1 if i == tight else 0) for i in range(8)]
    got = None
    for Wb in (6000, 16000):
        for seed in (1, 2, 3):
            out = f'runs/r2_{TB}_{tight}_{Wb}_{seed}.txt'
            p = subprocess.run(['./c/kbeamS8', str(Wb), str(max(TB - min(rdy) - min(min(svec), min(rdy)), 1)),
                                str(seed), '0.02', out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{st} {r} {d}" for st, r, d in zip(ST, rdy, ddl)]) + '\n',
                               capture_output=True, text=True, env=env)
            if p.returncode == 0: got = (Wb, seed, out); break
        if got: break
    print(f'  tighten wire {tight} to {TB-1}: ' + (f'FEASIBLE {got}' if got else 'INFEASIBLE'), flush=True)
print('RELAX2_DONE', flush=True)
