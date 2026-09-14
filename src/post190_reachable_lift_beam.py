"""Search phase-equivalent reachable-domain lifts with the current beam scheduler.

The 190 kernel only needs to be correct on code words produced by the two
loaders.  Values on the other 8-bit words are free, while adding an even
integer Boolean function is phase-equivalent everywhere.  This script searches
those freedoms, then scores the resulting exact kernels with the shipped
arrival profile.  It is deliberately an experiment: it never overwrites a
protected package.
"""
import argparse, json, math, random
from pathlib import Path
import numpy as np
from qiskit import qasm2
from build_two_stage_196 import encoders, KERNEL_WIRES
from distributed_frame_search import native
from post218_beam_phase import psynth
from post258_joint_encoder_schedule import touches
from post196_free_ancilla_order import finish


def reachable(codes):
    from post258_two_stage_anf import decode
    import two_stage_oracle as ts
    yl, xl = decode(codes['ylab']), decode(codes['xlab'])
    out = set()
    for y in range(64):
        yv = ((y >> 5) & 1)
        yc = yl[((y & 32).bit_count() & 1, ts.ROWCLS[y])]
        for x in range(64):
            xv = (x & 48).bit_count() & 1
            xc = xl[(((x & 48).bit_count() & 1), ts.COLCLS[x])]
            out.add(yv | (yc << 1) | (xv << 4) | (xc << 5))
    return sorted(out)


def coeff(values):
    from depth_parity_network import walsh
    return walsh(np.asarray(values, float) * math.pi)


def phase_values(path):
    """Return unwrapped phase in units of pi, matching coeff's input units."""
    # The 190 package is a later schedule of the same 63-term phase recipe;
    # use the saved coefficients as the canonical, unwrapped representation.
    recipe = Path('artifacts/193_cx853/phase_search_recipe.json')
    if recipe.exists():
        from depth_parity_network import walsh
        co = np.asarray(json.loads(recipe.read_text())['co'], float) * math.pi
        return walsh(co) * len(co) / math.pi
    from qiskit.quantum_info import Operator
    op = Operator(qasm2.load(path)).data
    # The packaged kernel intentionally exits in a physical ancilla
    # permutation. Read the phase from the sole nonzero entry of each input
    # column instead of assuming the operator is diagonal.
    cols = np.argmax(np.abs(op), axis=0)
    d = op[cols, np.arange(op.shape[1])]
    # The kernel's phase polynomial is a dyadic real phase, not merely a
    # Boolean sign. Keep the principal angle; adding 2 to any value is a
    # phase-equivalent lift.
    vals = np.angle(d) / math.pi
    assert np.max(np.abs(np.abs(d) - 1)) < 1e-8
    return vals


def run(outdir, candidates, steps, seed):
    assert not outdir.exists(); outdir.mkdir(parents=True)
    package = Path('artifacts/190')
    codes = json.loads((package/'class_codes.json').read_text())
    care = set(reachable(codes)); base = phase_values(package/'kernel.qasm')
    rng = random.Random(seed)
    # Even monomials preserve exp(i*pi*f) on every input. Free points preserve
    # the actual oracle because the loaders never produce them.
    mono = np.array([[1.0 if (m & ~w) == 0 else 0.0 for w in range(256)]
                     for m in range(256)])
    free = [w for w in range(256) if w not in care]
    def score(v):
        c = coeff(v)
        return int(np.count_nonzero(np.abs(c[1:]) > 1e-10)), c
    best = None; rows = []
    for trial in range(candidates):
        cur = base.copy()
        champion = base.copy(); champion_score, _ = score(base)
        # Start from a few random free-domain completions; then anneal exact
        # null moves. The current Boolean completion is always retained.
        for w in free:
            if trial and rng.random() < .05: cur[w] = rng.randrange(2)
        cur_score, _ = score(cur)
        if cur_score < champion_score:
            champion, champion_score = cur.copy(), cur_score
        for step in range(steps):
            nxt = cur.copy()
            if rng.random() < .45:
                nxt[rng.choice(free)] = rng.randrange(2)
            else:
                nxt += rng.choice((2, -2, 4, -4)) * mono[rng.randrange(256)]
            val, _ = score(nxt)
            temp = .4 + 4.0 * (1 - (step % 1200) / 1200)
            if val <= cur_score or rng.random() < math.exp((cur_score-val)/temp):
                cur, cur_score = nxt, val
            if cur_score < champion_score:
                champion, champion_score = cur.copy(), cur_score
        row = dict(trial=trial, terms=champion_score)
        if best is None or champion_score < best[0]:
            best = (champion_score, champion.copy())
            row['best'] = True
            np.save(outdir/f'completion_{champion_score}.npy', champion)
            print('completion', row, flush=True)
        rows.append(row)
        (outdir/'report.json').write_text(json.dumps(dict(care=len(care), candidates=trial+1,
            steps=steps, best_terms=best[0], rows=rows), indent=2))
    # Compile only the best few completions. The caller can promote a full
    # oracle only after exhaustive_verify and hash-matched replay.
    arrivals = touches(encoders(codes, 298, 506))
    best_rows = []
    for path in sorted(outdir.glob('completion_*.npy')):
        v = np.load(path); co = coeff(v)
        targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-10}
        for kseed in range(6):
            k = native(psynth(8, targets, seed=kseed, beam=96, branch=22,
                              alpha=6.0, timew=1.4, horizon=1.5, fill=2,
                              initial_times=[arrivals[w]-min(arrivals) for w in KERNEL_WIRES]))
            best_rows.append(dict(completion=path.name, seed=kseed,
                                  kernel_depth=k.depth(), cx=k.count_ops().get('cx', 0)))
    (outdir/'compiled.json').write_text(json.dumps(best_rows, indent=2))
    print('done', {'best_terms': best[0], 'compiled': sorted(best_rows, key=lambda x:(x['kernel_depth'],x['cx']))[:5]}, flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--candidates', type=int, default=16); p.add_argument('--steps', type=int, default=3000)
    p.add_argument('--seed', type=int, default=190); a=p.parse_args(); run(a.outdir,a.candidates,a.steps,a.seed)
