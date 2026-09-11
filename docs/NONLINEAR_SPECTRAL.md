# Nonlinear spectral-conjugation campaign

Updated September 11, 2026. This is an exact structural screen, not a
quantum-circuit result. It was opened after the destructive-XAG campaign was
closed as a low-return circuit class.

## Hypothesis

For a reversible coordinate change `T`, write

```text
U = T† D_g T,       g(z) = logo(T⁻¹(z)).
```

The hope was that a shallow nonlinear triangular transform could make `g`
have a much cheaper diagonal Walsh/parity representation. The tested mutation
family is `z[target] ^= a(z) & b(z)`, where `a` and `b` are bounded-weight
affine parities that do not contain the target coordinate. This is an
invertible update for every fixed assignment of the other coordinates.

The implementation is [`src/nonlinear_spectral.py`](../src/nonlinear_spectral.py).

## Exact baseline and invariant

The target has 1,097 marked points. For a Boolean phase vector, the Walsh
numerator at mask `S` is

```text
W(S) = sum_z (-1)^g(z) (-1)^(S·z).
```

There are 1,097 negative terms and 2,999 positive terms, so every numerator
is odd. A reversible coordinate change only permutes the values of `g`, so
the same odd-population argument applies after `T`. Therefore every Walsh
coefficient is nonzero for every reversible coordinate permutation. This is an
exact obstruction to the proposed support-collapse criterion.

The exact baseline report is
[`artifacts/nonlinear_spectral_baseline.json`](../artifacts/nonlinear_spectral_baseline.json):

| Metric | Value |
|---|---:|
| Marked population | 1,097 |
| Walsh support | 4,096 / 4,096 |
| Nonconstant support | 4,095 / 4,095 |
| Weighted support | 24,576 |
| Participation of each input wire | 2,048 masks |
| Maximum absolute Walsh coefficient | 1,902 |
| Absolute mass of largest 32 coefficients | 16,772 |

The support and weighted-support values are combinatorial invariants once all
masks are nonzero, so they cannot be useful optimization objectives for an
exact reversible recoding.

## Bounded mutation screen

The exact screen sampled 256 random mutation chains at each requested length,
using seed 42 and affine control masks of weight at most two. Every candidate
was checked as a bijection and scored by an exact FWHT:

| Mutations | Walsh support | Weighted support | Best top-32 absolute mass |
|---:|---:|---:|---:|
| 1 | 4,096 | 24,576 | 17,264 |
| 2 | 4,096 | 24,576 | 17,284 |
| 3 | 4,096 | 24,576 | 17,120 |
| 4 | 4,096 | 24,576 | 17,084 |
| 6 | 4,096 | 24,576 | 16,776 |
| 8 | 4,096 | 24,576 | 16,868 |

The concentration values fluctuate, but none establishes a native parity
network advantage. No candidate was promoted to a circuit artifact.

## Disposition

Close ordinary Walsh-support sparsification by reversible recoding. A future
spectral effort would need a different object—such as a non-permutation
embedding, a multi-output phase representation, or a cost model based on
coefficient angles and shared reversible transport—not merely a deeper
triangular coordinate permutation.

This is not a lower bound on all quantum circuits and does not change the
protected exact fallback at depth 524 / CX 950.
