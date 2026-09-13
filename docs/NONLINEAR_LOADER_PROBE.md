# Nonlinear coordinate preconditioning: measured negative result

The verified best remains **196 depth / 858 CX / 18 qubits**. Neither sub-140,
sub-100 nor rank one was achieved in this experiment.

Instead of changing the kernel or repeating the CNOT-basis search, this probe
applies reversible nonlinear changes to the coordinate registers before loading
the existing class codes. The changes remain in place through the kernel. Its
raw coordinate tag is protected, and the actual encoder inverse restores all
coordinates and cancels the RCCX gates' input-dependent phases afterward.
Thus there is no unnecessary restoration of the coordinates between loader and
kernel. The existing 43-layer kernel is unchanged.

`src/post196_nonlinear_loader_search.py` screens positive and negative control
Toffolis with targets outside the protected tag. It screens 6,061 distinct row
tables and 5,946 column tables through three gates, retaining a beam of 16
after each level. It ranks them by the existing frame lower bound plus a
heuristic seven-layer charge per added gate. This charge is **not a bound**.
Sixteen sequences per side receive native compilation: six scheduler seeds,
two walk constructions, then two shortlisted native schedules per sequence.
Every retained native loader passes all 64 input mappings, allowing its
removable input phase. Sixteen combinations of the best loaders are compiled
as complete circuits.

| Measurement | Existing circuit | Best new candidate |
|---|---:|---:|
| Row encoder depth | 77 | 81 |
| Column encoder depth | 77 | 81 |
| Complete oracle depth | 196 | 204 |
| Complete CX count | 858 | 891 |
| Width | 18 | 18 |

The best frame bound remained 77 at each searched level before charging the
preconditioning gates. Some spectra became sparser, but the compiled circuits
did not become shallower. This is evidence against the tested inexpensive
preconditioners for the current codes, not an impossibility proof for nonlinear
encoders, other codes, or a different oracle construction. The shortlist did
not compile every screened table or every three-gate sequence.

The serialized experimental circuit is
`artifacts/post196_nonlinear_loaders_v2/nonimproving_d204_cx891.qasm`, SHA
`fbcf17cc30a0251f415f0277df090c102c07ca06ab26a46b56c0ae365c479fd4`.
`src/exhaustive_verify.py` checked all 4,096 basis inputs with one common global
phase: maximum error 9.51e-15, zero ancilla error, discarded-amplitude bound
1.18e-14. It is a correct **non-improving** experiment, not a recommended
submission. The protected 196 QASM was not changed.

Reproduce the search using a new output directory:

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python \
  src/post196_nonlinear_loader_search.py --outdir artifacts/new_nonlinear_probe
```

The initial v1 run stopped at an incompatible sparse/open-walk flag combination
before producing compiled results. V2 fixes the flags. It is the completed run;
there are no optimization jobs left running.

The latest side analysis also does not close all three-bit radius/mode hybrids.
An encoding can reserve unused radius patterns for modes: radius codes 2,4,6,7
in the lower half, 2,4,5 in the upper half, code 1 for empty rows, code 3 for
rectangle-only rows, and code 0 for the lower radius-eight exception or upper
bridge rows. The retained y5 distinguishes those two uses of zero. Such a code
needs decoding and exception handling; this observation supplies no cheap
complete middle or sub-140 construction. A collision when all modes are forced
to literal radius zero establishes a limitation of that encoding only.
