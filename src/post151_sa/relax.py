"""Diagnostic: at target T, relax ONE wire's deadline by 1 at a time and report which relaxation
makes the kernel feasible.  Identifies the true obstruction."""
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

xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [(sx[w] if w < 9 else sy[w-9]) for w in W]
svec = [s if s >= 0 else rdy[k] for k, s in enumerate(svec)]
env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
env['SRDY'] = ','.join(map(str, svec))
print('W', W); print('rdy', rdy); print('s  ', svec, flush=True)
md = max(T - min(rdy) - min(min(svec), min(rdy)), 1)
for rel in range(-1, 8):
    ddl = [T - unl[i] + (1 if i == rel else 0) for i in range(8)]
    ok = False
    for seed in (1, 2, 3, 4):
        out = f'runs/rx_{T}_{rel}_{seed}.txt'
        p = subprocess.run(['./c/kbeamS8', '16000', str(md), str(seed), '0.02', out, '4', '0'],
                           input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                           [f"{st} {r} {d}" for st, r, d in zip(ST, rdy, ddl)]) + '\n',
                           capture_output=True, text=True, env=env)
        if p.returncode == 0:
            print(f'  RELAX wire {rel} -> FEASIBLE at seed {seed} ({out})', flush=True); ok = True; break
    if not ok:
        print(f'  relax wire {rel}: still infeasible', flush=True)
print('RELAX_DONE', flush=True)
