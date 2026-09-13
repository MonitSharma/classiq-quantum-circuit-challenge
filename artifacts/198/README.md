# Verified 198-depth oracle

`two_stage_198.qasm`: **198 depth / 858 CX / 18 qubits**, standalone U3/CX oracle.
SHA-256: `54502289740d096513f9a0df5556b9d990a2181bb28da8154959004566f29180`.

- The kernel was scheduled via beam search (`src/post218_beam_phase.py`), reducing the 8-wire diagonal kernel to **45 depth / 88 CX**.
- Combined with relative-phase encoders ($y$ seed 11, $x$ seed 155), the assembled circuit synthesizes down to **depth 198** with **858 CX**.
- All 4,096 coordinate basis inputs pass exhaustive check with one shared global phase, zero ancilla leakage, and maximum error 9.08e-15.
- Three independent dense random states pass with maximum error 2.51e-16 and ancilla leakage 6.35e-17.
- `two_stage_198.qmod` matches all 1,644 gates and parameters gate-for-gate. Its `main` adds twelve preparation Hadamards, which are absent from the standalone QASM.
