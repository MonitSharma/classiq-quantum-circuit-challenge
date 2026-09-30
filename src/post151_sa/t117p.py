"""T=117 kernel feasibility WITH PERMSET (kernel may end in a permutation of code wires)."""
import pickle, sys, os, subprocess, time
sys.path.insert(0, '.')
from kgen2 import build_kg_perm
from kdrv import assemble, KTERMS

R = '../../artifacts/118/recipes/'
DX = pickle.load(open(R + 'x_loader_d44.pkl', 'rb'))
DY = pickle.load(open(R + 'y_loader_d46_blkw.pkl', 'rb'))
pl, _ = pickle.load(open(R + 'kernel_plan_and_gates_118.pkl', 'rb'))
seq, W, ST, rdy, unl = pl

T = int(sys.argv[1])
masks = [0b00001111, 0b11110000, 0b11111111, 0b11000011, 0b00111100]
found = []
for pm_ in masks:
    for Wb in (6000, 20000):
        for mu in (0.02, 0.05):
            for seed in (1, 2, 3, 4):
                out = f'runs/p{T}_{pm_}_{Wb}_{mu}_{seed}.txt'
                env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['PERMSET'] = str(pm_)
                md = max(T - 2 * min(rdy), 1)
                p = subprocess.run(['./c/kbeamP8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                                   input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                                   [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                                   capture_output=True, text=True, env=env)
                if p.returncode == 0:
                    kg = build_kg_perm(pl, out)
                    sig = kg[0][1]
                    r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                    print(f'FEASIBLE T={T} PERMSET={pm_:08b} W={Wb} mu={mu} s={seed} sigma={sig} -> {r}', flush=True)
                    pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                    found.append(out)
                    break
        if found: break
    if found: break
print('RESULT', T, found, flush=True)
