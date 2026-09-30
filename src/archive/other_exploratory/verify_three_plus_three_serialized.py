"""Verify serialized 3+3 encoders on all six-bit computational inputs."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from qiskit import qasm2
from comparator_oracle_structure import X_C, X_LVL, Y_B, Y_M


def expected_index(original, metrics):
    side = metrics["side"]
    offset = 6 if side == "y" else 0
    anc = list(range(12, 15)) if side == "y" else list(range(15, 18))
    overwrite = metrics["overwrite"]
    codes = (Y_B, Y_M) if metrics["side"] == "y" else (X_C, X_LVL)
    code_bits = [bit for bit in range(4) if bit != overwrite]
    bits = [0] * 18
    for i in range(6):
        bits[offset + i] = ((original >> i) & 1) if i != 5 else 0
    rows = metrics["linear_rows"]
    for i, row in enumerate(rows[:5]):
        bits[offset + i] = (original & row).bit_count() & 1
    overwritten = (codes[0][original] if overwrite == 0 else codes[1][original])
    bits[offset + 5] = (overwritten >> (0 if overwrite == 0 else overwrite - 1)) & 1
    for j, target in enumerate(anc):
        bit = code_bits[j]
        value = codes[0][original] if bit == 0 else codes[1][original]
        bits[target] = (value >> (0 if bit == 0 else bit - 1)) & 1
    return sum(bit << i for i, bit in enumerate(bits))


def main(qasm_path, metrics_path):
    qasm_file = Path(qasm_path)
    metrics = json.loads(Path(metrics_path).read_text())
    circuit = qasm2.loads(qasm_file.read_text())
    if circuit.num_qubits > 18 or set(circuit.count_ops()) - {"u3", "cx"}:
        raise ValueError("serialized circuit is not in the required u3/cx basis")
    n = 64
    offset = 6 if metrics["side"] == "y" else 0
    indices = (np.arange(n, dtype=np.int32) << offset)[:, None]
    amplitudes = np.ones((n, 1), complex)
    tol = 2e-12

    def compress(idx, values):
        order = np.argsort(idx, axis=1)
        idx = np.take_along_axis(idx, order, axis=1)
        values = np.take_along_axis(values, order, axis=1)
        first = np.ones(idx.shape, bool)
        first[:, 1:] = idx[:, 1:] != idx[:, :-1]
        group = np.cumsum(first, axis=1) - 1
        width = int(group[:, -1].max()) + 1
        target = np.arange(n)[:, None] * width + group
        sums = (np.bincount(target.ravel(), weights=values.real.ravel(), minlength=n * width)
                + 1j * np.bincount(target.ravel(), weights=values.imag.ravel(), minlength=n * width))
        sums = sums.reshape(n, width)
        outidx = np.zeros((n, width), np.int32)
        rr = np.broadcast_to(np.arange(n)[:, None], idx.shape)[first]
        outidx[rr, group[first]] = idx[first]
        keep = np.abs(sums) > tol
        outw = int(keep.sum(1).max())
        dest = np.cumsum(keep, axis=1) - 1
        rr = np.broadcast_to(np.arange(n)[:, None], sums.shape)[keep]
        outidx2 = np.zeros((n, outw), np.int32)
        values2 = np.zeros((n, outw), complex)
        outidx2[rr, dest[keep]] = outidx[keep]
        values2[rr, dest[keep]] = sums[keep]
        return outidx2, values2

    for inst in circuit.data:
        wires = [circuit.find_bit(v).index for v in inst.qubits]
        if inst.operation.name == "cx":
            indices ^= (((indices >> wires[0]) & 1) << wires[1])
            continue
        theta, phi, lam = map(float, inst.operation.params)
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        bit = (indices >> wires[0]) & 1
        if abs(s) < tol:
            amplitudes *= np.where(bit, np.exp(1j * (phi + lam)) * c, c)
        elif abs(c) < tol:
            amplitudes *= np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
            indices ^= 1 << wires[0]
        else:
            low = amplitudes * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
            high = amplitudes * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
            indices, amplitudes = compress(
                np.concatenate([indices, indices ^ (1 << wires[0])], axis=1),
                np.concatenate([low, high], axis=1))
    failures = []
    for original in range(64):
        index = int(indices[original, np.abs(amplitudes[original]).argmax()])
        expected = expected_index(original, metrics)
        if index != expected or abs(np.max(np.abs(amplitudes[original])) - 1) > 1e-9:
            failures.append({"input": original, "expected": expected,
                             "actual": index, "amplitude": float(np.max(np.abs(amplitudes[original])))})
    report = {
        "qasm": str(qasm_file.resolve()),
        "qasm_sha256": hashlib.sha256(qasm_file.read_bytes()).hexdigest(),
        "metrics": str(Path(metrics_path).resolve()),
        "inputs_checked": 64,
        "mismatches": len(failures),
        "counterexamples": failures,
        "verification": "serialized u3/cx QASM basis action",
    }
    if "qasm_sha256" in metrics and metrics["qasm_sha256"] != report["qasm_sha256"]:
        raise ValueError("metrics QASM SHA does not match serialized file")
    output = qasm_file.with_suffix(".serialized.verify.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
