import pickle, sys, os
sys.path.insert(0, '.')
from kdrv import profile
from sim import symbolic_final, check_loader2

def evalframe(path):
    D = pickle.load(open(path, 'rb'))
    g = D['gates']
    e, _ = profile(g)
    req = D['req']
    span = {}
    for b in range(1, 16):
        v = 0
        for k in range(4):
            if b >> k & 1: v ^= req[k]
        span[v] = b
    rows = symbolic_final(g)
    ins = sorted((e[w], w, rows[w]) for w in range(9) if rows[w] in span)
    chk = check_loader2(g, D['newcode'])
    return dict(depth=max(e), prof=e, inspan=[t for t, _, _ in ins][:6],
                inspan_wires=[w for _, w, _ in ins][:6],
                dev=chk['max_dev'], rot=sum(1 for x in g if x[0][0] == 'rz'))

if __name__ == '__main__':
    for p in sys.argv[1:]:
        try:
            r = evalframe(p)
            print(os.path.basename(p), 'depth', r['depth'], 'inspan', r['inspan'],
                  'wires', r['inspan_wires'], 'rot', r['rot'], 'dev %.0e' % r['dev'], flush=True)
        except Exception as ex:
            print(os.path.basename(p), 'FAIL', repr(ex)[:120], flush=True)
