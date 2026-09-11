"""Five-output low-five-y code loader for the three-sweep experiment."""

import json
from pathlib import Path

from qiskit import qasm2, transpile

from full_mux import multiplexer


CONTROLS = list(range(6, 11))
TARGETS = list(range(12, 17))


def tables_from_codebook(path: str | Path) -> list[int]:
    data = json.loads(Path(path).read_text())
    z_to_code = {int(z): int(code) for z, code in data["z_to_code"].items()}
    return [
        sum(((z_to_code[z] >> bit) & 1) << z for z in range(32))
        for bit in range(5)
    ]


def build(tables: list[int], seed: int = 0):
    if len(tables) != 5:
        raise ValueError("expected five Boolean tables")
    return multiplexer(tables, TARGETS, CONTROLS, "y", seed)


def compile_loader(tables: list[int], seed: int = 0):
    return transpile(
        build(tables, seed),
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=seed,
    )


def write_candidate(tables: list[int], path: str | Path, seed: int = 0) -> dict:
    circuit = compile_loader(tables, seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qasm2.dumps(circuit))
    return {
        "qasm": str(path),
        "seed": seed,
        "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "width": circuit.num_qubits,
        "per_wire_ops": {
            str(i): sum(1 for instruction in circuit.data
                        if i in [circuit.find_bit(q).index for q in instruction.qubits])
            for i in range(circuit.num_qubits)
        },
    }

