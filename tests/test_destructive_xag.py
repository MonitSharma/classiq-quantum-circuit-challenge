from pathlib import Path

from destructive_xag import (
    load_xag,
    one_signal_register_pressure,
    signal_last_use,
    output_nodes,
)


ROOT = Path(__file__).resolve().parents[1]


def test_original_coordinate_seed_is_exact():
    parsed = load_xag(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    assert len(parsed.nodes) == 97
    assert parsed.graph.exact()
    assert len(output_nodes(parsed)) == 10


def test_last_use_is_topological():
    parsed = load_xag(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    last = signal_last_use(parsed)
    assert len(last) == 110
    assert all(value >= 0 for value in last)


def test_one_signal_allocator_fails_before_quantum_lowering():
    parsed = load_xag(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    report = one_signal_register_pressure(parsed, beam_width=1000)
    assert report["minimum_observed_peak_registers"] == 22
    assert not report["fits_reserved_predicate_register"]
