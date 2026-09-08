# Overnight optimization report

## Verified local best

The protected local best remains `artifacts/531/full_mux_531.qasm`:

- depth: **531**
- CX: **1020**
- width: **18**
- SHA-256: `8f7e2617cf1435ea76cc70688544b4b0e3a8b5082d82293f98777d90d5a3fda6`
- exhaustive verification: all 4096 clean-ancilla basis inputs; zero ancilla leakage

No candidate beat this result. No circuit was submitted to the external challenge.

## Experiments completed

- Actual compiled pair-basis search, including a fresh 60-step seed: no improvement; trusted pair result remained 779/736.
- Shared delta-stream schedule: 2183 depth / 1649 CX; negative.
- Shared XAG, joint pair sharing, retained-factor schedules, quadrant-rank compilation, and direct quadrant phase controls: all correct where accepted, but substantially worse than 531.
- PyZX extraction: 2655 depth / 3022 CX; negative.
- Classiq native rank model: QMOD generation succeeded, but synthesis stopped before an API task because macOS keychain authentication returned `KeyringError (-50)`.
- Qiskit and pytket cleanup variants, including FullPeephole, RemoveRedundancies, PeepholeOptimise2Q, ContextSimp, and CommuteThroughMultis: reproduced 531/1020 and produced no improvement.
- BDD cofactor mining found 109 distinct nonconstant nodes; 64 support-6-or-smaller cofactors were scored, with the cheapest nontrivial feature at 11 depth / 5 CX.
- Flattening the BDD into a 77-cube ESOP scored 2239 depth / 1508 CX. A direct reversible Shannon evaluator exceeded the clean-ancilla budget; a corrected dirty-input evaluator fit width 18 but scored 3,949,563 depth / 2,581,968 CX.

Detailed machine-readable results are in `artifacts/overnight_progress.jsonl`.

## Interpretation

The evidence rules out more algebraic-basis tuning, generic global cleanup, direct BDD evaluation, and the current independently synthesized pair/XAG compiler as the next high-value move. The remaining credible route is a genuinely new reversible primitive: a multi-output dirty-ancilla/QROM or phase synthesis method that removes repeated load/unload work while explicitly optimizing ancilla lifetime and serialized depth.

The overnight agent should therefore stop recycling the rejected architectures, preserve the 531 fallback, and only accept a new result after exact U3/CX serialization plus exhaustive verification and SHA matching.
