"""Exhaustive affine relabelling of the loaded code bits.

The kernel only needs the code to determine the class, so the three loaded bits
may be replaced by any invertible affine image of themselves -- optionally with
the raw parity mixed in, since the kernel reads that wire too.  That changes the
loaded angle tables (and so the loader's Walsh terms and frame balance) and
relabels the kernel truth table (and so its parity-term count), while leaving the
class partition, the cells and the reachable set untouched.

There are only 168 * 8 * 8 = 10,752 such maps, so unlike the annealed label
searches this one is exhaustive over its group.
"""
import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

from post196_frame_balance import kernel_terms, loader_floor
from post258_two_stage_anf import decode
from two_stage_oracle import ROWCLS, COLCLS


def invertible_maps():
    """All invertible 3x3 GF(2) matrices, as triples of output row masks."""
    out = []
    for rows in itertools.product(range(8), repeat=3):
        piv = {}
        ok = True
        for row in rows:
            value = row
            while value:
                top = value.bit_length() - 1
                if top in piv:
                    value ^= piv[top]
                else:
                    piv[top] = value
                    break
            else:
                ok = False
                break
        if ok:
            out.append(rows)
    assert len(out) == 168
    return out


MAPS = invertible_maps()


def apply_map(code_bits, raw, rows, shift, rawmix):
    """New loaded bit j = parity(rows[j] & code) ^ shift_j ^ (rawmix_j & raw)."""
    out = 0
    for j in range(3):
        bit = (rows[j] & code_bits).bit_count() & 1
        bit ^= (shift >> j) & 1
        if (rawmix >> j) & 1:
            bit ^= raw
        out |= bit << j
    return out


def side_variants(cls, rho, labels):
    base_raw = [((v & rho).bit_count() & 1) for v in range(64)]
    base_code = [labels[(base_raw[v], cls[v])] for v in range(64)]
    seen = {}
    for rows in MAPS:
        for shift in range(8):
            for rawmix in range(8):
                loaded = [apply_map(base_code[v], base_raw[v], rows, shift, rawmix)
                          for v in range(64)]
                tables = np.array([[math.pi * ((loaded[v] >> b) & 1) for v in range(64)]
                                   for b in range(3)])
                floor, _ = loader_floor(tables)
                full = [base_raw[v] | (loaded[v] << 1) for v in range(64)]
                key = (floor, tuple(full))
                if key not in seen:
                    seen[key] = (floor, full)
    return sorted(seen.values(), key=lambda z: z[0])


def run(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    record = json.loads(Path('artifacts/218/class_codes.json').read_text())
    ylab = decode(record['ylab'])
    xlab = decode(record['xlab'])
    yv = side_variants(ROWCLS, 32, ylab)
    xv = side_variants(COLCLS, 48, xlab)
    print('y variants', len(yv), 'best loader floor', yv[0][0],
          '| x variants', len(xv), 'best loader floor', xv[0][0], flush=True)
    rows = []
    for fy, ycode in yv[:80]:
        for fx, xcode in xv[:80]:
            tk = kernel_terms(ycode, xcode)
            if tk is None:
                continue
            rows.append(dict(loader_floor=max(fy, fx), y_floor=fy, x_floor=fx,
                             kernel_terms=tk,
                             predicted=round(2 * max(fy, fx) + 0.48 * tk, 1),
                             ycode=ycode, xcode=xcode))
    rows.sort(key=lambda r: r['predicted'])
    (outdir / 'affine.json').write_text(json.dumps(rows[:30], indent=1) + '\n')
    for r in rows[:8]:
        print({k: r[k] for k in ('loader_floor', 'kernel_terms', 'predicted')}, flush=True)
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    run(p.parse_args().outdir)
