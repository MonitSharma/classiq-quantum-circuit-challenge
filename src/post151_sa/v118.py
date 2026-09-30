import pickle, sys
sys.path.insert(0, '.')
from kdrv import profile, full_gates
from sim import symbolic_final
from kgen import side_plan
R = '../../artifacts/118/recipes/'
for name in ('x_loader_d44', 'y_loader_d46_blkw', 'x_support_89', 'y_support_89'):
    D = pickle.load(open(R + name + '.pkl', 'rb'))
    g = full_gates(D); e, l = profile(g)
    tg = D['targets']
    rot = sum(len(tg[i]) for i in range(3))
    rows = symbolic_final(g)
    fx, W, co, rdy = side_plan(g, e, D, 0)
    print(name, 'side', D['side'], 'depth', max(e), 'rot', rot,
          'supports', [len(tg[i]) for i in range(3)])
    print('   prof', e)
    print('   rows', rows)
    print('   req', D['req'], 'code wires(local)', W, 'coords', co,
          'rdy', rdy, 'max', max(rdy), 'sum', sum(rdy), 'fix', len(fx))
