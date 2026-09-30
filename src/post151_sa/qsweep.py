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
binary = sys.argv[2]
best = None
n = 0
for Wb in (1500, 2500, 4000, 8000):
    for mu in (0.02, 0.03, 0.05):
        for kch in (20, 60):
            for seed in (1, 2, 3):
                n += 1
                inp = [str(len(KTERMS)), ' '.join(map(str, KTERMS))] + \
                      [f"{s} {r} {Tm-u}" for s, r, u in zip(ST, rdy, unl)]
                out = f'runs/s{Tm}_{Wb}_{mu}_{kch}_{seed}.txt'
                env = dict(os.environ); env['SINGLES_PENDING'] = '1'
                env['KCH'] = str(kch); env['TOUCHOK'] = '1'; env['TOUCHBAD'] = '1'
                md = max(Tm - 74, 1)
                t0 = time.time()
                p = subprocess.run([binary, str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                                   input='\n'.join(inp) + '\n', capture_output=True, text=True, env=env)
                dt = time.time() - t0
                if p.returncode == 0:
                    kg = build_kg_perm(pl, out)
                    r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                    print(f'[{n}] T={Tm} W={Wb} mu={mu} kch={kch} s={seed} {dt:.0f}s -> real {r}', flush=True)
                    if best is None or r[0] < best[0]:
                        best = (r[0], r[1], out.replace('.txt', '.qasm'))
                        pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                        if r[0] <= Tm:
                            print('TARGET REACHED', best, flush=True)
                            sys.exit(0)
                else:
                    print(f'[{n}] T={Tm} W={Wb} mu={mu} kch={kch} s={seed} fail {dt:.0f}s', flush=True)
print('BEST', best, flush=True)
