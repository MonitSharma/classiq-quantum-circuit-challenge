"""Lower bound on total oracle depth T from a loader ready-vector.

Wire i is usable in [ready_i, T - ready_i].  A kernel term can only be executed once
every wire in its coordinate support has arrived.  For every cut time tau:
      sum_i max(0, (T - ready_i) - max(tau, ready_i))  >=  3 * #{terms with a_t >= tau}
(each remaining term costs one CX = 2 slots plus one rotation slot).
"""
import sys, itertools
sys.path.insert(0, '/work/cq/src/post151_sa')
from kdrv import KTERMS

def coords(vecs):
    """vecs: 4 combinations (1..15) of the side's code directions, as held by the wires.
    returns, for each side-part s in 0..15, the set of wire indices needed."""
    out = {}
    for s in range(16):
        for b in range(16):
            v = 0
            for w in range(4):
                if b >> w & 1: v ^= vecs[w]
            if v == s: out[s] = b; break
    return out

def avail_times(yv, xv, yr, xr):
    cy = coords(yv); cx = coords(xv)
    ts = []
    for m in KTERMS:
        yb = cy[m & 15]; xb = cx[(m >> 4) & 15]
        t = 0
        for w in range(4):
            if yb >> w & 1: t = max(t, yr[w])
            if xb >> w & 1: t = max(t, xr[w])
        ts.append(t)
    return ts

def min_T(yv, xv, yr, xr, kcx=None, slots_per_term=3.0, lo=90, hi=140):
    ts = avail_times(yv, xv, yr, xr)
    rdy = list(yr) + list(xr)
    for T in range(lo, hi):
        ok = True
        # global
        avail = sum(max(0, T - 2 * r) for r in rdy)
        need = (2 * kcx + len(KTERMS)) if kcx else slots_per_term * len(KTERMS)
        if avail < need: ok = False
        if ok:
            for tau in sorted(set(ts)):
                rem = sum(1 for t in ts if t >= tau)
                cap = sum(max(0, (T - r) - max(tau, r)) for r in rdy)
                if cap < slots_per_term * rem: ok = False; break
        if ok: return T, ts
    return None, ts
