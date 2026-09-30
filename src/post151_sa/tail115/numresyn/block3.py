"""block3.py file.qasm : greedy convex 3-qubit blocks (a block stops taking new wires once any wire is closed).
Prints per-block CX count, layer span, critical flag; dumps blocks to block3.json."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, json
from blockscan import parse, layers

def blocks3(ops, n=18, K=3):
    open_ = [None] * n; B = []
    def close(q):
        k = open_[q]
        if k is None: return
        B[k]['open'].discard(q); B[k]['sealed'] = True; open_[q] = None
    for i, o in enumerate(ops):
        qs = o[1]
        ks = {open_[q] for q in qs}
        if len(ks) == 1 and None not in ks:
            B[open_[qs[0]]]['g'].append(i); continue
        # try to extend the block of one operand with the fresh other wire
        done = False
        if len(qs) == 2:
            for x, y in (qs, qs[::-1]):
                k = open_[x]
                if k is not None and not B[k]['sealed'] and len(B[k]['q'] | {y}) <= K and open_[y] is None:
                    B[k]['q'].add(y); B[k]['open'].add(y); open_[y] = k; B[k]['g'].append(i); done = True; break
                if k is not None and not B[k]['sealed'] and open_[y] is not None and open_[y] != k:
                    # merge only if the other block is a pure single-wire fragment (no gates on other wires)
                    k2 = open_[y]
                    if B[k2]['q'] == {y} and not B[k2]['sealed'] and len(B[k]['q'] | {y}) <= K:
                        B[k]['q'].add(y); B[k]['open'].add(y); B[k]['g'] += B[k2]['g']; B[k2]['g'] = []; B[k2]['q'] = set()
                        open_[y] = k; B[k]['g'].append(i); done = True; break
        if done: continue
        for q in qs: close(q)
        B.append(dict(q=set(qs), open=set(qs), sealed=False, g=[i]))
        for q in qs: open_[q] = len(B) - 1
    out = []
    for b in B:
        if b['g']: out.append(dict(q=sorted(b['q']), g=sorted(b['g'])))
    return out

if __name__ == '__main__':
    ops = parse(sys.argv[1]); lay, D = layers(ops)
    fr = [D + 1] * 18; alap = [0] * len(ops)
    for i in range(len(ops) - 1, -1, -1):
        t = min(fr[q] for q in ops[i][1]) - 1
        for q in ops[i][1]: fr[q] = t
        alap[i] = t
    B = blocks3(ops)
    assert sorted(i for b in B for i in b['g']) == list(range(len(ops)))
    rows = []
    for k, b in enumerate(B):
        ncx = sum(ops[i][0] == 'cx' for i in b['g'])
        span = max(lay[i] for i in b['g']) - min(lay[i] for i in b['g']) + 1
        crit = sum(lay[i] == alap[i] for i in b['g'])
        b.update(ncx=ncx, span=span, crit=crit, t0=min(lay[i] for i in b['g']))
        rows.append(b)
    from collections import Counter
    print('blocks', len(B), 'nq hist', Counter(len(b['q']) for b in B), 'cx hist', sorted(Counter(b['ncx'] for b in B).items()))
    big = [b for b in rows if len(b['q']) == 3 and b['ncx'] >= 3]
    big.sort(key=lambda b: -b['ncx'])
    for b in big[:40]: print(b['q'], 'cx', b['ncx'], 'span', b['span'], 't0', b['t0'], 'critgates', b['crit'])
    json.dump(rows, open(f'{WK}/block3.json', 'w'))
