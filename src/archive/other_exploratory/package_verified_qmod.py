"""Add a literal gate-for-gate QMOD companion to an ALREADY VERIFIED package folder.

The QASM is left untouched; the QMOD mirrors it gate for gate, and main adds twelve preparation
Hadamards (absent from the oracle QASM), matching the convention of artifacts/118/ and artifacts/123/.
"""
import argparse, hashlib, json, re
from pathlib import Path
from qiskit import qasm2
from classiq import qfunc, QArray, QBit, Output, allocate, H, U, CX, Constraints, OptimizationParameter, create_model, write_qmod


def package(source, outdir, name):
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    report = json.loads(source.with_suffix('.exhaustive.json').read_text())
    assert report['sha256'] == sha, (report['sha256'], sha)
    assert report['basis_inputs_checked'] == 4096
    assert report['challenge_width_eligible'] is True
    q = qasm2.load(source)
    assert q.num_qubits == 18 and set(q.count_ops()) <= {'u3', 'cx'}, q.count_ops()
    gates = [(i.operation.name, list(map(float, i.operation.params)),
              [q.find_bit(b).index for b in i.qubits]) for i in q.data]

    @qfunc
    def conditional_loader_logo_oracle(q: QArray[QBit, 18]):
        for gname, p, w in gates:
            if gname == 'cx':
                CX(q[w[0]], q[w[1]])
            else:
                U(p[0], p[1], p[2], 0.0, q[w[0]])

    @qfunc
    def main(q: Output[QArray[QBit, 18]]):
        allocate(18, q)
        for i in range(12):
            H(q[i])
        conditional_loader_logo_oracle(q)

    model = create_model(main, constraints=Constraints(max_width=18,
                                                       optimization_parameter=OptimizationParameter.DEPTH))
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_qmod(model, name, directory=outdir, decimal_precision=17)
    qm = outdir / f'{name}.qmod'
    qm.write_text(f'// Standalone QASM SHA-256: {sha}\n'
                  f'// Literal gate-for-gate companion of the QASM; main adds twelve preparation Hadamards '
                  f'(absent from the QASM).\n' + qm.read_text())

    # gate-for-gate check against the source QASM
    body = qm.read_text().split('qfunc conditional_loader_logo_oracle', 1)[1].split('}', 1)[0]
    parsed = []
    for gname, args in re.findall(r'\b(U|CX)\(([^;]+)\);', body):
        w = list(map(int, re.findall(r'q\[(\d+)\]', args)))
        if gname == 'CX':
            parsed.append(('cx', [], w))
        else:
            p = list(map(float, args.split(',')[:4]))
            assert p[3] == 0.0
            parsed.append(('u3', p[:3], w))
    assert parsed == gates, 'QMOD does not match the QASM gate for gate'
    print(json.dumps(dict(qasm=source.name, qmod=qm.name, sha256=sha, gates=len(gates),
                          depth=report['depth'], cx=report['cx_count'],
                          qmod_gate_match=True, qmod_gate_count=len(gates)), indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--outdir', type=Path, required=True)
    a = p.parse_args()
    package(a.source, a.outdir, a.name)
