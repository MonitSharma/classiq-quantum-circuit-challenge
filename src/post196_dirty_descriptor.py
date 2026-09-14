"""Fibre alignment as a lookup output on the dirty coordinate wire.

The closure in `FOLD_THEN_LOOKUP.md` assumed the two raw fibres must be aligned
*before* the lookup, so it needed one common code partition and stalled at 11-12
blocks against the 8 that three loaded bits allow.  That assumption is droppable.

Split the coordinate as `z = (A, R)`, address `A` and residual `R`, and let the
same lookup that produces the clean code bits also write `R -> R xor h(A)` in
place on the coordinate wires.  The descriptor becomes

    D(z) = ( R xor h(A),  c(A) )

so the alignment is address-dependent and is produced by the lookup rather than
paid for in front of it.

The feasibility test collapses nicely.  Inputs sharing an address always get
distinct descriptors, so only different-address pairs bind, and two addresses can
share a code value exactly when their class patterns over the residual agree
under some translation.  Translations form a group, so "agrees under some
translation" is an equivalence relation, and the whole question is:

    do the class patterns fall into at most (number of code values) classes?

`|AGL(2,2)| = 24 = 4!`, so for a two-bit residual the affine variant realises
*every* permutation of the four residual states, which is the widest possible
per-address re-pairing.
"""
import argparse
import itertools
import json
from pathlib import Path


def patterns(classes, address_bits):
    """Class pattern over the residual, one per address."""
    residual_bits = [i for i in range(6) if i not in address_bits]
    table = {}
    for z in range(64):
        a = sum(((z >> b) & 1) << k for k, b in enumerate(address_bits))
        r = sum(((z >> b) & 1) << k for k, b in enumerate(residual_bits))
        table.setdefault(a, {})[r] = classes[z]
    size = 1 << len(residual_bits)
    return [tuple(table[a][r] for r in range(size)) for a in range(1 << len(address_bits))]


def translation_classes(pats, width):
    """Group patterns that agree under XOR translation of the residual."""
    groups, offsets = [], {}
    for index, p in enumerate(pats):
        placed = False
        for gid, rep in enumerate(groups):
            for delta in range(1 << width):
                if all(p[r] == rep[r ^ delta] for r in range(1 << width)):
                    offsets[index] = (gid, delta)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            offsets[index] = (len(groups), 0)
            groups.append(p)
    return len(groups), offsets


def permutation_classes(pats, width):
    """Group patterns that agree under any invertible affine map of the residual."""
    size = 1 << width
    maps = []
    for perm in itertools.permutations(range(size)):
        # keep only affine ones: perm(r) = M r xor t is affine over GF(2)
        t = perm[0]
        ok = True
        for r in range(size):
            for s in range(size):
                if perm[r ^ s] != perm[r] ^ perm[s] ^ t:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            maps.append(perm)
    groups, offsets = [], {}
    for index, p in enumerate(pats):
        placed = False
        for gid, rep in enumerate(groups):
            for m in maps:
                if all(p[r] == rep[m[r]] for r in range(size)):
                    offsets[index] = (gid, m)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            offsets[index] = (len(groups), tuple(range(size)))
            groups.append(p)
    return len(groups), offsets, len(maps)


def run(outdir):
    from two_stage_oracle import ROWCLS, COLCLS
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, classes in (('y', ROWCLS), ('x', COLCLS)):
        rows = []
        for width, budget in ((4, 4), (5, 8)):
            residual = 6 - width
            for bits in itertools.combinations(range(6), width):
                pats = patterns(classes, bits)
                n, _ = translation_classes(pats, residual)
                entry = dict(address_bits=list(bits), address_width=width,
                             code_values_needed=n, budget=budget,
                             feasible=n <= budget, kind='translation')
                if residual == 2:
                    m, _, nmaps = permutation_classes(pats, residual)
                    entry['affine_code_values_needed'] = m
                    entry['affine_feasible'] = m <= budget
                    entry['affine_maps'] = nmaps
                rows.append(entry)
        rows.sort(key=lambda r: (r['code_values_needed'], r['address_width']))
        report[name] = rows
        for r in rows[:4]:
            print(name, 'address', r['address_bits'], 'width', r['address_width'],
                  'codes needed', r['code_values_needed'], 'budget', r['budget'],
                  'FEASIBLE' if r['feasible'] else '',
                  ('affine ' + str(r.get('affine_code_values_needed'))) if 'affine_code_values_needed' in r else '',
                  flush=True)
    (outdir / 'dirty_descriptor.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    run(p.parse_args().outdir)
