"""The extended search must retain terms above bit 63 in counting and hashing."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_extended_phase_bitset_and_hash(tmp_path):
    compiler = shutil.which('cc')
    if compiler is None:
        pytest.skip('C compiler unavailable')
    source = tmp_path / 'check.c'
    engine = ROOT / 'src/post151_sa/kbeam128.c'
    source.write_text(f'''
#define main beam_main
#include "{engine}"
#undef main
#include <assert.h>
int main(void) {{
    assert(popc64(~(__uint128_t)0) == 128);
    for (int k = 0; k < 128; ++k) {{
        __uint128_t bit = ((__uint128_t)1) << k;
        assert(popc64(bit) == 1);
        assert((bit >> k) == 1);
    }}
    MODE = 4;
    S a = {{0}}, b = {{0}};
    a.done = 7;
    b.done = a.done | (((__uint128_t)1) << 100);
    assert(hstate(&a) != hstate(&b));
    assert(popc64(b.done) == 4);
    assert((b.done >> 100) & 1);
    return 0;
}}
''')
    binary = tmp_path / 'check'
    subprocess.run([compiler, '-O1', str(source), '-o', str(binary)],
                   check=True, capture_output=True)
    subprocess.run([str(binary)], check=True)
