"""ranks.py blocks.json [minCX] : for each block (convex, qubits Q), sparse-simulate all 4096 clean inputs through the
block's ancestors and compute the rank of the reduced mixture support on Q (don't-care freedom if rank < 2^|Q|)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, json, numpy as np
import blockscan as BS
QASM = f'{WK}/kp/cx569_a33_m115.qasm'
ops = BS.parse(QASM); n = len(ops)
last = [None] * 18; pred = [[] for _ in range(n)]
for i, o in enumerate(ops):
    for w in o[1]:
        if last[w] is not None: pred[i].append(last[w])
        last[w] = i
anc = [0] * n
for i in range(n):
    m = 0
    for j in pred[i]: m |= (1 << j) | anc[j]
    anc[i] = m
N = 4096; tol = 1e-12

def compress(idx, a):
    order = np.argsort(idx, axis=1); idx = np.take_along_axis(idx, order, 1); a = np.take_along_axis(a, order, 1)
    first = np.ones(idx.shape, bool); first[:, 1:] = idx[:, 1:] != idx[:, :-1]
    group = np.cumsum(first, axis=1) - 1; w = int(group[:, -1].max()) + 1
    target = (np.arange(N)[:, None] * w + group).ravel()
    sums = (np.bincount(target, weights=a.real.ravel(), minlength=N * w) + 1j * np.bincount(target, weights=a.imag.ravel(), minlength=N * w)).reshape(N, w)
    outidx = np.zeros((N, w), np.int64); rr = np.broadcast_to(np.arange(N)[:, None], idx.shape)[first]
    outidx[rr, group[first]] = idx[first]
    keep = np.abs(sums) > tol; width = int(keep.sum(1).max()); dest = np.cumsum(keep, axis=1) - 1
    rr = np.broadcast_to(np.arange(N)[:, None], sums.shape)[keep]
    oo = np.zeros((N, width), np.int64); aa = np.zeros((N, width), complex)
    oo[rr, dest[keep]] = outidx[keep]; aa[rr, dest[keep]] = sums[keep]
    return oo, aa

def simulate(gates):
    idx = np.arange(N, dtype=np.int64)[:, None]; amp = np.ones((N, 1), complex)
    for i in gates:
        o = ops[i]
        if o[0] == 'cx':
            c, t = o[1]; idx = idx ^ (((idx >> c) & 1) << t)
        else:
            q = o[1][0]; th, ph, la = o[2]; c = np.cos(th / 2); s = np.sin(th / 2); bit = (idx >> q) & 1
            if abs(s) < 1e-14: amp = amp * np.where(bit, np.exp(1j * (ph + la)) * c, c)
            elif abs(c) < 1e-14: amp = amp * np.where(bit, -np.exp(1j * la) * s, np.exp(1j * ph) * s); idx = idx ^ (1 << q)
            else:
                aa = amp * np.where(bit, np.exp(1j * (ph + la)) * c, c); bb = amp * np.where(bit, -np.exp(1j * la) * s, np.exp(1j * ph) * s)
                idx, amp = compress(np.concatenate([idx, idx ^ (1 << q)], 1), np.concatenate([aa, bb], 1))
    return idx, amp

def support(idx, amp, Q):
    qm = sum(1 << q for q in Q); rest = idx & ~qm
    loc = np.zeros(idx.shape, np.int64)
    for k, q in enumerate(Q): loc |= ((idx >> q) & 1) << (len(Q) - 1 - k)
    key = np.arange(N)[:, None].astype(np.int64) * (1 << 18) + rest
    m = np.abs(amp) > tol
    keys, inv = np.unique(key[m], return_inverse=True)
    V = np.zeros((len(keys), 1 << len(Q)), complex); np.add.at(V, (inv, loc[m]), amp[m])
    G = V.conj().T @ V; ev, evec = np.linalg.eigh(G)
    r = int(np.sum(ev > 1e-9 * ev.max()))
    return r, evec[:, ev > 1e-9 * ev.max()]

if __name__ == '__main__':
    B = json.load(open(sys.argv[1])); mincx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    out = []
    for b in B:
        if b['ncx'] < mincx: continue
        am = 0
        for i in b['g']: am |= anc[i]
        gates = [i for i in range(n) if (am >> i) & 1]
        idx, amp = simulate(gates); r, P = support(idx, amp, b['q'])
        print(b['q'], 't0', b['t0'], 'cx', b['ncx'], 'rank', r, '/', 1 << len(b['q']), flush=True)
        out.append(dict(q=b['q'], t0=b['t0'], rank=r))
    json.dump(out, open(sys.argv[1].replace('.json', '_ranks.json'), 'w'))
