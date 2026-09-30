"""y's code vector req[0] = 32 = the bare input bit y5, which wire 5 holds from time 0.
Could the y loader freeze wire 5 immediately?  That needs every pending rotation's mask to be
expressible without wire 5, i.e. no atom may use address bit 5.  Count how many do."""
import pickle, sys, collections
sys.path.insert(0, '.')
R = '../../artifacts/118/recipes/'
for side, f in (('y', 'y_support_89'), ('x', 'x_support_89')):
    S = pickle.load(open(R + f + '.pkl', 'rb'))
    req = S['req']
    print(f'--- {side}: req {req}')
    tot = 0; uses5 = 0
    for i in range(3):
        for m, a in S['targets'][i].items():
            if abs(a) < 1e-12: continue
            tot += 1
            s = m & 63
            if s >> 5 & 1: uses5 += 1
        cnt = sum(1 for m, a in S['targets'][i].items() if abs(a) > 1e-12)
        c5 = sum(1 for m, a in S['targets'][i].items() if abs(a) > 1e-12 and (m & 63) >> 5 & 1)
        print(f'    target {i}: {cnt} atoms, {c5} use address bit 5')
    print(f'  TOTAL {tot} atoms, {uses5} use bit 5 ({100.0*uses5/tot:.0f}%)')
    # how many address bits are used at all
    used = set()
    for i in range(3):
        for m, a in S['targets'][i].items():
            if abs(a) < 1e-12: continue
            s = m & 63
            for b in range(6):
                if s >> b & 1: used.add(b)
    print('  address bits used:', sorted(used))
