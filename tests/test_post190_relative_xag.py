from post190_relative_xag import affine_library, residual_search


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
