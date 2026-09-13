# Classiq challenge optimization workspace

The objective is sub-180 depth and rank 1 in the [Classiq challenge](https://www.classiq.io/challenge). Work is unfinished. The lowest verified local depth is **218**, with **897 CX gates and 18 qubits**. The exact standalone U3/CX QASM passes all 4096 coordinate inputs, three dense-state checks, and an identical-hash replay. No rank-1 or sub-180 result is claimed.

Start with [the handoff](docs/HANDOFF.md), [experiment history](docs/EXPERIMENTS.md), and [current research](docs/POST221_RESEARCH.md). [AGENTS.md](AGENTS.md) records the essential correctness constraints. Historical results below remain preserved.

## Lowest verified depth

- [218-depth QASM](artifacts/218/two_stage_218.qasm)
- [Matching gate-level QMOD](artifacts/218/two_stage_218.qmod); its main adds preparation Hadamards, which are absent from the oracle QASM.
- [Exhaustive verification](artifacts/218/two_stage_218.exhaustive.json)
- [Dense-state verification](artifacts/218/two_stage_218.verification.json)
- [Package and replay recipe](artifacts/218/README.md)
- SHA-256 `3a685c32ea0d78637be1a575c91e6c7d13db0efdbf37a8f794fb44e7fb024a88`
- Method: parity-assisted class codes using y5 and x4 XOR x5, a 66-layer kernel, and relative-phase lookup boundaries.


## Historical protected 524-depth artifact

- Circuit: [artifacts/524/full_mux_feature_linear_tket_524.qasm](artifacts/524/full_mux_feature_linear_tket_524.qasm) — depth 524, CX 950
- Exhaustive verification: [artifacts/524/full_mux_feature_linear_tket_524.exhaustive.json](artifacts/524/full_mux_feature_linear_tket_524.exhaustive.json)
- Superseded predecessor: [artifacts/tket_FullPeephole.qasm](artifacts/tket_FullPeephole.qasm) — depth 531, CX 1020
- Provenance: [src/full_mux.py](src/full_mux.py) seed 94 (depth 536, still verified as
  [artifacts/full_mux.qasm](artifacts/full_mux.qasm)), then pytket `FullPeepholeOptimise`
  and a rebase to exact `u3`/`cx`
- The protected result is an affine six-feature `full_mux` construction, followed by
  pytket post-processing and exact `u3`/`cx` serialization.
- Original notebook: [classiq-challenge-baseline (1).ipynb](classiq-challenge-baseline%20%281%29.ipynb)

The exact protected QASM SHA-256 is `7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`. The matching logical QMOD is packaged at `artifacts/524/full_mux_feature_linear_tket_524.qmod`.

Earlier architecture closure statements are historical; the verified 258-to-224 improvements supersede broad claims that distributed lookup cannot improve. Detailed methods, measurements, and failure reasons
are indexed in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Verify locally

Run from this directory:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/exhaustive_verify.py artifacts/218/two_stage_218.qasm
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/verify.py artifacts/218/two_stage_218.qasm 3
```

The packaged reports record successful exhaustive checking on all 4,096 inputs and dense random-state checks. Neither command submits anything.

Do not assume every QASM under `artifacts/` is valid. Several older experimental circuits were invalid because of a compiler initialization assumption. Read the handoff before reusing them.
