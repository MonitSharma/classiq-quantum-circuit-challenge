# Classiq challenge optimization workspace

The objective is to reach rank 1 in the [Classiq challenge](https://www.classiq.io/challenge). Work is unfinished: the best locally verified circuit has **depth 536, 1,020 CX gates, and 18 qubits**. The last observed leader had depth 291. Nothing has been submitted, and no rank has been obtained or guaranteed.

Handoff updated September 8, 2026 (Asia/Singapore). Start with [the handoff](docs/HANDOFF.md), then read [the experiment history](docs/EXPERIMENTS.md) and [the current design](docs/CURRENT_DESIGN.md). [AGENTS.md](AGENTS.md) records essential correctness constraints for a new agent.

## Best artifact

- Circuit: [artifacts/full_mux.qasm](artifacts/full_mux.qasm)
- Exhaustive verification: [artifacts/full_mux.exhaustive.json](artifacts/full_mux.exhaustive.json)
- Generator: [src/full_mux.py](src/full_mux.py), seed 94
- Original notebook: [classiq-challenge-baseline (1).ipynb](classiq-challenge-baseline%20%281%29.ipynb)

The exact verified QASM SHA-256 is `93857f2dac80456feaf9c97ac464ee382eb532d8efe87e3622689103223683f0`. Existing QMOD files describe earlier experiments; **there is not yet a matching submission-ready QMOD for this best circuit**.

## Verify locally

Run from this directory:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/exhaustive_verify.py artifacts/full_mux.qasm
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/verify.py artifacts/full_mux.qasm 5
```

The first command was completed successfully on all 4,096 basis inputs. The second is an additional dense random-state cross-check; it has not yet been run on this best artifact. Neither command submits anything.

Do not assume every QASM under `artifacts/` is valid. Several older experimental circuits were invalid because of a compiler initialization assumption. Read the handoff before reusing them.
