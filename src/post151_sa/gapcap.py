"""The value-fixed gap on a code wire = the number of support atoms that can fire there AFTER the
wire's last CX target.  A rotation fires on a wire when the wire's row equals the atom's mask, so the
gap is capped by the number of atoms whose mask equals that wire's code-vector row.
Count them for the x Lx1 wire (row 128) and the whole x support."""
import pickle, sys, collections
sys.path.insert(0, '.')
R = '../../artifacts/118/recipes/'
S = pickle.load(open(R + 'x_support_89.pkl', 'rb'))
req = S['req']
print('x req', req)
allmasks = []
for i in range(3):
    for m, a in S['targets'][i].items():
        if abs(a) > 1e-12: allmasks.append((m, i))
cnt = collections.Counter(m for m, i in allmasks)
print('atoms', len(allmasks), 'distinct masks', len(cnt))
for row, name in ((128, 'Lx1'), (64, 'Lx0'), (256, 'Lx2'), (48, 'px')):
    n = sum(v for m, v in cnt.items() if m == row)
    print(f'  atoms with mask == {row} ({name} wire row): {n}')
print()
print('masks with exactly one label bit and low s (bit6,7,8 = labels):')
for m, i in sorted(set(allmasks)):
    if m < 512 and bin(m).count('1') <= 2:
        print(f'   mask {m:4d} target {i} popcount {bin(m).count("1")}')
