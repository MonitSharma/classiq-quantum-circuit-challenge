"""Run the audited Quasar v3 artifact with paid IBM rebasing and saved outputs.

Use src/run_bounded.py around this process. Install artifact dependencies in an
isolated directory, supplied through PYTHONPATH; do not replace repo packages.
All snapshots still require native scoring and exhaustive oracle verification.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile


def verify_outputs(root):
    from distributed_frame_search import native
    from exhaustive_verify import exhaustive
    rows, seen = [], set()
    sources = [root / 'input_ibm.qasm', *sorted((root / 'snapshots').glob('*.qasm'))]
    if (root / 'output_ibm.qasm').exists():
        sources.append(root / 'output_ibm.qasm')
    for path in sources:
        # Upstream uses the legacy qelib extension for sx. Our exported result
        # is standalone u3/cx, parsed by the strict exhaustive verifier.
        q = native(QuantumCircuit.from_qasm_file(str(path)))
        text = qasm2.dumps(q)
        if text in seen:
            continue
        seen.add(text)
        output = root / (path.stem + '_native.qasm')
        assert not output.exists()
        output.write_text(text)
        exhaustive(output)
        rows.append(dict(source=str(path), native=str(output), depth=q.depth(), cx=q.count_ops().get('cx', 0)))
    (root / 'native_results.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=45)
    p.add_argument('--step', type=int, default=3)
    p.add_argument('--score-only', action='store_true')
    a = p.parse_args()
    if a.score_only:
        print(verify_outputs(a.outdir))
        return
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    original = qasm2.load('artifacts/185/two_stage_185.qasm')
    rebased = transpile(original, basis_gates=['rz', 'sx', 'x', 'cx'], optimization_level=3,
                        seed_transpiler=185, qubits_initially_zero=False)
    assert rebased.layout is None or rebased.layout.final_index_layout() == list(range(18))
    input_path = a.outdir / 'input_ibm.qasm'
    input_path.write_text(qasm2.dumps(rebased))
    (a.outdir / 'input_metrics.json').write_text(json.dumps(dict(depth=rebased.depth(), ops=dict(rebased.count_ops())), indent=2))
    sys.path.insert(0, str(a.artifact / 'seq-eg'))
    # The upstream decimal parser calls limit_denominator() (default 10^6),
    # which perturbs otherwise exact input rotations by ~1e-11 in this oracle.
    # Keep binary input floats exact as rational values, then round-trip with
    # 17 digits. Preserve the downloaded artifact and save the two-line patch.
    source = (a.artifact / 'seq-eg/optimize.py').read_text()
    assert source.count('Fraction(n.value).limit_denominator()') == 1
    assert source.count('{float(b):.15g}') == 1
    patched = source.replace('Fraction(n.value).limit_denominator()', 'Fraction(n.value)').replace('{float(b):.15g}', '{float(b):.17g}')
    patch_path = a.outdir / 'optimize_precise.py'
    patch_path.write_text(patched)
    (a.outdir / 'precision_patch.json').write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        patched_sha256=hashlib.sha256(patched.encode()).hexdigest(),
        changes=['Remove Fraction.limit_denominator from numeric constants', 'Format decimal outputs with 17 significant digits']), indent=2))
    spec = importlib.util.spec_from_file_location('quasar_precise_optimize', patch_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert float(module._eval_angle('0.12345678912345678')[1]) == float('0.12345678912345678')
    print('Rebased input:', rebased.depth(), dict(rebased.count_ops()), flush=True)
    module.optimize_until_stable(
        rules_path=str(a.artifact / 'seq-eg/rules.txt'),
        rules_once_path=None, init_qasm_path=str(input_path),
        work_path=str(a.outdir / 'work.qasm'), final_path=str(a.outdir / 'output_ibm.qasm'),
        gate_set='ibm_new', max_iters=3, explore_step_each_stage=a.step,
        ilp_disabled=True, time_limit_sec=a.seconds, escalate=True, max_step=a.step + 1,
        timeline_csv=str(a.outdir / 'timeline.csv'), snapshot_dir=str(a.outdir / 'snapshots'),
    )


if __name__ == '__main__':
    main()
