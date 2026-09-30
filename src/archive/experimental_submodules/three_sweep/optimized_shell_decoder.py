"""Build the best bounded shell-codebook candidate."""

import json
from pathlib import Path

from qiskit import qasm2

from .codebook_search import search
from .shell_decoder import build


def write(seed=0, path="artifacts/three_sweep/optimized_shell_decoder.qasm"):
    result = search()
    lower = {int(k): int(v) for k, v in result["lower_best"]["labels"].items()}
    upper = {int(k): int(v) for k, v in result["upper_best"]["labels"].items()}
    circuit = build(seed, lower_labels=lower, upper_labels=upper)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qasm2.dumps(circuit))
    metrics = {
        "seed": seed,
        "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "width": circuit.num_qubits,
        "lower_labels": lower,
        "upper_labels": upper,
        "qasm": str(path),
    }
    path.with_suffix(".metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    write()

