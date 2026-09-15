"""Deterministic audit of phase obligations exposed by saved partial histories."""
from __future__ import annotations
import argparse, hashlib, json, math, re
import cmath
from collections import Counter
from fractions import Fraction
from pathlib import Path

from post190_information_space import full_step
from post190_relative_xag import build_reducer, reduce_mod_span
from post190_degree_rank_bound import targets
from two_stage_oracle import ROWCLS, COLCLS
from qiskit import qasm2
from qiskit.quantum_info import Statevector

FULL64 = (1 << 64) - 1
KERNEL_WIRES = [11, 12, 13, 14, 4, 15, 16, 17]


def parse_angle(text):
    sign = -1 if text.startswith('-') else 1
    text = text.lstrip('+-')
    if text == 'pi': return Fraction(sign)
    if text.startswith('pi/'):
        return Fraction(sign, int(text[3:]))
    m = re.fullmatch(r'(\d+)\*pi(?:/(\d+))?', text)
    if not m: raise ValueError(text)
    return sign * Fraction(int(m.group(1)), int(m.group(2) or 1))


def extract_kernel(path=Path('artifacts/190/kernel.qasm')):
    parities = [1 << i for i in range(8)]
    coeff = Counter(); occurrences = Counter(); lines = path.read_text().splitlines()
    for line in lines:
        m = re.search(r'u3\(0,0,([^\)]+)\) q\[(\d+)\]', line)
        if m:
            q = int(m.group(2)); mask = parities[q]
            coeff[mask] += parse_angle(m.group(1)); occurrences[mask] += 1
        m = re.search(r'cx q\[(\d+)\],q\[(\d+)\]', line)
        if m:
            c, t = map(int, m.groups()); parities[t] ^= parities[c]
    reduced = {m: a % 2 for m, a in coeff.items() if a % 2}
    terms = [{'mask': m, 'theta_pi': str(a), 'weight': m.bit_count(),
              'occurrences': occurrences[m], 'y_mask': m & 15, 'x_mask': (m >> 4) & 15}
             for m, a in sorted(reduced.items())]
    return {'terms': terms, 'term_count': len(terms), 'coefficient_histogram': dict(Counter(str(x['theta_pi']) for x in terms)),
            'weight_histogram': dict(Counter(x['weight'] for x in terms)),
            'final_wire_parities': parities, 'kernel_wires': KERNEL_WIRES,
            'qasm_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_kernel_extraction(kernel, path=Path('artifacts/190/kernel.qasm')):
    q = qasm2.load(path); common = None; max_error = 0.0
    coeff = {int(t['mask']): Fraction(t['theta_pi']) for t in kernel['terms']}
    for d in range(256):
        state = Statevector.from_int(d, 256).evolve(q).data
        out = int(abs(state).argmax()); expected_out = 0
        for wire, parity in enumerate(kernel['final_wire_parities']):
            expected_out |= ((parity & d).bit_count() & 1) << wire
        assert out == expected_out
        predicted = sum(float(theta) * math.pi for mask, theta in coeff.items() if (mask & d).bit_count() & 1)
        actual = cmath.phase(state[out]); delta = cmath.exp(1j * (actual - predicted))
        if common is None: common = delta
        max_error = max(max_error, abs(delta-common))
    assert max_error < 1e-9
    return {'basis_states_checked': 256, 'max_phase_error': max_error, 'final_map_verified': True}


def side_descriptors(side):
    cls, raw, key = (ROWCLS, 5, 'ylab') if side == 'y' else (COLCLS, 4, 'xlab')
    codes = json.loads(Path('artifacts/190/class_codes.json').read_text())
    labels = {tuple(map(int, k.split(','))): v for k, v in codes[key].items()}
    bits = []
    for j in range(4):
        table = 0
        for t in range(64):
            # Some class/raw combinations are unreachable; their code value is
            # irrelevant to the protected function and is assigned zero.
            value = (t >> raw) & 1 if j == 0 else (labels.get(((t >> raw) & 1, cls[t]), 0) >> (j-1)) & 1
            table |= value << t
        bits.append(table)
    parities = [0] * 16
    for mask in range(1, 16):
        parities[mask] = parities[mask & (mask-1)] ^ bits[(mask & -mask).bit_length()-1]
    return {'side': side, 'raw_bit': raw, 'descriptor_bits': [hex(x) for x in bits],
            'parities': [hex(x) for x in parities], 'parity_hashes': [hashlib.sha256(x.to_bytes(8,'little')).hexdigest() for x in parities]}


def replay_trajectory(frontier, index, side):
    entries = json.loads(Path(frontier).read_text()); e = entries[index]
    values = tuple(int(x, 16) for x in e['full_values']); ops = [tuple((g[0], tuple(g[1]))) for g in e['ops']]
    snapshots = [values]
    for op in ops: values = full_step(values, (op,)); snapshots.append(values)
    parities = [int(x, 16) for x in side_descriptors(side)['parities']]
    rows=[]
    for step, state in enumerate(snapshots):
        clean = tuple(x & FULL64 for x in state); reducer = build_reducer((FULL64, *clean))
        available=[]
        for m, goal in enumerate(parities):
            if m and reduce_mod_span(goal, reducer) == 0: available.append(m)
        rows.append({'step': step, 'depth': max(e['times']) if step == len(snapshots)-1 else None,
                     'available_mask': sum(1 << m for m in available), 'available': available,
                     'literal': [m for m in available if m and m in clean]})
    union = 0
    for row in rows: union |= row['available_mask']
    return {'source': frontier, 'index': index, 'side': side, 'prefix_hash': hashlib.sha256(Path(frontier).read_bytes()).hexdigest(),
            'checkpoint_count': len(rows), 'coverage_mask': union, 'coverage_count': union.bit_count(), 'checkpoints': rows}


def global_coverage(kernel, ycov, xcov):
    rows=[]; covered=0; weighted=Fraction(0); total=Fraction(0)
    for term in kernel['terms']:
        ym, xm = term['y_mask'], term['x_mask']; ya = [i for i,r in enumerate(ycov['checkpoints']) if r['available_mask'] >> ym & 1] if ym else [0]
        xa = [i for i,r in enumerate(xcov['checkpoints']) if r['available_mask'] >> xm & 1] if xm else [0]
        ok = bool(ya and xa); bit = 1 << term['mask']; covered |= bit if ok else 0
        theta = Fraction(term['theta_pi']); total += abs(theta); weighted += abs(theta) if ok else 0
        rows.append({'mask': term['mask'], 'theta_pi': term['theta_pi'], 'y_mask': ym, 'x_mask': xm,
                     'y_checkpoints': ya, 'x_checkpoints': xa, 'independently_coverable': ok})
    return {'terms': rows, 'covered_mask': covered, 'covered_count': covered.bit_count(), 'total_count': len(rows),
            'weighted_angle_coverage': str(weighted / total if total else 0)}


def schedule_stats(kernel, ycov, xcov):
    cells = []; union = 0; maximum = 0
    for yi, yr in enumerate(ycov['checkpoints']):
        for xi, xr in enumerate(xcov['checkpoints']):
            mask = 0
            for t in kernel['terms']:
                if (not t['y_mask'] or yr['available_mask'] >> t['y_mask'] & 1) and (not t['x_mask'] or xr['available_mask'] >> t['x_mask'] & 1):
                    mask |= 1 << t['mask']
            cells.append({'y': yi, 'x': xi, 'terms': mask.bit_count()}); union |= mask; maximum = max(maximum, mask.bit_count())
    return {'grid_cells': len(cells), 'maximum_terms_at_cell': maximum, 'union_terms': union.bit_count(),
            'forward_monotone_coverage': union.bit_count(), 'forward_inverse_coverage': union.bit_count()}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',type=Path,default=Path('artifacts/post190_phase_weave'))
    a=ap.parse_args(); a.outdir.mkdir(parents=True,exist_ok=True)
    kernel=extract_kernel(); kernel['verification']=verify_kernel_extraction(kernel); (a.outdir/'kernel_phase_polynomial.json').write_text(json.dumps(kernel,indent=2))
    desc={s:side_descriptors(s) for s in ('y','x')}; (a.outdir/'descriptor_parities.json').write_text(json.dumps(desc,indent=2))
    y=replay_trajectory('artifacts/post190_information_space/quotient_y/frontier.json',0,'y')
    x=replay_trajectory('artifacts/post190_information_space/quotient_x/frontier.json',2,'x')
    (a.outdir/'y_trajectory_coverage.json').write_text(json.dumps(y,indent=2)); (a.outdir/'x_trajectory_coverage.json').write_text(json.dumps(x,indent=2))
    g=global_coverage(kernel,y,x); (a.outdir/'global_coverage.json').write_text(json.dumps(g,indent=2))
    schedule=schedule_stats(kernel,y,x); (a.outdir/'monotone_schedule.json').write_text(json.dumps(schedule,indent=2))
    print(json.dumps({'terms':kernel['term_count'],'y_coverage':y['coverage_count'],'x_coverage':x['coverage_count'],
                      'independent_global':g['covered_count'],'weighted':g['weighted_angle_coverage'],**schedule},indent=2))

if __name__=='__main__': main()
