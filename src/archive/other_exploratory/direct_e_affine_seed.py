"""Reproduce the ten-step global affine ANF screen, retaining its witness."""
import argparse
import json
from pathlib import Path
import numpy as np
from direct_e_v2 import TARGET


def anf_count(values):
    a = values.copy()
    for bit in range(12):
        blocks = a.reshape(-1, 2 * (1 << bit))
        blocks[:, 1 << bit:] ^= blocks[:, :1 << bit]
    return int(a.sum())


def screen():
    points = np.arange(4096, dtype=np.int32)
    values = np.unpackbits(np.frombuffer(TARGET.to_bytes(512, 'little'), dtype=np.uint8), bitorder='little')
    ops = [('cx', a, b) for a in range(12) for b in range(12) if a != b] + [('x', a) for a in range(12)]
    permutations = [points ^ (((points >> op[1]) & 1) << op[2]) if op[0] == 'cx' else points ^ (1 << op[1]) for op in ops]
    current, mapping = values.copy(), points.copy()
    history, counts = [], []
    for _ in range(10):
        scores = [anf_count(current[p]) for p in permutations]
        chosen = int(np.argmin(scores))
        current = current[permutations[chosen]]
        mapping = mapping[permutations[chosen]]
        history.append(ops[chosen])
        counts.append(scores[chosen])
    assert np.array_equal(current, values[mapping])
    # Verify the physical encoder inverse and substitution orientation.
    encoded = points.copy()
    for op in history:
        encoded ^= (((encoded >> op[1]) & 1) << op[2]) if op[0] == 'cx' else (1 << op[1])
    assert np.array_equal(mapping[encoded], points)
    assert np.array_equal(current[encoded], values)
    return dict(identity_terms=anf_count(values), terms=anf_count(current), counts=counts,
                substitution_ops=history, mapping_old_input_for_new_coordinate=mapping.tolist(),
                convention='g(z)=f(T1(T2(...Tk(z)))); physical encoder applies T1 then T2 through Tk',
                warning='ANF proxy only; not a complete oracle or native depth estimate')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists()
    record = screen()
    a.out.write_text(json.dumps(record, indent=2) + '\n')
    print({k: v for k, v in record.items() if k != 'mapping_old_input_for_new_coordinate'})
