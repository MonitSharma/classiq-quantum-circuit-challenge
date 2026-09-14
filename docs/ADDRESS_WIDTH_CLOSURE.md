# The lookup must read all six address bits: a general closure

Protected best unchanged: **196 / 858 / 18**, `artifacts/196/`.

Address width is the strongest lever measured in this repository -- a three-output
lookup costs **77** layers at six address bits, **48** at five, **33** at four --
so narrowing it is worth far more than any scheduling gain. This file closes the
question for a four-wire descriptor, which is what an eight-wire kernel requires.

## The criterion

Split the coordinate as `z = (A, R)`: `k` address bits and a `(6-k)`-bit residual.
The most general four-wire descriptor available is

    D(z) = ( p address bits,  R' = f_A(R),  m clean lookup bits )

with `p + (6-k) + m = 4` and `m <= 3` clean ancillas. `f_A` may be a *different*
invertible map of the residual for every address, produced by the same lookup
that makes the clean bits and written in place on the dirty coordinate wires --
so no alignment is paid for before the lookup.

Inputs sharing an address always receive distinct descriptors, so only
different-address pairs can collide, and

    D(z) = D(z')  =>  class(z) = class(z')

holds exactly when any two addresses given the same code value have class
patterns over the residual that agree under some `f`. Agreement under a group of
maps is an equivalence relation, so the whole question becomes:

> **do the address patterns fall into at most `2^(p+m) = 2^(k-2)` equivalence
> classes?**

Nothing here requires inputs of the same class to share a descriptor; a class may
split across several codes.

## The answer, for every splitting

| k | residual | code budget | row side needs | column side needs |
|---:|---:|---:|---:|---:|
| 4 | 2 bits | 4 | **12** | **11** |
| 5 | 1 bit | 8 | **14** | **13** |
| 6 | none | 16 | 11 | 11 |

Only `k = 6` fits, and that is the current design. The four- and five-address
splittings miss by a factor of three and nearly two respectively -- not narrowly.

For a two-bit residual the maps were taken over the full affine group, and
`|AGL(2,2)| = 24 = 4!`, so **every** permutation of the four residual states was
allowed: this is the widest possible per-address re-pairing, and the counts do not
move (12 and 11 either way). Every choice of which wires form the address was
tried, both sides.

## What this closes

* Aligning the fibres with a pre-map before the lookup (`post196_prefold.py`,
  `post196_fiber_align.py`): affine alignment reaches 11-12 blocks against 8,
  short uncontrolled circuits do not reach 10 on the row side.
* Aligning them *inside* the lookup, by writing `R -> f_A(R)` onto the dirty
  coordinate wires as extra lookup outputs (`post196_dirty_descriptor.py`).
  This is strictly more general than the pre-map -- the re-pairing may vary per
  address -- and it fails by the same margin.
* Any combination: the criterion is stated on the descriptor, not on a
  construction, so it covers both at once.

Widening the descriptor to five wires does admit `k = 5` (13-15 classes against a
budget of 16), but the kernel then acts on ten wires with roughly 28 of 32
descriptor values used per side, leaving almost no don't-care freedom -- the
measured outcome of that regime was 711 kernel terms at 382 layers.

## How to screen the next idea

Any proposal that claims to narrow the lookup address must first pass:

```
patterns = post196_dirty_descriptor.patterns(classes, address_bits)
needed, _ = post196_dirty_descriptor.translation_classes(patterns, 6 - k)
assert needed <= 2 ** (k - 2)
```

That is a one-line test and it is where the last three routes died.
