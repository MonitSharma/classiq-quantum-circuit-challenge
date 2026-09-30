"""Does a cheap in-place Toffoli permutation P of the 6 coordinate wires shrink the Walsh support
of the protected 3-bit labels (best GL(3) frame)?  Parity code bit must stay linear."""
import sys, json, itertools
import numpy as np
sys.path.insert(0, 'src')
import two_stage_oracle as ts
from post258_two_stage_anf import decode
rec = json.load(open('artifacts/185/class_codes.json'))
yl, xl = decode(rec['ylab']), decode(rec['xlab'])
LAB = {'y': [yl[((y >> 5) & 1, ts.ROWCLS[y])] for y in range(64)],
       'x': [xl[((x & 48).bit_count() & 1, ts.COLCLS[x])] for x in range(64)]}
PMASK = {'y': 32, 'x': 48}
H = np.array([[(-1) ** bin(a & b).count('1') for b in range(64)] for a in range(64)])
FRAMES = [f for f in itertools.combinations(range(1, 8), 3) if len({a ^ b for a in f for b in f} | set(f)) >= 6 and (f[0] ^ f[1]) != f[2]]

def support(lab_z):
    # lab_z[z] 3-bit; per nonzero combo c: support of (-1)^{c.lab}
    sup = {}
    for c in range(1, 8):
        v = np.array([(-1) ** bin(c & lab_z[z]).count('1') for z in range(64)])
        sup[c] = int(np.count_nonzero(H @ v))
    return min(sup[a] + sup[b] + sup[c] for a, b, c in FRAMES)

def apply_perm(gates):
    """gates: list of (c1, c2, t, n1, n2) Toffolis on 6 wires; returns z(x)."""
    out = []
    for x in range(64):
        z = x
        for c1, c2, t, n1, n2 in gates:
            if (((z >> c1) & 1) ^ n1) & (((z >> c2) & 1) ^ n2):
                z ^= 1 << t
        out.append(z)
    return out

def evaluate(side, gates):
    z = apply_perm(gates)
    inv = [0] * 64
    for x, zz in enumerate(z): inv[zz] = x
    # parity bit must be linear in z: p(inv[z]) linear
    p = [bin(inv[zz] & PMASK[side]).count('1') & 1 for zz in range(64)]
    pv = np.array([(-1) ** b for b in p]); ph = H @ pv
    if np.count_nonzero(ph) != 1:
        return None
    lab_z = [LAB[side][inv[zz]] for zz in range(64)]
    return support(lab_z)

if __name__ == '__main__':
    for side in 'xy':
        base = evaluate(side, [])
        best = (base, [])
        singles = [(c1, c2, t, n1, n2) for c1 in range(6) for c2 in range(c1 + 1, 6) for t in range(6) if t not in (c1, c2) for n1 in (0, 1) for n2 in (0, 1)]
        res = []
        for g in singles:
            s = evaluate(side, [g])
            if s is not None: res.append((s, [g]))
        res.sort()
        print(side, 'base', base, 'best single toffoli', res[:3], flush=True)
        # pairs of disjoint toffolis (one batch) from the top 40 singles + all combos with them
        top = [r[1][0] for r in res[:40]]
        pairs = []
        for g1 in top:
            for g2 in singles:
                if len({g1[0], g1[1], g1[2]} & {g2[0], g2[1], g2[2]}) == 0:
                    s = evaluate(side, [g1, g2])
                    if s is not None: pairs.append((s, [g1, g2]))
        pairs.sort()
        print(side, 'best disjoint pair', pairs[:3], flush=True)
