import pickle, sys, os, subprocess
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
print('W', W, 'rdy', rdy, flush=True)
inp = '\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                 [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n'
for Wb in (40000, 100000):
    for kch in (60, 200):
        for mu in (0.02, 0.035, 0.05):
            for seed in range(1, 9):
                out = f'runs/p4_{T}_{Wb}_{kch}_{mu}_{seed}.txt'
                env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
                env['KCH'] = str(kch)
                env['md'] = '1'
                p = subprocess.run(['./c/kbeamQ8', str(Wb), str(max(T - 2 * min(rdy), 1)), str(seed), str(mu), out, '4', '0'],
                                   input=inp, capture_output=True, text=True, env=env)
                print(f'  W={Wb} KCH={kch} mu={mu} s={seed} rc={p.returncode}', flush=True)
                if p.returncode == 0:
                    kg = build_kg_perm(pl, out)
                    r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                    print('FEASIBLE', r, out, flush=True)
                    pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                    sys.exit(0)
print('INFEASIBLE at T =', T, flush=True)
