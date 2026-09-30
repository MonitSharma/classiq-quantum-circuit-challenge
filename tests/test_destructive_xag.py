from pathlib import Path

from destructive_xag import (
    load_xag,
    one_signal_register_pressure,
    signal_last_use,
    output_nodes,
)
from destructive_xag_rank import rank_profile
from destructive_xag_scheduler import prepare, search
from destructive_dirty_search import canonical_span, prepare_products, search as dirty_search


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


def test_affine_live_rank_profile_is_exact_and_over_capacity():
    report = rank_profile(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    assert report["exact"]
    assert report["maximum_naive_live_count"] == 33
    assert report["maximum_affine_rank_including_constant"] == 34
    assert not report["affine_packing_alone_fits_current_order"]


def test_rank_constrained_scheduler_never_exceeds_18_wires():
    prepared = prepare(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    result = search(prepared, budget=0, beam_width=10)
    assert result["maximum_rank"] <= 19
    assert result["exact_semantic_verification"]
    assert not result["impossibility_proof"]


def test_dirty_span_starts_with_twelve_input_dimensions():
    initial, _, _, _ = prepare_products(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    assert len(initial.basis) == 12
    assert len(canonical_span(list(initial.basis) + [0])) == 12


def test_dirty_span_search_is_rank_constrained():
    result = dirty_search(ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag", beam_width=2, max_evaluations=2)
    assert result["maximum_affine_rank_including_constant"] <= 19
    assert result["exact_semantic_verification"]
