import pickle, sys, os, subprocess
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
xf, yf, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
pl = plan(DX, DY)
seq_, W, ST, rdy, unl = pl
print('W', W, 'rdy', rdy, flush=True)
md = max(T - 2 * min(rdy), 1)
for Wb in (20000, 40000, 60000):
    for mu in (0.02, 0.035, 0.05):
        for seed in range(1, 7):
            out = f'runs/big_{T}_{Wb}_{mu}_{seed}.txt'
            env = dict(os.environ); env['SINGLES_PENDING'] = '1'; env['TOUCHBAD'] = '1'
            p = subprocess.run(['./c/kbeamQ8', str(Wb), str(md), str(seed), str(mu), out, '4', '0'],
                               input='\n'.join([str(len(KTERMS)), ' '.join(map(str, KTERMS))] +
                               [f"{s} {r} {T-u}" for s, r, u in zip(ST, rdy, unl)]) + '\n',
                               capture_output=True, text=True, env=env)
            print(f'  W={Wb} mu={mu} s={seed} rc={p.returncode}', flush=True)
            if p.returncode == 0:
                kg = build_kg_perm(pl, out)
                r = assemble(DX, DY, kg, out.replace('.txt', '.qasm'))
                print('FEASIBLE', r, out, flush=True)
                pickle.dump((pl, kg), open(out.replace('.txt', '.pkl'), 'wb'))
                sys.exit(0)
print('INFEASIBLE at T =', T, flush=True)
