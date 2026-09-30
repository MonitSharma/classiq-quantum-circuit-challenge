import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qiskit import QuantumCircuit
import post190_interval_ripple as ir
import post190_rect_prefix as rp


def test_modular_blocks_exact():
    assert ir.check() == 0


def test_disk_predicate_on_every_assignment():
    body = QuantumCircuit(18)
    ir.guard(body); ir.add_t(body); ir.add_k(body); ir.inc_t(body); ir.compare(body)
    for v in range(32):
        for t in range(8):
            for y5 in (0, 1):
                for x5 in (0, 1):
                    out = ir.simulate(body, (v << 6) | (y5 << 11) | (t << 12) | (x5 << 5))
                    got = (not (out >> 16 & 1)) and bool(out >> 17 & 1)
                    c = 19 if not y5 else 9
                    assert got == (bool(x5) and t != 0 and c - t - 1 <= v <= c + t + 1)


def test_interval_block_restores_every_ancilla():
    q = ir.raw_interval()
    for v in range(0, 32, 3):
        for t in range(8):
            for y5 in (0, 1):
                s = (v << 6) | (y5 << 11) | (t << 12)
                assert ir.simulate(q, s) == s


def test_bound_cubes_cover_every_threshold():
    assert rp.check() == 0
