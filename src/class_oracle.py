"""Prototype row-class phase oracles.

This module explores the 11 distinct row patterns of the logo.  It deliberately
does not overwrite any existing artifact; callers should choose a new output
name and run exhaustive_verify.py on the serialized QASM.
"""

import json
import random
from pathlib import Path

from pyeda.inter import exprvars, espresso_tts, truthtable
from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from mcz import phase_cube
from search import esop, logo, truth


def row_classes():
    """Return (class_rows, x_masks), grouped by identical marked x rows."""
    groups = {}
    for y in range(64):
        xs = tuple(x for x in range(64) if logo(x, y))
        groups.setdefault(xs, []).append(y)
    return list(groups.values()), [truth(xs) for xs in groups]


def column_classes():
    """Return (class_columns, y_masks), grouped by identical marked y columns."""
    groups = {}
    for x in range(64):
        ys = tuple(y for y in range(64) if logo(x, y))
        groups.setdefault(ys, []).append(x)
    return list(groups.values()), [truth(ys) for ys in groups]


def codebook_binary():
    """Simple 4-bit baseline: class order encoded as integers 0..10."""
    return {i: i for i in range(11)}


def codebook_family4():
    """4-bit structured code: family bit plus nonzero 3-bit level."""
    return {0: 0, **{i: i for i in range(1, 6)},
            **{i + 5: 8 + i for i in range(1, 6)}}


def codebook_thermometer(level_codes=(0, 1, 2, 3, 4)):
    """5-bit baseline: active bit, family bit, and a 3-bit level code.

    Class 0 is blank.  Classes 1..5 are the upper/disk family and classes 6..10
    are the lower/square family.  The level bits use a compact 3-bit index.
    """
    # Bit 3 is an active marker; bit 4 selects A/B.  Blank is all-zero.
    out = {0: 0}
    # Keep the level code within the three dedicated level bits.  The active
    # bit keeps level code 0 distinct from the blank class.
    for family, start in ((0, 1), (1, 6)):
        for level in range(5):
            bits = (1 << 3) | (family << 4)
            bits |= level_codes[level]
            out[start + level] = bits
    return out


def class_tables(classes, codes, nbits):
    """Build one truth-table bit per encoded class feature, indexed by y."""
    tables = []
    for bit in range(nbits):
        tables.append(truth(y for i, ys in enumerate(classes)
                            for y in ys if (codes[i] >> bit) & 1))
    return tables


def class_phase(q, x_masks, classes, codes, nbits, feature_offset):
    """Apply the exact class-conditioned x masks as an ESOP of phase cubes."""
    for i, xmask in enumerate(x_masks):
        # Each class is selected by one cube on the feature bits.  Each x-mask
        # is expanded by ESOP; phase is XOR-linear over these cubes.
        for mask, value in esop(xmask, 6):
            cube = []
            for bit in range(6):
                if mask >> bit & 1:
                    cube.append(bit + 1 if value >> bit & 1 else -(bit + 1))
            for bit in range(nbits):
                cube.append(feature_offset + bit + 1
                            if codes[i] >> bit & 1
                            else -(feature_offset + bit + 1))
            phase_cube(q, frozenset(cube), [])


def nested_phase(q, x_masks, feature_offset, coordinate_offset=0,
                 level_codes=(0, 1, 2, 3, 4)):
    """Mark nested family shells using level-threshold predicates.

    The first five nonblank classes are family A and the next five are family
    B.  Instead of one full x-mask per class, use the XOR shell added at each
    level and control it by ``level >= k``.  The 5-bit baseline uses bits
    feature_offset:feature_offset+3 for the binary level and the last feature
    bit for family (0=A, 1=B).
    """
    level_bits = list(range(feature_offset, feature_offset + 3))
    active_bit = feature_offset + 3
    family_bit = feature_offset + 4
    for family, start, family_literal in ((0, 1, -family_bit - 1),
                                          (1, 6, family_bit + 1)):
        previous = 0
        for level in range(5):
            shell = x_masks[start + level] ^ previous
            previous = x_masks[start + level]
            level_truth = truth(level_codes[j] for j in range(5)
                                if j >= level)
            for xterm_mask, xterm_value in esop(shell, 6):
                xcube = [coordinate_offset + bit + 1
                          if xterm_value >> bit & 1
                          else -(coordinate_offset + bit + 1)
                         for bit in range(6) if xterm_mask >> bit & 1]
                for lmask, lvalue in esop(level_truth, 3):
                    cube = list(xcube) + [active_bit + 1, family_literal]
                    cube += [level_bits[bit] + 1
                             if lvalue >> bit & 1 else -(level_bits[bit] + 1)
                             for bit in range(3) if lmask >> bit & 1]
                    phase_cube(q, frozenset(cube), [])


def nested_phase4(q, x_masks, feature_offset, coordinate_offset=0):
    """Four-bit family/level decoder; zero level is the blank class."""
    level_bits = list(range(feature_offset, feature_offset + 3))
    family_bit = feature_offset + 3
    level_codes = (1, 2, 3, 4, 5)
    for start, family_literal in ((1, -(family_bit + 1)),
                                  (6, family_bit + 1)):
        previous = 0
        for level in range(5):
            shell = x_masks[start + level] ^ previous
            previous = x_masks[start + level]
            if level == 0:
                allowed = level_codes
            else:
                allowed = level_codes[level:]
            level_truth = truth(code for code in allowed)
            for xterm_mask, xterm_value in esop(shell, 6):
                xcube = [coordinate_offset + bit + 1
                          if xterm_value >> bit & 1
                          else -(coordinate_offset + bit + 1)
                         for bit in range(6) if xterm_mask >> bit & 1]
                for lmask, lvalue in esop(level_truth, 3):
                    cube = list(xcube) + [family_literal]
                    cube += [level_bits[bit] + 1
                             if lvalue >> bit & 1 else -(level_bits[bit] + 1)
                             for bit in range(3) if lmask >> bit & 1]
                    phase_cube(q, frozenset(cube), [])


def build_nested4(seed=0):
    classes, x_masks = row_classes()
    codes = codebook_family4()
    q = QuantumCircuit(18)
    lookup = multiplexer(class_tables(classes, codes, 4),
                         list(range(12, 16)), list(range(6, 12)),
                         'y', seed)
    q.compose(lookup, inplace=True)
    nested_phase4(q, x_masks, 12)
    q.compose(lookup.inverse(), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'],
                     qubits_initially_zero=False, optimization_level=3)


def espresso_phase(q, x_masks, codes, nbits, feature_offset):
    """Apply an Espresso don't-care cover plus exact reachable residual.

    Espresso minimizes the OR relation with unreachable feature codes as
    don't-cares.  Since phase accumulation is XOR rather than OR, the parity
    difference on the 11 reachable codes is computed and corrected explicitly.
    """
    classes = len(x_masks)
    inverse = {code: i for i, code in codes.items()}
    n = 6 + nbits
    values = []
    for z in range(1 << n):
        x = z & 63
        code = (z >> 6) & ((1 << nbits) - 1)
        i = inverse.get(code)
        values.append('-' if i is None else
                      ('1' if i and (x_masks[i] >> x & 1) else '0'))
    expr = espresso_tts(
        truthtable(exprvars('z', n), ''.join(values))
    )[0]

    cover = []
    for cube in expr.cover:
        logical = [lit.node.data() for lit in cube]
        cover.append(logical)
        physical = []
        for lit in logical:
            v = abs(lit) - 1
            wire = v if v < 6 else feature_offset + v - 6
            physical.append(wire + 1 if lit > 0 else -(wire + 1))
        phase_cube(q, frozenset(physical), [])

    # Correct Espresso's OR cover to the required XOR phase on reachable
    # feature codes.  The residual is represented per class, where its x
    # function is small and exact under the existing ESOP routine.
    for code, i in inverse.items():
        residual = 0
        for x in range(64):
            z = x | (code << 6)
            parity = 0
            for cube in cover:
                if all(((z >> (abs(lit) - 1)) & 1) == (1 if lit > 0 else 0)
                       for lit in cube):
                    parity ^= 1
            target = 1 if i and (x_masks[i] >> x & 1) else 0
            if parity != target:
                residual |= 1 << x
        for mask, value in esop(residual, 6):
            cube = [bit + 1 if value >> bit & 1 else -(bit + 1)
                    for bit in range(6) if mask >> bit & 1]
            cube += [feature_offset + bit + 1
                     if code >> bit & 1 else -(feature_offset + bit + 1)
                     for bit in range(nbits)]
            phase_cube(q, frozenset(cube), [])


def build_espresso(codebook, nbits, seed=0):
    """Build a class oracle using an Espresso don't-care central decoder."""
    classes, x_masks = row_classes()
    q = QuantumCircuit(18)
    lookup = multiplexer(
        class_tables(classes, codebook, nbits),
        list(range(12, 12 + nbits)),
        list(range(6, 12)),
        'y',
        seed,
    )
    q.compose(lookup, inplace=True)
    espresso_phase(q, x_masks, codebook, nbits, 12)
    q.compose(lookup.inverse(), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'],
                     qubits_initially_zero=False, optimization_level=3)


def build(codebook, nbits, seed=0):
    classes, x_masks = row_classes()
    assert len(classes) == 11
    assert set(codebook) == set(range(11))
    assert len(set(codebook.values())) == 11

    feature_offset = 12
    q = QuantumCircuit(18)
    tables = class_tables(classes, codebook, nbits)
    lookup = multiplexer(
        tables,
        list(range(feature_offset, feature_offset + nbits)),
        list(range(6, 12)),
        'y',
        seed,
    )
    q.compose(lookup, inplace=True)
    class_phase(q, x_masks, classes, codebook, nbits, feature_offset)
    q.compose(lookup.inverse(), inplace=True)
    return transpile(
        q,
        basis_gates=['u3', 'cx'],
        qubits_initially_zero=False,
        optimization_level=3,
    )


def build_nested(seed=0, level_codes=(0, 1, 2, 3, 4)):
    """Build the 5-bit family/level prototype with shared shell phases."""
    classes, x_masks = row_classes()
    q = QuantumCircuit(18)
    codebook = codebook_thermometer(level_codes)
    lookup = multiplexer(
        class_tables(classes, codebook, 5),
        list(range(12, 17)),
        list(range(6, 12)),
        'y',
        seed,
    )
    q.compose(lookup, inplace=True)
    nested_phase(q, x_masks, 12, level_codes=level_codes)
    q.compose(lookup.inverse(), inplace=True)
    return transpile(
        q,
        basis_gates=['u3', 'cx'],
        qubits_initially_zero=False,
        optimization_level=3,
    )


def build_nested_transposed(seed=0):
    """Same shell decoder with column classes loaded from x and phased on y."""
    classes, y_masks = column_classes()
    q = QuantumCircuit(18)
    codebook = codebook_thermometer()
    lookup = multiplexer(
        class_tables(classes, codebook, 5),
        list(range(12, 17)),
        list(range(0, 6)),
        'y',
        seed,
    )
    q.compose(lookup, inplace=True)
    nested_phase(q, y_masks, 12, coordinate_offset=6)
    q.compose(lookup.inverse(), inplace=True)
    return transpile(
        q,
        basis_gates=['u3', 'cx'],
        qubits_initially_zero=False,
        optimization_level=3,
    )


def emit(name, codebook, nbits, seed=0):
    q = build(codebook, nbits, seed)
    Path(f'artifacts/{name}.qasm').write_text(qasm2.dumps(q))
    Path(f'artifacts/{name}.json').write_text(json.dumps({
        'codebook': codebook,
        'nbits': nbits,
        'seed': seed,
        'depth': q.depth(),
        'cx_count': q.count_ops().get('cx', 0),
    }, indent=2))
    print(name, 'depth', q.depth(), 'cx', q.count_ops().get('cx', 0), flush=True)


if __name__ == '__main__':
    emit('class_binary4_proto', codebook_binary(), 4, seed=0)
    emit('class_thermometer5_proto', codebook_thermometer(), 5, seed=0)
    nested = build_nested(0)
    Path('artifacts/class_nested5_proto.qasm').write_text(qasm2.dumps(nested))
    Path('artifacts/class_nested5_proto.json').write_text(json.dumps({
        'encoding': '5-bit family plus binary level',
        'seed': 0,
        'depth': nested.depth(),
        'cx_count': nested.count_ops().get('cx', 0),
    }, indent=2))
    print('class_nested5_proto', 'depth', nested.depth(),
          'cx', nested.count_ops().get('cx', 0), flush=True)
