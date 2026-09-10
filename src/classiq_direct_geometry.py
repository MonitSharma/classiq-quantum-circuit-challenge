"""Classiq-native direct arithmetic geometry model.

This intentionally gives Qmod the four shape predicates rather than prescribing
the repository's UCR/radius architecture.  It writes only a logical QMOD until
the caller requests synthesis.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("CLASSIQ_TEXT_ONLY", "true")
from classiq import *
from classiq.qmod.symbolic import pi
from qiskit import qasm2, transpile


ROOT = Path(__file__).resolve().parents[1]


@qperm
def logo_phase_oracle(x: Const[QNum[6]], y: Const[QNum[6]]) -> None:
    square = (x >= 2) & (x <= 26) & (y >= 29) & (y <= 53)
    bar = (x >= 26) & (x <= 49) & (y >= 39) & (y <= 43)
    disk1 = ((x - 55) ** 2 + (y - 41) ** 2) <= 42
    disk2 = ((x - 40) ** 2 + (y - 19) ** 2) <= 72
    control(square | bar | disk1 | disk2, lambda: phase(pi))


@qfunc
def main(x: Output[QNum[6]], y: Output[QNum[6]]) -> None:
    allocate(x)
    allocate(y)
    hadamard_transform(x)
    hadamard_transform(y)
    logo_phase_oracle(x, y)


def make_model():
    return create_model(
        main,
        constraints=Constraints(
            optimization_parameter=OptimizationParameter.DEPTH,
            max_width=18,
        ),
    )


if __name__ == "__main__":
    model = make_model()
    out = ROOT / "artifacts/classiq_direct_geometry.qmod"
    write_qmod(model, str(out.with_suffix("")))
    print(out)
    if "--synthesize" in sys.argv:
        print("Synthesis requested; use the Classiq SDK only after model creation succeeds.")
        result = synthesize(model)
        raw = export(result, TargetLanguage.QASM2)
        lines = raw.splitlines()
        prep = [i for i, line in enumerate(lines)
                if "hadamard_transform_" in line and "q[" in line
        ]
        if len(prep) != 2:
            raise ValueError(f"Expected two state-preparation calls, found {len(prep)}")
        source = "\n".join(line for i, line in enumerate(lines) if i not in prep)
        circuit = qasm2.loads(source, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        circuit = transpile(circuit, basis_gates=["u3", "cx"],
                            qubits_initially_zero=False, optimization_level=3)
        qasm_out = out.with_suffix(".qasm")
        qasm_out.write_text(qasm2.dumps(circuit))
        print({"qasm": str(qasm_out), "depth": circuit.depth(),
               "cx": circuit.count_ops().get("cx", 0), "width": circuit.num_qubits})
