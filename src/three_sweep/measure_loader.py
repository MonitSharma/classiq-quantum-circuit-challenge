"""Bounded seed screen for the five-output low-five-y loader."""

import json
from pathlib import Path

from .loader5 import compile_loader, tables_from_codebook


def screen(codebook_path="artifacts/three_sweep/codebook_deterministic.json",
           seeds=range(32), output_dir="artifacts/three_sweep/loader"):
    tables = tables_from_codebook(codebook_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in seeds:
        circuit = compile_loader(tables, seed)
        qasm_path = output_dir / f"loader5_seed{seed}.qasm"
        from qiskit import qasm2
        qasm_path.write_text(qasm2.dumps(circuit))
        rows.append({
            "seed": seed,
            "qasm": str(qasm_path),
            "depth": circuit.depth(),
            "cx_count": circuit.count_ops().get("cx", 0),
            "width": circuit.num_qubits,
        })
    rows.sort(key=lambda row: (row["depth"], row["cx_count"], row["seed"]))
    report = {"codebook": codebook_path, "seeds": len(rows), "results": rows}
    (output_dir / "screen.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"best": rows[0], "worst_depth": max(r["depth"] for r in rows)}, indent=2))
    return report


if __name__ == "__main__":
    screen()
