import pickle, sys, glob
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2, symbolic_final
from kdrv import profile
D = pickle.load(open('runs/s118y.pkl', 'rb'))
print('D targets sizes', [len(D['targets'][i]) for i in range(3)])
for p in sorted(glob.glob(sys.argv[1]))[:4]:
    raw = open(p).read().split('\n')
    print('==', p, 'header', raw[0], 'nonempty layers', sum(1 for l in raw[1:] if l.strip()))
    bd, seq = load_beam(p)
    print('   beam layers', bd, 'cx', len(seq))
    # how many rotations must be fired?
    need = sum(len(D['targets'][i]) for i in range(3))
    d, pen, g = sa4(D, seq, tag='dbg', binary='./c/sa4')
    print('   sa4 depth', d, 'pen', pen, 'gates', len(g), 'rz', sum(1 for x in g if x[0][0] == 'rz'))
    chk = check_loader2(g, D['newcode'])
    print('   max_dev', chk['max_dev'])
    rows = symbolic_final(g)
    print('   rows', rows)
    e, _ = profile(g)
    print('   prof', e)
