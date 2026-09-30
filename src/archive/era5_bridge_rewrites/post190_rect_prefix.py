"""Rectangle phases from disjoint prefix cubes instead of dyadic cube covers.

[v >= k] decomposes into disjoint cubes "prefix equals k above bit i, bit i is
1" for each zero bit i of k; the complement [v < k] likewise has one cube per
one bit.  Taking the cheaper of the two makes each of the eight bounds cost one
to three multi-controlled gates, and the rectangle is then a single four-control
phase on the two pairs of bound bits.
"""
import json
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native
from qiskit.synthesis import synth_mcx_2_clean_kg24
from post190_y_fold import mcx as rel
from post190_radius_interval import positive_phase

X = list(range(6))
Y = list(range(6, 12))


def bound_cubes(k, wires):
    """Cubes for [v >= k]; returns (cubes, complemented).

    [v < k] is the disjoint union over one bits i of k of "v agrees with k above
    bit i and v_i = 0"; [v >= k] = [v > k-1] is the same over zero bits of k-1.
    Whichever list is shorter is used, the first one negating the target.
    """
    n = len(wires); assert 0 < k <= 1 << n
    lt = [[(wires[j], (k >> j) & 1) for j in range(n - 1, i, -1)] + [(wires[i], 0)]
          for i in range(n) if (k >> i) & 1]
    m = k - 1
    gt = [[(wires[j], (m >> j) & 1) for j in range(n - 1, i, -1)] + [(wires[i], 1)]
          for i in range(n) if not (m >> i) & 1]
    return (gt, False) if len(gt) <= len(lt) else (lt, True)


def mcx_any(q, controls, target, helpers):
    controls = list(controls)
    if len(controls) == 1: q.cx(controls[0], target)
    elif len(controls) == 2: q.rccx(controls[0], controls[1], target)
    elif len(controls) <= 4: rel(q, controls, target, helpers)
    else:
        q.compose(synth_mcx_2_clean_kg24(len(controls)),
                  controls + [target] + list(helpers), inplace=True)


def emit(q, cubes, complemented, target, helpers):
    for lits in cubes:
        neg = [w for w, b in lits if not b]
        if neg: q.x(neg)
        mcx_any(q, [w for w, _ in lits], target, helpers)
        if neg: q.x(neg)
    if complemented: q.x(target)


def box(q, xlo, xhi, ylo, yhi, wires=(12, 14, 13, 16), helpers=(15, 17)):
    """Phase (-1)^[xlo<=x<=xhi and ylo<=y<=yhi]; all four wires end clean."""
    a, b, c, d = wires
    pre = QuantumCircuit(18)
    emit(pre, *bound_cubes(xlo, X), a, helpers)
    emit(pre, *bound_cubes(xhi + 1, X), b, helpers)
    emit(pre, *bound_cubes(ylo, Y), c, helpers)
    emit(pre, *bound_cubes(yhi + 1, Y), d, helpers)
    q.compose(pre, inplace=True)
    q.x([b, d])
    q.compose(positive_phase(4), [a, b, c, d] + list(helpers), inplace=True)
    q.x([b, d])
    q.compose(pre.inverse(), inplace=True)


def rectangles():
    q = QuantumCircuit(18)
    box(q, 2, 26, 29, 53)
    box(q, 27, 48, 39, 43)
    return native(q)


def simulate_phase(q, state):
    from post190_interval_ripple import simulate
    return simulate(q, state)


def check():
    """Every bound's cube list is disjoint and exactly covers its half-line."""
    bad = 0
    for k in range(1, 65):
        cubes, comp = bound_cubes(k, X)
        for v in range(64):
            hit = sum(all((v >> (w % 6) & 1) == b for w, b in lits) for lits in cubes)
            if hit > 1: bad += 1
            if (hit ^ comp) != int(v >= k): bad += 1
    return bad


def run(out):
    assert not out.exists(); out.mkdir(parents=True)
    assert check() == 0
    from post190_interval_ripple import interval_phase
    from post190_radius_interval import make_lookup
    lookup, values, lr = make_lookup()
    e = QuantumCircuit(18)
    for i in range(5): e.cx(11, i)
    e.x(3); e.cx(3, 4)
    for i in range(4): e.cx(4, i)
    e.compose(lookup, [0, 1, 2, 3, 4, 11, 12, 13, 14], inplace=True); e = native(e)
    rect = rectangles(); k = interval_phase()
    disk = native(e.compose(k).compose(e.inverse()))
    full = native(rect.compose(disk))
    for name, c in [('rectangles', rect), ('oracle', full)]:
        (out / (name + '.qasm')).write_text(qasm2.dumps(c))
    from exhaustive_verify import exhaustive
    exhaustive(out / 'oracle.qasm')
    r = dict(lookup=lr, encoder_depth=e.depth(), interval_depth=k.depth(),
             rectangle_depth=rect.depth(), rectangle_cx=rect.count_ops().get('cx', 0),
             disk_depth=disk.depth(), depth=full.depth(),
             cx=full.count_ops().get('cx', 0), width=18)
    (out / 'report.json').write_text(json.dumps(r, indent=2)); print(r, flush=True)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--outdir', required=True, type=Path)
    run(p.parse_args().outdir)
