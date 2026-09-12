# Verified distributed lookup oracle

**Depth 258 · CX 1188 · width 18.** No challenge submission has been made for
this package. The observed 183-depth leader has not been matched.

Use `distributed_level_258.qasm` as the authoritative standalone oracle and
`distributed_level_258.qmod` as its matching source companion. The QMOD oracle
function mirrors all QASM gates exactly; its `main` adds only the twelve
Hadamards used as a synthesis harness. Do not add those Hadamards to the QASM.

The exhaustive report checks all 4096 clean-ancilla input columns with one
shared global phase. The separate verification report uses independent dense
Aer simulations. `manifest.json` and `audit.json` record hashes and the
gate-for-gate QMOD comparison. The original notebook and earlier best QASMs
remain preserved elsewhere.

QASM SHA-256:

`b2a2e8ac6a6d7ee2c2e4ec11bcca4b4ba4fe54aab15b11c71236efcecdca3066`

Reproduce from the workspace root:

```sh
.venv/bin/python src/build_distributed_best.py --recipe artifacts/258/recipe.json --kernel artifacts/258/kernel.qasm --outdir /tmp/classiq_258_new --verify-components
.venv/bin/python src/exhaustive_verify.py /tmp/classiq_258_new/distributed_level_258.qasm
```

See `docs/DISTRIBUTED_LOOKUP_258.md` for the construction, proof, experiments,
limitations, and source map.

An executed companion notebook is available at
[`classiq-distributed-lookup-258.ipynb`](../../classiq-distributed-lookup-258.ipynb).
It checks the packaged result, rebuilds an identical QASM in a fresh temporary
directory, and reruns exhaustive verification.
