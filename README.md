# Classiq challenge optimization workspace

The objective is to reach rank 1 in the [Classiq challenge](https://www.classiq.io/challenge). Work is unfinished: the best locally verified circuit has **depth 531, 1,020 CX gates, and 18 qubits**. The last observed leader had depth 291. Nothing has been submitted, and no rank has been obtained or guaranteed.

Handoff updated September 8, 2026 (Asia/Singapore), second continuation. Start with [the handoff](docs/HANDOFF.md), then read [the experiment history](docs/EXPERIMENTS.md) and [the current design](docs/CURRENT_DESIGN.md). [AGENTS.md](AGENTS.md) records essential correctness constraints for a new agent.

## Best artifact

- Circuit: [artifacts/tket_FullPeephole.qasm](artifacts/tket_FullPeephole.qasm) — depth 531, CX 1020
- Exhaustive verification: [artifacts/tket_FullPeephole.exhaustive.json](artifacts/tket_FullPeephole.exhaustive.json)
- Provenance: [src/full_mux.py](src/full_mux.py) seed 94 (depth 536, still verified as
  [artifacts/full_mux.qasm](artifacts/full_mux.qasm)), then pytket `FullPeepholeOptimise`
  and a rebase to exact `u3`/`cx`
- Original notebook: [classiq-challenge-baseline (1).ipynb](classiq-challenge-baseline%20%281%29.ipynb)

Packaged submission artifacts are in [artifacts/531](artifacts/531):
`full_mux_531.qasm`, its matching exhaustive report, and the companion
`full_mux_531.qmod` logical oracle model.

The exact verified QASM SHA-256 is `8f7e2617cf1435ea76cc70688544b4b0e3a8b5082d82293f98777d90d5a3fda6` (the depth-536 predecessor is `93857f2dac80456feaf9c97ac464ee382eb532d8efe87e3622689103223683f0`). The matching logical QMOD is packaged at `artifacts/531/full_mux_531.qmod`; it is not expected to synthesize back to the exact optimized QASM.

## Verify locally

Run from this directory:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/exhaustive_verify.py artifacts/tket_FullPeephole.qasm
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/verify.py artifacts/full_mux.qasm 5
```

The first command was completed successfully on all 4,096 basis inputs. The second is an additional dense random-state cross-check; it has not yet been run on this best artifact. Neither command submits anything.

Do not assume every QASM under `artifacts/` is valid. Several older experimental circuits were invalid because of a compiler initialization assumption. Read the handoff before reusing them.
