import pickle, sys, os, subprocess, time
sys.path.insert(0, '.')
from kgen2 import build_kg_perm
from kdrv import assemble, KTERMS

R = '../../artifacts/124/recipes/'
DX = pickle.load(open(R + 'x_loader_star47_span.pkl', 'rb'))
DY = pickle.load(open(R + 'y_loader_beam47_span.pkl', 'rb'))
pl = pickle.load(open(R + 'kernel_plan.pkl', 'rb'))
seq, W, ST, rdy, unl = pl

Tm = int(sys.argv[1])
Wb = int(sys.argv[2]); mu = float(sys.argv[3]); kch = int(sys.argv[4])
seeds = [int(s) for s in sys.argv[5].split(',')]
inp = [str(len(KTERMS)), ' '.join(map(str, KTERMS))] + [f"{s} {r} {Tm-u}" for s, r, u in zip(ST, rdy, unl)]
best = None
for seed in seeds:
    out = f'runs/m{Tm}_W{Wb}_mu{mu}_k{kch}_s{seed}.txt'
    env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['KCH'] = str(kch)
    md = max(Tm - 74, 1)
    t0 = time.time()
    p = subprocess.run(['./c/kbeamP8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                       input='\n'.join(inp) + '\n', capture_output=True, text=True, env=env)
    dt = time.time() - t0
    if p.returncode != 0:
        print(f'model T={Tm} seed={seed} infeasible {dt:.0f}s', flush=True)
        continue
    kg = build_kg_perm(pl, out)
    r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
    print(f'model T={Tm} W={Wb} mu={mu} kch={kch} seed={seed} {dt:.0f}s -> real {r}', flush=True)
    if best is None or r[0] < best[0]:
        best = (r[0], r[1], out.replace('.txt', '.qasm'))
        pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
print('BEST', best, flush=True)
