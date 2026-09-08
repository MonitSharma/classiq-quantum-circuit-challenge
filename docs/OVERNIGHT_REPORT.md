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
- Bounded exact Z3 min-MC XAG synthesis: 29/30 unique factors independently verified; the three-ancilla side compiler produced only one complete Pareto pair at 139/215.
- Pebble-friendly chain-XAG synthesis: 29/30 factors solved, but only 5/10, 4/10, and 5/10 complete pairs compiled for the three tested bases; partial depth sums were 771, 744, and 793.
- An 80-step actual-cost GL(10,2) search found no basis improvement: best scores were 779/736, 795/754, and 803/751.
- Direct dirty-input ESOP/MCX pair compilation passed exhaustive verification but measured 2156 depth / 1346 CX / width 18.
- Exact 4096-term Walsh phase polynomial with GraySynth measured 8168 depth / 4094 CX / width 12; negative.
- QROM-tree radius oracle passed exhaustive verification but measured 777 depth / 606 CX / width 18; negative.
- GraySynth section-size sweep (`1,2,3,4,6,12`) reproduced 8168 depth / 4094 CX for every setting; negative.
- Berkeley ABC AIG flows remained at 224–247 AND nodes and levels 17–22; no compact reversible computation graph was exposed.
- Shared delta-stream schedule: 2183 depth / 1649 CX; negative.
- Shared XAG, joint pair sharing, retained-factor schedules, quadrant-rank compilation, and direct quadrant phase controls: all correct where accepted, but substantially worse than 531.
- PyZX extraction: 2655 depth / 3022 CX; negative.
- Classiq native rank model: QMOD generation succeeded, but synthesis stopped before an API task because macOS keychain authentication returned `KeyringError (-50)`.
- Qiskit and pytket cleanup variants, including FullPeephole, RemoveRedundancies, PeepholeOptimise2Q, ContextSimp, and CommuteThroughMultis: reproduced 531/1020 and produced no improvement.
- BDD cofactor mining found 109 distinct nonconstant nodes; 64 support-6-or-smaller cofactors were scored, with the cheapest nontrivial feature at 11 depth / 5 CX.
- Flattening the BDD into a 77-cube ESOP scored 2239 depth / 1508 CX. A direct reversible Shannon evaluator exceeded the clean-ancilla budget; a corrected dirty-input evaluator fit width 18 but scored 3,949,563 depth / 2,581,968 CX.

Detailed machine-readable results are in `artifacts/overnight_progress.jsonl`.

## Interpretation

The evidence rules out more algebraic-basis tuning, generic global cleanup, direct BDD evaluation, and the current independently synthesized pair/XAG compiler as the next high-value move. The remaining credible route is a genuinely new reversible primitive: a multi-output dirty-ancilla/QROM or phase synthesis method that removes repeated load/unload work while explicitly optimizing ancilla lifetime and serialized depth. The native Classiq synthesis attempt remains blocked by `KeyringError (-50, 'Unknown Error')`; no credentials were changed or repeatedly retried.

The overnight agent should therefore stop recycling the rejected architectures, preserve the 531 fallback, and only accept a new result after exact U3/CX serialization plus exhaustive verification and SHA matching.
