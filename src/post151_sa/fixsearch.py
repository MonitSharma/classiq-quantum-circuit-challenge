"""Can a longer start-of-kernel CX fixup deliver the code vectors on better wires / earlier?"""
import pickle, sys, itertools
sys.path.insert(0, '.')
from kdrv import full_gates, profile
from kgen import side_plan
from sim import symbolic_final

R = '../../artifacts/118/recipes/'
D = {'x': pickle.load(open(R + 'x_loader_d44.pkl', 'rb')),
     'y': pickle.load(open(R + 'y_loader_d46_blkw.pkl', 'rb'))}
for side in ('x', 'y'):
    g = full_gates(D[side]); e, _ = profile(g)
    rows = symbolic_final(g)
    print(f'--- {side}: e {e} rows {rows} req {D[side]["req"]}')
    for ml in (0, 1, 2, 3):
        fx, W, co, rdy = side_plan(g, e, D[side], 0, maxlen=ml)
        print(f'   maxlen={ml}: seq {fx} W {W} coords {co} rdy {rdy} max {max(rdy)} sum {sum(rdy)}', flush=True)
    # also try a much longer greedy fixup directly
    sm = {}
    for b in range(1, 16):
        v = 0
        for k in range(4):
            if b >> k & 1: v ^= D[side]['req'][k]
        sm[v] = b
    print('   in-span wires:', [(w, rows[w], sm[rows[w]]) for w in range(9) if rows[w] in sm])
