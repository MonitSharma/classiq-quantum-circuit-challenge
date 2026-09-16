"""Order-sensitive list decoding for a historical GF(2) phase span."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class DecodeResult:
    residual: int
    distance: int
    beam_width: int
    order_name: str
    processed: int


def decode(target: int, signals: Sequence[int], width: int = 64,
           order_name: str = "given") -> DecodeResult:
    """Keep the best unique residuals while processing independent signals."""
    if width < 1:
        raise ValueError("width must be positive")
    beam = {target}
    for signal in signals:
        expanded = beam | {residual ^ signal for residual in beam}
        beam = set(sorted(expanded, key=int.bit_count)[:width])
    residual = min(beam, key=lambda value: min(value.bit_count(),
                                               4096 - value.bit_count()))
    distance = min(residual.bit_count(), 4096 - residual.bit_count())
    return DecodeResult(residual, distance, width, order_name,
                        len(signals))


def signal_orders(values: Sequence[int], seed: int = 1609) -> list[tuple[str, list[int]]]:
    orders = [("given", list(values)),
              ("reverse", list(reversed(values))),
              ("correlation", sorted(values, key=lambda v: v.bit_count(), reverse=True))]
    rng = random.Random(seed)
    for index in range(8):
        order = list(values)
        rng.shuffle(order)
        orders.append((f"shuffle_{index:02d}", order))
    return orders


def calibrate(target: int, values: Iterable[int], widths=(64, 512, 1024)) -> list[dict]:
    values = list(values)
    rows = []
    for order_name, ordered in signal_orders(values):
        for width in widths:
            result = decode(target, ordered, width, order_name)
            rows.append({"order": result.order_name, "width": result.beam_width,
                         "signals": result.processed, "distance": result.distance,
                         "residual_weight": result.distance})
    return rows
