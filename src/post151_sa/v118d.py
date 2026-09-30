import pickle, sys, math
sys.path.insert(0, '.')
R = '../../artifacts/118/recipes/'
print('=== check the parity identity n_S/2 = S.v (mod 2) used by lift2.py ===')
for side, f in (('x', 'x_loader_d44'), ('y', 'y_loader_d46_blkw')):
    D = pickle.load(open(R + f + '.pkl', 'rb'))
    code = D['newcode']
    for tgt in (0, 2):
        L = [(c >> tgt) & 1 for c in code]
        if sum(L) % 2: continue
        v = 0
        for z, b in enumerate(L):
            if b: v ^= z
        bad = 0
        for S in range(64):
            nS = sum(L[z] * (-1) ** (bin(S & z).count('1')) for z in range(64))
            if (nS // 2) % 2 != bin(S & v).count('1') % 2: bad += 1
        print(f'  {side} target {tgt}: |L|={sum(L)} v={v} identity violations {bad}/64')
