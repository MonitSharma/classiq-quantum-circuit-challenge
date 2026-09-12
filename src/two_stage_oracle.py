"""Two-stage distributed oracle: one loader block per direction instead of three.

The 258 build loads a three-bit level code, applies a kernel, re-loads a second
three-bit code, applies a second kernel, then unloads.  Three loader blocks at
78 layers each is 234 before the kernels, which is already above any sub-180
target, and the block depth is set by CX contention rather than by the number of
rotations, so sparser codes do not help.

Instead give each side a FOUR-bit class code: one raw coordinate wire plus three
loaded bits.  Four bits distinguish all eleven row (and column) classes, so a
single load serves both passes and the middle block disappears.  The price is a
single eight-variable kernel, which is emitted as a distributed phase polynomial
over the eight code wires.
"""
import math
import numpy as np
from qiskit import QuantumCircuit

import distributed_ucry as dist

XW = list(range(6))
YW = list(range(6, 12))
YA = [12, 13, 14]
XA = [15, 16, 17]
YRAW, XRAW = 5, 4              # raw coordinate bit used as the fourth code bit
YRAW_WIRE = YW[YRAW]
XRAW_WIRE = XW[XRAW]
KERNEL_WIRES = [YRAW_WIRE] + YA + [XRAW_WIRE] + XA


def logo(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53) or (26 <= x <= 49 and 39 <= y <= 43)
            or (x - 55) ** 2 + (y - 41) ** 2 <= 42
            or (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def classes():
    rows, rowcls = {}, [0] * 64
    for y in range(64):
        rowcls[y] = rows.setdefault(tuple(1 if logo(x, y) else 0 for x in range(64)), len(rows))
    cols, colcls = {}, [0] * 64
    for x in range(64):
        colcls[x] = cols.setdefault(tuple(1 if logo(x, y) else 0 for y in range(64)), len(cols))
    return rowcls, colcls


ROWCLS, COLCLS = classes()


def cells(cls, raw):
    out = {}
    for t in range(64):
        out.setdefault(((t >> raw) & 1, cls[t]), []).append(t)
    return out


YCELL, XCELL = cells(ROWCLS, YRAW), cells(COLCLS, XRAW)


def code_tables(ylab, xlab):
    """Per-coordinate three-bit loaded code, as angle tables for the loader."""
    ycode = [0] * 64
    for key, members in YCELL.items():
        for y in members:
            ycode[y] = ylab[key]
    xcode = [0] * 64
    for key, members in XCELL.items():
        for x in members:
            xcode[x] = xlab[key]
    ytab = np.array([[math.pi * ((ycode[y] >> j) & 1) for y in range(64)] for j in range(3)])
    xtab = np.array([[math.pi * ((xcode[x] >> j) & 1) for x in range(64)] for j in range(3)])
    return ycode, xcode, ytab, xtab


def kernel_table(ylab, xlab, fill=0):
    """Eight-bit truth table of the kernel; unreachable code pairs take `fill`."""
    table = [fill] * 256
    for ykey, ymembers in YCELL.items():
        yv = ykey[0] | (ylab[ykey] << 1)
        for xkey, xmembers in XCELL.items():
            xv = xkey[0] | (xlab[xkey] << 1)
            table[yv | (xv << 4)] = 1 if logo(xmembers[0], ymembers[0]) else 0
    return table


def walsh8(table):
    a = np.array(table, dtype=float)
    h = 1
    while h < 256:
        for i in range(0, 256, 2 * h):
            lo = a[i:i + h].copy()
            hi = a[i + h:i + 2 * h].copy()
            a[i:i + h] = lo + hi
            a[i + h:i + 2 * h] = lo - hi
        h *= 2
    return a / 256


def emit_kernel(table, wires):
    """Distributed phase polynomial for the diagonal exp(i pi * table).

    Each nonzero Walsh mask is hosted on one of its own wires; the host walks to
    the mask with CX gates, takes its Rz, and carries on.  Masks are grouped by
    host and ordered greedily so consecutive masks in a group are close.
    """
    coeff = walsh8([math.pi * v for v in table])
    masks = [m for m in range(1, 256) if abs(coeff[m]) > 1e-12]
    groups = {j: [] for j in range(8)}
    for m in sorted(masks, key=lambda z: (bin(z).count('1'), z)):
        host = min((j for j in range(8) if m >> j & 1),
                   key=lambda j: len(groups[j]))
        groups[host].append(m)
    qc = QuantumCircuit(max(wires) + 1)
    for host, items in groups.items():
        if not items:
            continue
        order, rest, cur = [], list(items), 1 << host
        while rest:
            nxt = min(rest, key=lambda m: bin(m ^ cur).count('1'))
            order.append(nxt)
            rest.remove(nxt)
            cur = nxt
        cur = 1 << host
        for m in order:
            for bit in range(8):
                if (cur ^ m) >> bit & 1 and bit != host:
                    qc.cx(wires[bit], wires[host])
            cur = m
            qc.rz(-2 * float(coeff[m]), wires[host])
        for bit in range(8):
            if (cur ^ (1 << host)) >> bit & 1 and bit != host:
                qc.cx(wires[bit], wires[host])
    return qc, len(masks)


def build(ylab, xlab, seeds=(0, 1, 2, 3), fill=0):
    _, _, ytab, xtab = code_tables(ylab, xlab)
    qc = QuantumCircuit(18)
    stages = []
    for sign, label in ((1.0, 'load'), (-1.0, 'unload')):
        for angles, wires in ((sign * ytab, YW + YA), (sign * xtab, XW + XA)):
            best = None
            for seed in seeds:
                for open_walk in (True, False):
                    raw = dist.structured_ucry(angles, [6, 7, 8], list(range(6)),
                                               seed, open_walk=open_walk)
                    from qiskit import transpile
                    comp = transpile(raw, basis_gates=['u3', 'cx'],
                                     qubits_initially_zero=False,
                                     optimization_level=3, seed_transpiler=0)
                    score = (comp.depth(), comp.count_ops().get('cx', 0))
                    if best is None or score < best[0]:
                        best = (score, comp, seed, open_walk)
            stages.append((label, best[0]))
            qc.compose(best[1], wires, inplace=True)
        if label == 'load':
            kern, nmask = emit_kernel(kernel_table(ylab, xlab, fill), KERNEL_WIRES)
            qc.compose(kern, inplace=True)
            stages.append(('kernel', (nmask,)))
    return qc, stages
