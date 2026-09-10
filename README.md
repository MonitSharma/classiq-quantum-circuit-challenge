# Classiq challenge optimization workspace

The objective is to reach rank 1 in the [Classiq challenge](https://www.classiq.io/challenge). Work is unfinished: the protected best locally verified circuit has **depth 524, 950 CX gates, and 18 qubits**. No rank-1 claim is made.

Handoff updated September 10, 2026 (Asia/Singapore). Start with [the handoff](docs/HANDOFF.md), then read [the experiment history](docs/EXPERIMENTS.md) and [the current design](docs/CURRENT_DESIGN.md). [AGENTS.md](AGENTS.md) records essential correctness constraints for a new agent.

## Best protected artifact

- Circuit: [artifacts/524/full_mux_feature_linear_tket_524.qasm](artifacts/524/full_mux_feature_linear_tket_524.qasm) — depth 524, CX 950
- Exhaustive verification: [artifacts/524/full_mux_feature_linear_tket_524.exhaustive.json](artifacts/524/full_mux_feature_linear_tket_524.exhaustive.json)
- Provenance: affine six-feature `full_mux` construction, then pytket post-processing and exact `u3`/`cx` serialization
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

The first command was completed successfully on all 4,096 basis inputs. Neither command submits anything.

Do not assume every QASM under `artifacts/` is valid. Several older experimental circuits were invalid because of a compiler initialization assumption. Read the handoff before reusing them.
