"""blockscan.py file.qasm : maximal 2-qubit blocks, KAK minimal CX count (Shende-Markov-Bullock gamma test),
and whether any block on a critical path could be rebuilt shallower."""
import sys, re, numpy as np

def parse(path):
    ops = []
    for l in open(path):
        l = l.strip()
        if l.startswith('cx'):
            a, b = map(int, re.findall(r'q\[(\d+)\]', l)); ops.append(('cx', (a, b), None))
        elif l.startswith('u3'):
            p = [float(x) for x in re.search(r'\((.*)\)', l).group(1).split(',')]
            q = int(re.search(r'q\[(\d+)\]', l).group(1)); ops.append(('u3', (q,), p))
    return ops

def u3(t, p, l):
    return np.array([[np.cos(t / 2), -np.exp(1j * l) * np.sin(t / 2)],
                     [np.exp(1j * p) * np.sin(t / 2), np.exp(1j * (p + l)) * np.cos(t / 2)]])

def layers(ops, n=18):
    fr = [0] * n; lay = []
    for o in ops:
        t = max(fr[q] for q in o[1]) + 1
        for q in o[1]: fr[q] = t
        lay.append(t)
    return lay, max(fr)

def blocks(ops, n=18):
    open_ = [None] * n; pend = [[] for _ in range(n)]; B = []
    for i, o in enumerate(ops):
        if o[0] == 'u3':
            q = o[1][0]
            if open_[q] is not None: B[open_[q]]['g'].append(i)
            else: pend[q].append(i)
        else:
            a, b = o[1]
            if open_[a] is not None and open_[a] == open_[b]:
                B[open_[a]]['g'].append(i)
            else:
                for q in (a, b):
                    if open_[q] is not None:
                        k = open_[q]
                        for r in B[k]['pair']: open_[r] = None
                B.append(dict(pair=tuple(sorted((a, b))), g=sorted(pend[a] + pend[b]) + [i]))
                pend[a] = []; pend[b] = []
                open_[a] = open_[b] = len(B) - 1
    return B

def block_unitary(ops, blk):
    a, b = blk['pair']; U = np.eye(4, dtype=complex)
    I2 = np.eye(2)
    for i in blk['g']:
        o = ops[i]
        if o[0] == 'u3':
            m = u3(*o[2]); G = np.kron(m, I2) if o[1][0] == a else np.kron(I2, m)
        else:
            c, t = o[1]
            G = np.zeros((4, 4))
            for s in range(4):
                bits = [(s >> 1) & 1, s & 1]            # bits[0]=a, bits[1]=b
                ci = 0 if c == a else 1; ti = 1 - ci
                nb = list(bits)
                if nb[ci]: nb[ti] ^= 1
                G[nb[0] * 2 + nb[1], s] = 1
        U = G @ U
    return U

def min_cx(U, tol=1e-7):
    U = U / np.linalg.det(U) ** 0.25
    Y = np.kron([[0, -1j], [1j, 0]], [[0, -1j], [1j, 0]])
    g = U @ Y @ U.T @ Y; tr = np.trace(g)
    if abs(abs(tr) - 4) < tol and abs(tr.imag) < tol: return 0
    if abs(tr) < tol and np.allclose(g @ g, -np.eye(4), atol=tol): return 1
    if abs(tr.imag) < tol: return 2
    return 3

if __name__ == '__main__':
    ops = parse(sys.argv[1]); lay, D = layers(ops)
    # critical path: gate is critical if ASAP layer == ALAP layer
    fr = [D + 1] * 18; alap = [0] * len(ops)
    for i in range(len(ops) - 1, -1, -1):
        t = min(fr[q] for q in ops[i][1]) - 1
        for q in ops[i][1]: fr[q] = t
        alap[i] = t
    crit = [lay[i] == alap[i] for i in range(len(ops))]
    B = blocks(ops)
    print('depth', D, 'cx', sum(o[0] == 'cx' for o in ops), 'blocks', len(B))
    hist = {}; gains = []
    for k, blk in enumerate(B):
        ncx = sum(ops[i][0] == 'cx' for i in blk['g'])
        m = min_cx(block_unitary(ops, blk))
        hist[(ncx, m)] = hist.get((ncx, m), 0) + 1
        span = max(lay[i] for i in blk['g']) - min(lay[i] for i in blk['g']) + 1
        c = any(crit[i] for i in blk['g'])
        if m < ncx: gains.append((k, blk['pair'], ncx, m, span, c))
    print('(block cx, KAK min cx): count', sorted(hist.items()))
    print('reducible blocks', len(gains))
    for g in gains: print('  block', g[0], 'pair', g[1], 'cx', g[2], '->', g[3], 'span', g[4], 'critical', g[5])
