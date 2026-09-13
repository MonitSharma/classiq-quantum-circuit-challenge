# Verified 196-depth oracle

`two_stage_196.qasm`: **196 depth / 858 CX / 18 qubits**, standalone U3/CX oracle.
SHA-256: `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`.

The architecture is unchanged from `artifacts/218`: two relative-phase loaders in
parallel, one eight-wire diagonal kernel, then the inverse loaders. The class
codes and the integer phase lift are byte-for-byte the ones recorded there
(`class_codes.json` is copied from that package).

What changed is the kernel schedule. `src/post218_beam_phase.py` replaces the
one-layer greedy of `post258_kernel_schedule.synth` with a beam search ranked by
an exact potential — the total coordinate weight of the outstanding parities,
whose change under `CX(a, b)` is `n_b - 2 M[a][b]` for the coordinate
coincidence matrix `M`. The same 69-term phase polynomial now compiles to
**43 depth / 89 CX** instead of 66 / 123. Re-selecting the encoder seeds against
the new kernel (y seed 99, x seed 155) gives the remaining layers.

| | 218 package | this package |
|---|---|---|
| kernel | 66 / 123 | **43 / 89** |
| loaders (each) | 77 | 77 |
| oracle | 218 / 897 | **196 / 858** |

## Verification

* All 4096 coordinate basis inputs pass with one shared global phase, maximum
  error 9.03e-15, zero ancilla error (`two_stage_196.exhaustive.json`).
* Five independent dense random states supported on all 4096 coordinates pass,
  maximum error 2.54e-16 (`two_stage_196.verification.json`).
* The kernel is checked against `diag(exp(i * phases))` up to global phase
  before assembly; that check is inside the build script and fails the build.
* `two_stage_196.qmod` matches all 1647 serialized gates and parameters. Its
  `main` adds twelve preparation Hadamards, which are absent from the QASM.

## Replay

From the workspace root, into a fresh directory:

```sh
.venv/bin/python src/build_two_stage_196.py --outdir /tmp/classiq_196_fresh --verify
```

The rebuild is deterministic and reproduces the SHA above.

## Limitations

Sub-180 and rank one remain unresolved; this is an intermediate result. The
loader is now the whole cost (77 + 43 + 77 with almost no cross-boundary
merging), and `docs/POST218_RESEARCH.md` records two independent arguments that
77 is close to optimal for a three-bit, six-address-bit lookup on nine wires,
together with the code and architecture variants that were tried and failed.
Neither cloud resynthesis nor challenge submission has been performed.
