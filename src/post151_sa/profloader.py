import pickle, sys, collections
sys.path.insert(0, '.')
from kdrv import profile
D = pickle.load(open(sys.argv[1], 'rb'))
g = D['gates']
# per-layer occupancy with the repository's ASAP rule
wt = [0] * 9
layers = []
for gg in g:
    if gg[0][0] == 'cx':
        c, t = gg[1], gg[2]
    else:
        c = t = gg[1]
    l = max(wt[c], wt[t]) + 1
    wt[c] = wt[t] = l
    layers.append((l, gg))
D_ = max(wt)
print('depth', D_)
occ = collections.defaultdict(lambda: ['.'] * 9)
for l, gg in layers:
    if gg[0][0] == 'cx':
        occ[l][gg[1]] = 'c'; occ[l][gg[2]] = 't'
    else:
        occ[l][gg[1]] = 'R'
for l in range(1, D_ + 1):
    row = occ[l]
    print(f'{l:3d} {"".join(row)}  cx={row.count("c")} rot={row.count("R")}')
print('targets', {k: len(v) for k, v in D['targets'].items()})
