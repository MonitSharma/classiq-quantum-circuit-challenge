import pickle, sys, time, os
sys.path.insert(0, '.')
from kgen import run_beam, build_kg, plan
from kdrv import assemble

R = '../../artifacts/124/recipes/'
DX = pickle.load(open(R + 'x_loader_star47_span.pkl', 'rb'))
DY = pickle.load(open(R + 'y_loader_beam47_span.pkl', 'rb'))
pl = pickle.load(open(R + 'kernel_plan.pkl', 'rb'))
print('rdy', pl[3], 'unl', pl[4], flush=True)

T = int(sys.argv[1]); Wb = int(sys.argv[2]); mu = float(sys.argv[3]); seeds = [int(s) for s in sys.argv[4].split(',')]
for seed in seeds:
    out = f'runs/T{T}_W{Wb}_s{seed}.txt'
    t0 = time.time()
    rc = run_beam(pl, T, Wb, mu, seed, out)
    dt = time.time() - t0
    print(f'T={T} W={Wb} seed={seed} rc={rc} {dt:.0f}s', flush=True)
    if rc == 0:
        kg = build_kg(pl, out)
        q = out.replace('.txt', '.qasm')
        print('ASSEMBLED', T, assemble(DX, DY, kg, q), q, flush=True)
        pickle.dump((pl, kg), open(q.replace('.qasm', '.pkl'), 'wb'))
        break
