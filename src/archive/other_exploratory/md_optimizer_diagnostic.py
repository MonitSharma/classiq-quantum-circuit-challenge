"""Bounded post-lowering optimizer diagnostic for the MD prototype."""

from pathlib import Path

from pytket.passes import FullPeepholeOptimise
from pytket.qasm import circuit_from_qasm_str, circuit_to_qasm_str


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "artifacts/multiplicative_depth/md_rank_stream.qasm"
    target = ROOT / "artifacts/multiplicative_depth/md_rank_stream_pytket.qasm"
    circuit = circuit_from_qasm_str(source.read_text())
    FullPeepholeOptimise().apply(circuit)
    target.write_text(circuit_to_qasm_str(circuit))
    print({"qasm": str(target), "depth": circuit.depth(), "gate_count": circuit.n_gates})


if __name__ == "__main__":
    main()
