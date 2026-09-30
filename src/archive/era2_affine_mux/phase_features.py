"""Selective historical Z/CZ phase features for destructive trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from phase_history_search import ALL_ONES, HistoricalBasis, TARGET, rank_factor_hints, rank_product_hints, replay_history


@dataclass(frozen=True)
class Feature:
    kind: str
    step: int
    wire: int
    other_wire: int | None
    value: int


def collect_features(gates: Sequence[tuple], pair_limit: int = 8,
                     target: int = TARGET) -> tuple[HistoricalBasis, dict[int, list[Feature]], list[tuple[int, ...]]]:
    """Collect all historical Z features and a selective CZ dictionary."""
    _, _, snapshots = replay_history(gates)
    basis = HistoricalBasis()
    metadata: dict[int, list[Feature]] = {}
    hints = rank_product_hints() + rank_factor_hints()
    for step, wires in enumerate(snapshots):
        for wire, value in enumerate(wires):
            signal_id = basis.add(value, step, wire, "z")
            metadata.setdefault(signal_id, []).append(Feature("z", step, wire, None, value))
        candidates = []
        for a in range(len(wires)):
            for b in range(a + 1, len(wires)):
                value = wires[a] & wires[b]
                if not value:
                    continue
                hint_distance = min((value ^ hint).bit_count() for hint in hints) if hints else 0
                target_distance = min((value ^ target).bit_count(), (value ^ (target ^ ALL_ONES)).bit_count())
                exact_hint = int(value in hints)
                candidates.append((-exact_hint, hint_distance, target_distance, a, b, value))
        ranked = sorted(candidates)
        exact = [row for row in ranked if row[0] == 0]
        approximate = [row for row in ranked if row[0] != 0][:pair_limit]
        for _, _, _, a, b, value in exact + approximate:
            signal_id = basis.add(value, step, a, f"cz:{a}:{b}")
            metadata.setdefault(signal_id, []).append(Feature("cz", step, a, b, value))
    return basis, metadata, snapshots


def feature_taps(basis: HistoricalBasis, metadata: dict[int, list[Feature]], target: int = TARGET) -> list[dict] | None:
    solution = basis.solve(target)
    if solution is None:
        return None
    mask, _ = solution
    taps = []
    for signal_id, occurrences in metadata.items():
        if mask & (1 << signal_id):
            feature = min(occurrences, key=lambda item: (item.kind != "z", item.step, item.wire, item.other_wire or -1))
            taps.append({"kind": feature.kind, "step": feature.step,
                         "wire": feature.wire, "other_wire": feature.other_wire,
                         "signal_id": signal_id})
    return taps
