# Classiq challenge optimization workspace

The objective is to reach rank 1 in the [Classiq challenge](https://www.classiq.io/challenge). Work is unfinished. The lowest verified **depth** is now **456** (CX 1140, 18 qubits) from the level/comparator architecture in [docs/LEVEL_COMPARATOR.md](docs/LEVEL_COMPARATOR.md); the lowest verified **CX count** remains the protected **depth 524, 950 CX** artifact. The live page refreshed September 11, 2026 showed Hyun-Jung K. at 183 / 789, with depth primary and CX as the tie-breaker. Nothing has been submitted, and no rank-1 claim is made. See the [research review](docs/RESEARCH_REVIEW_2026-09-09.md) for the repository audit and prior experiments.

Handoff updated September 10, 2026 (Asia/Singapore). Start with [the handoff](docs/HANDOFF.md), then read [the experiment history](docs/EXPERIMENTS.md) and [the current design](docs/CURRENT_DESIGN.md). [AGENTS.md](AGENTS.md) records essential correctness constraints for a new agent.

## Lowest verified depth

- Circuit: [artifacts/456/level_merged_456.qasm](artifacts/456/level_merged_456.qasm) — depth 456, CX 1140, width 18
- Exhaustive verification: [artifacts/456/level_merged_456.exhaustive.json](artifacts/456/level_merged_456.exhaustive.json)
- SHA-256 `8e997e511d9fb043ad82896a7c873f5c3a1cca4cde0cce7bf5df5cba6c6c6e7c`
- Source: [src/level_oracle.py](src/level_oracle.py), `build_merged`
- Method: `logo(x,y) = [u1(y)+v1(x) >= 6] XOR [u2(y)+v2(x) >= 6]`, two three-bit
  level comparisons. See [docs/LEVEL_COMPARATOR.md](docs/LEVEL_COMPARATOR.md).
- It does **not** supersede the 524 artifact on CX count, so both are kept.

## Best protected artifact

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

The six-feature UCR load/phase/unload architecture is formally closed for
competition optimization. Detailed methods, measurements, and failure reasons
are indexed in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Verify locally

Run from this directory:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/exhaustive_verify.py artifacts/524/full_mux_feature_linear_tket_524.qasm
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/verify.py artifacts/524/full_mux_feature_linear_tket_524.qasm 5
```

The packaged reports record successful exhaustive checking on all 4,096 inputs and dense random-state checks. Neither command submits anything.

Do not assume every QASM under `artifacts/` is valid. Several older experimental circuits were invalid because of a compiler initialization assumption. Read the handoff before reusing them.
