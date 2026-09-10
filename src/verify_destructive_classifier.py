"""Verify a semantic destructive classifier gate-history JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from destructive_semantic_search import (
    TARGET,
    apply_biaffine_semantic,
    apply_cx_semantic,
    apply_rccx_semantic,
    apply_x_semantic,
    initial_wire_truth_tables,
)


def verify(path: str) -> dict:
    payload = json.loads(Path(path).read_text())
    wires = initial_wire_truth_tables()
    for gate in payload["gates"]:
        kind = gate[0]
        if kind == "biaffine":
            _, a, mix_a, b, mix_b, target = gate
            wires = apply_biaffine_semantic(
                wires, a, mix_a, b, mix_b, target
            )
            continue
        _, a, b, target = gate
        if kind == "x":
            wires = apply_x_semantic(wires, a)
        elif kind == "cx":
            wires = apply_cx_semantic(wires, a, b)
        elif kind == "rccx":
            wires = apply_rccx_semantic(wires, a, b, target)
        else:
            raise ValueError(kind)
    target_wire = payload.get("target_wire", 12)
    mismatches = (wires[target_wire] ^ TARGET).bit_count()
    result = {
        "states_checked": 4096,
        "marked_states": TARGET.bit_count(),
        "target_wire": target_wire,
        "mismatches": mismatches,
        "semantic_hash": payload.get("semantic_hash"),
        "verified": mismatches == 0,
    }
    print(json.dumps(result, indent=2))
    if mismatches:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    verify(parser.parse_args().path)
