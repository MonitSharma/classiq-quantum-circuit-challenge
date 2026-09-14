# Verified 193-depth oracle

**193 depth / 857 CX / 18 qubits**, standalone `u3`/`cx` QASM.
SHA-256: `5c00b23d9ea061b8b3062caac17ae2de0ab8457a4705ecc3eea8c1eed49a1bec`.

This improves the protected 196 / 858 / 18 circuit by three layers and one CX.
It is not a sub-140 circuit or a verified leaderboard result. It has not been
submitted or cloud-resynthesized.

The class codes and loaders are unchanged. Reweighted linear programming on
the 182 reachable kernel inputs finds a 63-term phase representation instead
of 69 terms. A beam schedule followed by restoration up to an ancilla
permutation yields a **41-depth / 87-CX** kernel. The inverse loaders are
rewired consistently. Coordinates retain their original positions; all six
ancillas end at zero. The original 196 package is preserved.

**`kernel.qasm` alone is not diagonal.** It performs the phase and a physical
permutation. The uncomputation mapping in `kernel_recipe.json` is essential;
do not insert this kernel into the old symmetric builder unchanged.

`two_stage_193.qasm` is the complete oracle. `two_stage_193.qmod` matches all
1,640 serialized oracle gates exactly. Its `main` adds twelve preparation
Hadamards for the Classiq harness; those are absent from the standalone QASM.

Verification:

- All 4,096 basis inputs pass with a single shared global phase, maximum
  error 7.81e-15, zero ancilla error, discarded-amplitude bound 1.33e-14.
- The kernel coefficients round exactly to multiples of pi/32. Integer
  arithmetic verifies their required phases on all 182 reachable inputs.
- The kernel's phase-and-permutation action is checked independently.
- An independent rebuild reproduces the exact standalone QASM SHA.
- Five dense random superpositions pass, maximum error 2.01e-16, and eleven
  targeted tests pass.

Rebuild into a new directory:

```sh
.venv/bin/python src/build_two_stage_193.py --outdir artifacts/new_193_replay --verify
```

See `docs/POST193_RESEARCH.md` for the search scope and unsuccessful variants.
