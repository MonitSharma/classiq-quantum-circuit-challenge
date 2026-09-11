"""Basis-action check for the serialized y code loader."""

import json
import sys
from pathlib import Path

import hashlib
import numpy as np
from qiskit import qasm2

from comparator_oracle_structure import Y_B, Y_M


def main(path):
    q = qasm2.loads(Path(path).read_text())
    n = 4096
    indices = np.arange(n, dtype=np.int32)[:, None]
    amp = np.ones((n, 1), complex)
    tol = 2e-12
    dropped = np.zeros(n)
    peak = 1

    def compress(idx, values):
        order = np.argsort(idx, axis=1)
        idx = np.take_along_axis(idx, order, axis=1)
        values = np.take_along_axis(values, order, axis=1)
        first = np.ones(idx.shape, bool); first[:, 1:] = idx[:, 1:] != idx[:, :-1]
        group = np.cumsum(first, axis=1) - 1
        width = int(group[:, -1].max()) + 1
        target = (np.arange(n)[:, None] * width + group).ravel()
        real = np.bincount(target, weights=values.real.ravel(), minlength=n * width)
        imag = np.bincount(target, weights=values.imag.ravel(), minlength=n * width)
        sums = (real + 1j * imag).reshape(n, width)
        outidx = np.zeros((n, width), np.int32)
        rr = np.broadcast_to(np.arange(n)[:, None], idx.shape)[first]
        outidx[rr, group[first]] = idx[first]
        keep = np.abs(sums) > tol
        lost = np.sum(np.abs(sums) * ~keep, axis=1)
        count = keep.sum(1); outw = int(count.max())
        dest = np.cumsum(keep, axis=1) - 1
        out = np.zeros((n, outw), np.int32); values_out = np.zeros((n, outw), complex)
        rr = np.broadcast_to(np.arange(n)[:, None], sums.shape)[keep]
        out[rr, dest[keep]] = outidx[keep]
        values_out[rr, dest[keep]] = sums[keep]
        return out, values_out, lost

    for inst in q.data:
        wires = [q.find_bit(v).index for v in inst.qubits]
        if inst.operation.name == "cx":
            indices ^= (((indices >> wires[0]) & 1) << wires[1])
        else:
            theta, phi, lam = map(float, inst.operation.params)
            c, s = np.cos(theta / 2), np.sin(theta / 2)
            bit = (indices >> wires[0]) & 1
            if abs(s) < tol:
                amp *= np.where(bit, np.exp(1j * (phi + lam)) * c, c)
            elif abs(c) < tol:
                amp *= np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
                indices ^= 1 << wires[0]
            else:
                aa = amp * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
                bb = amp * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
                indices, amp, lost = compress(
                    np.concatenate([indices, indices ^ (1 << wires[0])], axis=1),
                    np.concatenate([aa, bb], axis=1))
                dropped += lost; peak = max(peak, amp.shape[1])
    bad = []
    for x in range(64):
        for y in range(64):
            row = x | (y << 6)
            code = (Y_B[y] & 1) | ((Y_M[y] & 7) << 1)
            expected = row | (code << 12)
            matches = np.where(indices[row] == expected)[0]
            good = len(matches) == 1 and abs(abs(amp[row, matches[0]]) - 1) < 1e-9
            if not good:
                bad.append({"x": x, "y": y, "expected_index": int(expected),
                            "actual_indices": [int(v) for v in indices[row]],
                            "max_amplitude": float(np.max(np.abs(amp[row])))})
    report = {"qasm": str(Path(path).resolve()),
              "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
              "basis_inputs_checked": n,
              "mismatches": len(bad),
              "counterexamples": bad,
              "peak_sparse_support": peak,
              "verification": "4096 coordinate basis actions: x/y preservation, code in q12..q15, unused wires zero"}
    report["max_amplitude_error"] = float(max((abs(abs(a) - 1) for a in amp.flat), default=0))
    out = Path(path).with_suffix(".basis.json")
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1])
