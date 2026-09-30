import pickle, sys, math
sys.path.insert(0, '.')
R = '../../artifacts/118/recipes/'
print('=== the mod-2pi lift argument, checked on the real label functions ===')
for side, f in (('x', 'x_loader_d44'), ('y', 'y_loader_d46_blkw')):
    D = pickle.load(open(R + f + '.pkl', 'rb'))
    code = D['newcode']
    for tgt in range(3):
        L = [(c >> tgt) & 1 for c in code]
        w = sum(L)
        v = 0
        for z, b in enumerate(L):
            if b: v ^= z
        # Walsh transform of the +-1 form
        n = [0] * 64
        for S in range(64):
            n[S] = sum((1 - 2 * L[z]) * (-1) ** (bin(S & z).count('1')) for z in range(64))
        even = all(x % 2 == 0 for x in n)
        nz = sum(1 for S in range(1, 64) if n[S] != 0)
        killable = sum(1 for S in range(64) if bin(S & v).count('1') % 2 == 0)
        print(f'  {side} target {tgt}: |L| = {w} (even: {w%2==0}), v = {v} '
              f'(nonzero: {v!=0}), all Walsh coefs even: {even}, '
              f'nonzero coefs {nz}/63, |v^perp| = {killable}/64')
    print()
print('=== atoms actually used per target ===')
for side, f in (('x', 'x_loader_d44'), ('y', 'y_loader_d46_blkw')):
    D = pickle.load(open(R + f + '.pkl', 'rb'))
    tg = D['targets']
    print(f'  {side}: supports {[len(tg[i]) for i in range(3)]} total {sum(len(tg[i]) for i in range(3))}')
