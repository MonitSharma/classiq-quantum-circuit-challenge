"""Bounded physical-row CEGIS for joint five-batch x/y encoders."""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from post190_degree_rank_bound import targets

FULL = (1 << 64) - 1
VARS = [sum(1 << p for p in range(64) if p & (1 << bit)) for bit in range(6)]

def reduce_by(value: int, rows: list[int]) -> int:
    piv = {}
    for row in rows:
        while row:
            bit = row.bit_length() - 1
            if bit in piv: row ^= piv[bit]
            else: piv[bit] = row; break
    while value:
        bit = value.bit_length() - 1
        if bit not in piv: break
        value ^= piv[bit]
    return value

def wanted_tables():
    raw = targets()
    return {s: [sum(bit << p for p, bit in enumerate(v)) for v in rows]
            for s, rows in raw.items()}

def residual(rows, wanted, points=range(64)):
    mask = sum(1 << p for p in points)
    basis = [r & mask for r in rows] + [mask]
    return sum((reduce_by(t & mask, basis) & mask).bit_count() for t in wanted)

def affine_residual(rows, wanted): return residual(rows, wanted)

def random_batch(rng, count=3):
    order = list(range(9)); rng.shuffle(order); out = []
    for i in range(0, 7, 3):
        if len(out) == count or rng.random() < .25: continue
        out.append(tuple(order[i:i + 3]))
    return out

def beam_side(wanted, points, stages, rng, width=24, options_per_state=20):
    """Bounded beam over physical batches; paths retain their gate history."""
    initial = tuple(VARS + [0, 0, 0])
    beam = [(initial, [])]
    seen = {initial}
    for _ in range(stages):
        expanded = []
        for rows, history in beam:
            options = [[]]
            while len(options) < options_per_state:
                batch = random_batch(rng)
                if batch not in options: options.append(batch)
            for batch in options:
                nxt = apply(rows, batch)
                if nonlinear_storage(nxt) > 6: continue
                if nxt in seen: continue
                seen.add(nxt)
                key = (residual(nxt, wanted, points), affine_residual(nxt, wanted),
                       sum(bool(b) for b in history+[batch]), sum(len(b) for b in history+[batch]))
                expanded.append((key, nxt, history+[batch]))
        expanded.sort(key=lambda item: item[0])
        beam = [(rows, history) for _, rows, history in expanded[:width]]
        if not beam: break
    return beam

def apply(rows, batch):
    before, out = rows, list(rows)
    for a, b, t in batch: out[t] ^= before[a] & before[b]
    return tuple(out)

def nonlinear_storage(rows):
    """Number of physical rows outside the input-plus-constant affine span."""
    affine = VARS + [FULL]
    return sum(reduce_by(row, affine) != 0 for row in rows)

def storage_profile(batches, limit=6):
    rows = tuple(VARS + [0, 0, 0]); profile = []
    for batch in batches:
        rows = apply(rows, batch)
        profile.append(nonlinear_storage(rows))
    peak = max(profile, default=0)
    return {'peak': peak, 'profile': profile, 'within_limit': peak <= limit}

def nonlinear_batches(batches): return sum(bool(b) for b in batches)
def toggle_count(batches): return sum(len(b) for b in batches)

def peak_liveness(batches):
    live, peak = set(range(6)), 6
    for batch in batches:
        for a, b, t in batch: live.update((a, b, t))
        peak = max(peak, len(live))
    return peak

def candidate_score(x, y, xb, yb, wanted, points=range(64)):
    exact = residual(x, wanted['x'], points) + residual(y, wanted['y'], points)
    affine = affine_residual(x, wanted['x']) + affine_residual(y, wanted['y'])
    return (exact, affine, nonlinear_batches(xb)+nonlinear_batches(yb),
            max(peak_liveness(xb), peak_liveness(yb)), toggle_count(xb)+toggle_count(yb))

def failing_points(x, y, wanted):
    bad = 0
    for rows, side in ((x, 'x'), (y, 'y')):
        basis = list(rows) + [FULL]
        for target in wanted[side]:
            bad |= reduce_by(target, basis)
    return [p for p in range(64) if bad >> p & 1]

def affine_decomposition(target, rows):
    items = list(enumerate(rows)) + [(-1, FULL)]
    for mask in range(1 << len(items)):
        value = 0; chosen = []
        for i, (idx, row) in enumerate(items):
            if mask >> i & 1: value ^= row; chosen.append(idx)
        if value == target: return chosen
    return None

def materialize_affine_frames(qc, rows, wanted, wires, targets_):
    ops = []
    for target, want in zip(targets_, wanted):
        chosen = affine_decomposition(want, rows)
        if chosen is None: return {'exact': False, 'reason': 'not-affine'}
        if -1 in chosen: qc.x(wires[target]); ops.append(('x', wires[target]))
        for source in chosen:
            if source >= 0 and source != target:
                qc.cx(wires[source], wires[target]); ops.append(('cx', wires[source], wires[target]))
    return {'exact': True, 'ops': ops, 'depth': qc.depth()}

def materialize_encoder(batches, wanted_side, input_wires, target_wires, n=9):
    qc = QuantumCircuit(n); physical = list(input_wires) + list(target_wires)
    for batch in batches:
        for a, b, t in batch: qc.rccx(physical[a], physical[b], physical[t])
    rows = tuple(VARS + [0, 0, 0])
    for batch in batches: rows = apply(rows, batch)
    frame = materialize_affine_frames(qc, rows, wanted_side, physical, range(6, 9))
    return qc, rows, frame

def compose_preserved_kernel(x_batches, y_batches, package=Path('artifacts/190')):
    """Compose exact lowered replacements with the recorded kernel.

    This is intentionally callable only after both affine frames are exact.
    The package is read-only; the returned circuit is a fresh native circuit.
    """
    from distributed_frame_search import native
    from post190_register_compose import KERNEL_WIRES
    wanted = wanted_tables()
    y, yr, yf = materialize_encoder(y_batches, wanted['y'], range(6), range(6, 9))
    x, xr, xf = materialize_encoder(x_batches, wanted['x'], range(6), range(6, 9))
    if not (yf['exact'] and xf['exact']):
        raise ValueError('encoder is not exact in the full affine span')
    enc = QuantumCircuit(18)
    enc.compose(y, list(range(6, 12)) + list(range(12, 15)), inplace=True)
    enc.compose(x, list(range(0, 6)) + list(range(15, 18)), inplace=True)
    kernel = qasm2.load(package / 'kernel.qasm')
    return native(enc.compose(kernel, KERNEL_WIRES).compose(enc.inverse()))

def cegis(seconds, seed, stages=5, affine_budget=14, sample_size=8, beam_width=24):
    wanted = wanted_tables(); rng = random.Random(seed)
    points = sorted(rng.sample(range(64), sample_size)); x = y = tuple(VARS+[0,0,0]); xb = yb = []
    best = None; start = time.monotonic(); iterations = rounds = 0
    while time.monotonic()-start < seconds:
        xbeam = beam_side(wanted['x'], points, stages, rng, beam_width)
        ybeam = beam_side(wanted['y'], points, stages, rng, beam_width)
        pairs = []
        for px, bx in xbeam:
            for py, by in ybeam:
                pairs.append((candidate_score(px, py, bx, by, wanted, points), px, py, bx, by))
        pairs.sort(key=lambda item: item[0])
        for score, px, py, bx, by in pairs[:min(32, len(pairs))]:
            full = candidate_score(px,py,bx,by,wanted)
            if best is None or full < best['full_score']:
                best={'score':score,'full_score':full,'x_batches':bx,'y_batches':by,
                      'x_rows':px,'y_rows':py,'sample_points':points[:],'round':rounds,
                      'x_storage':storage_profile(bx),'y_storage':storage_profile(by)}
                points=sorted(set(points)|set(failing_points(px,py,wanted)[:16])); rounds += 1
        if best and best['full_score'][0] == 0 and best['full_score'][1] <= affine_budget: break
        iterations += 1
    return {'status':'complete','seed':seed,'seconds':time.monotonic()-start,'iterations':iterations,
            'cegis_rounds':rounds,'sample_points':points,'affine_budget':affine_budget,'best':best,
            'beam_width': beam_width,
            'decision_gate':('build-full-oracle' if best and best['full_score'][0]==0 and best['full_score'][1]<=affine_budget else 'bounded-negative-or-pending')}

def run(seconds, seed, stages=5):
    r=cegis(seconds,seed,stages); b=r.get('best') or {}; r.update(
      best_affine_residual=(b.get('full_score') or (None,None))[1], exact_side_span=bool(b and b['full_score'][0]==0),
      x_batches=b.get('x_batches',[]), y_batches=b.get('y_batches',[]), native_materialization='available-for-exact-candidate', full_oracle_verification='NOT_RUN')
    return r

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); p.add_argument('--seconds',type=float,default=5); p.add_argument('--seed',type=int,default=137); p.add_argument('--affine-budget',type=int,choices=(8,10,12,14),default=14); a=p.parse_args()
    result=run(a.seconds,a.seed); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2,default=list)+'\n'); print(json.dumps(result,indent=2,default=list))
if __name__=='__main__': main()
