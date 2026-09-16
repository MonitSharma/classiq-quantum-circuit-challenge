"""Audit exact diagonal phase completion from saved 18-wire checkpoints."""
from __future__ import annotations
import argparse, itertools, json, time
from pathlib import Path

from destructive_phase_xag import basis, represent
from post129_phase_rooted_xag import PhaseRooted, resume_state
from destructive_xag import load_xag
from md_xag import FULL

SOURCE = Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag')
DEFAULTS = [Path('artifacts/post129_phase_rooted_longer/best.json'),
            Path('artifacts/post129_phase_rooted_resumed/best.json'),
            Path('artifacts/post129_phase_rooted_reset/best.json')]

def add_with_witness(piv, vector, witness):
    """Insert a GF(2) vector and its monomial witness into a pivot basis."""
    value, combo = vector, witness
    while value:
        bit = value.bit_length() - 1
        if bit in piv:
            old, old_combo = piv[bit]; value ^= old; combo ^= old_combo
        else:
            piv[bit] = (value, combo); return

def reduce_witness(value, piv):
    combo = 0
    while value:
        bit = value.bit_length() - 1
        if bit not in piv: return value, combo
        old, old_combo = piv[bit]; value ^= old; combo ^= old_combo
    return 0, combo

def phase_profile(rows, residual_phase, max_degree=9, recover_degree=4):
    piv = {}
    terms = []
    add_with_witness(piv, FULL, 0)
    profile = []
    for degree in range(1, max_degree + 1):
        for wires in itertools.combinations(range(len(rows)), degree):
            value = FULL
            for wire in wires: value &= rows[wire]
            witness = 1 << len(terms)
            terms.append(wires)
            add_with_witness(piv, value, witness)
        remainder, witness = reduce_witness(residual_phase, piv)
        row = {'degree': degree, 'monomial_count': len(terms), 'rank': len(piv),
               'residual_weight': remainder.bit_count(), 'exact': remainder == 0}
        if row['exact']:
            if degree <= recover_degree:
                selected = [terms[i] for i in range(len(terms)) if witness >> i & 1]
                row['representation'] = selected
            profile.append(row)
            return profile
        profile.append(row)
    return profile

def analyze(path, source=SOURCE, max_degree=9):
    parsed = load_xag(source); lower = PhaseRooted(parsed, seed=0)
    state = resume_state(lower, path)
    residual_phase = lower.target ^ state.phase
    started = time.monotonic()
    profile = phase_profile(state.rows, residual_phase, max_degree=max_degree)
    exact = next((r for r in profile if r['exact']), None)
    return {'checkpoint': str(path), 'phase_mask_bits': state.phased_roots.bit_count(),
            'forward_depth': max(state.clocks), 'residual_weight': residual_phase.bit_count(),
            'wire_count': len(state.rows), 'profile': profile,
            'minimum_degree_found': exact['degree'] if exact else None,
            'elapsed_seconds': time.monotonic()-started}

def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, action='append'); p.add_argument('--max-degree', type=int, default=9)
    a = p.parse_args(); paths = a.checkpoint or [v for v in DEFAULTS if v.exists()]
    result = {'status': 'complete', 'source': str(SOURCE), 'checkpoints': [analyze(v, max_degree=a.max_degree) for v in paths]}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, indent=2)+'\n'); print(json.dumps(result, indent=2))
if __name__ == '__main__': main()
