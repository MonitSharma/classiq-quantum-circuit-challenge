"""Focused checks for the post-185 architecture-floor tooling."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
from qiskit import transpile

import post185_balanced_loader as bl
import post185_loader_aware_codes as lac
import post185_schedule_floor as floor
import two_stage_oracle as ts
from distributed_ucry import verify_component
from post258_raw_parity_codes import cells
from post258_two_stage_anf import decode

RECORD = Path('artifacts/185/class_codes.json')


def protected_codes():
    rec = json.loads(RECORD.read_text())
    out = {}
    for side, lab_key, cls, mask_key in (('y', 'ylab', ts.ROWCLS, 'ymask'),
                                         ('x', 'xlab', ts.COLCLS, 'xmask')):
        lab = decode(rec[lab_key])
        mask = rec[mask_key]
        out[side] = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
    return rec, out


def test_walk_table_is_a_closed_walk():
    for bits in (0b00000001, 0b10101010, 0b11111111, 0b00010110):
        cost, order = bl.WALK[bits]
        assert set(order) == {m for m in range(8) if bits >> m & 1}
        total = cur = 0
        for m in order:
            total += (cur ^ m).bit_count()
            cur = m
        assert total + cur.bit_count() == cost


def test_shift_walk_covers_every_host_group():
    for init in ((0, 0, 0), (3, 5, 6), (7, 1, 2)):
        for direction in (0, 1):
            seen = set()
            for stage in bl.shift_walk(init, direction):
                seen.update(bl.stage_groups(stage))
            assert len(seen) == 24


def test_balanced_loader_reproduces_the_protected_y_code():
    _, codes = protected_codes()
    key, circuit, cfg = bl.best(codes['y'], configs=1, seeds=3)
    tab = np.array([[math.pi * ((codes['y'][y] >> j) & 1) for y in range(64)]
                    for j in range(3)])
    assert verify_component(circuit, tab) < 1e-10
    assert key[0] > 0


def test_loader_cost_ranks_the_protected_code_near_its_measured_depth():
    _, codes = protected_codes()
    # the protected encoder compiles to 78 layers; the estimate must be close
    assert 70 <= lac.loader_cost(codes['y']) <= 86


def test_schedule_floor_matches_the_protected_record():
    rec, _ = protected_codes()
    labs = [decode(rec['ylab']), decode(rec['xlab'])]
    value, parts, _ = floor.floor_of(labs, rec['ymask'], rec['xmask'],
                                     cells(ts.ROWCLS, rec['ymask']),
                                     cells(ts.COLCLS, rec['xmask']))
    assert parts[:2] == (174, 175)
    assert parts[2] == 90
    # the built oracle is 185 layers, just above this bound
    assert 170 <= value <= 180


def test_raw_width_probe_prefers_the_protected_split():
    import post185_raw_width_probe as rw
    narrow = rw.probe([32], [48], 3, tries=200)
    wide = rw.probe([8, 20, 32], [1, 16, 44], 2, tries=200)
    assert wide['loader_depth'] < narrow['loader_depth']
    assert wide['kernel_masks'] > 4 * narrow['kernel_masks']
    assert wide['total'] > narrow['total']
