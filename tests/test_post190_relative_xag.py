from post190_relative_xag import (affine_library, build_reducer, reduce_mod_span,
                                  residual_search, residual_search_r2_exact)


def test_affine_library_and_zero_residual():
    full = (1 << 64) - 1
    lib = affine_library((1, 2))
    assert lib[0] and (1 ^ 2) in lib
    assert len(lib) == 8
    p = {'basis': (full, 1), 'goals': (1,), 'missing': ()}
    assert residual_search(p, max_products=0)['status'] == 'SAT'


def test_one_relative_and_shared_output():
    full = (1 << 64) - 1
    # Prefix contains a and b; both missing outputs are the same new product.
    p = {'basis': (full, 0xAAAAAAAAAAAAAAAA, 0xCCCCCCCCCCCCCCCC),
         'goals': (0x8888888888888888, 0x8888888888888888), 'missing': (0, 1)}
    r = residual_search(p, max_products=1, max_stages=1, seconds=5)
    assert r['status'] == 'SAT' and r['products'] == 1


def test_reducer_cosets_and_exact_library_rank():
    full = (1 << 64) - 1
    reducer = build_reducer((full, 0xAAAAAAAAAAAAAAAA))
    assert reduce_mod_span(0xAAAAAAAAAAAAAAAA ^ 0x1234, reducer) == reduce_mod_span(0x1234, reducer)
    assert len(affine_library((full, 0xAAAAAAAAAAAAAAAA))) == 4


def test_r2_dependent_product_is_found():
    full = (1 << 64) - 1
    a, b, c = (0xAAAAAAAAAAAAAAAA, 0xCCCCCCCCCCCCCCCC,
               0xF0F0F0F0F0F0F0F0)
    p = a & b
    # The second product depends on p and is needed to produce the goal.
    q = (a ^ p) & c
    prefix = {'basis': (full, a, b, c), 'goals': (p, q), 'missing': (0, 1)}
    r = residual_search_r2_exact(prefix, seconds=10)
    assert r['status'] == 'SAT'
