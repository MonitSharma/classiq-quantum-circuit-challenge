"""Bounded Direct-E v3 prototype with selective historical CZ features."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

from direct_e_v2 import layout, mutate, structured_seed
from history_list_decoder import decode
from phase_features import collect_features, feature_taps
from phase_history_search import ALL_ONES, TARGET, compile_u3_cx, build_phase_history_circuit


ROOT = Path(__file__).resolve().parents[1]


def score(layers: list[dict], pair_limit: int) -> tuple[tuple, dict]:
    gates = []
    for layer in layers:
        kind = {"ccx": "rccx"}.get(layer["kind"], layer["kind"])
        gates.append(("layer", tuple((kind, *gate) for gate in layer["gates"])))
    basis, metadata, _ = collect_features(gates, pair_limit=pair_limit)
    solution = basis.solve(TARGET)
    taps = feature_taps(basis, metadata)
    independent = [reduced for _, (reduced, _) in sorted(basis.pivots.items())
                   if reduced != ALL_ONES]
    decoded = decode(TARGET, independent, width=64,
                     order_name="pivot").distance
    key = (0 if solution is not None else 1, decoded, -basis.rank, len(metadata))
    return key, {"basis": basis, "metadata": metadata, "taps": taps,
                 "historical_rank": basis.rank, "feature_count": len(metadata),
                 "decoder_distance": decoded, "exact": solution is not None}


def run(out: Path, nonlin: int, affine: int, seconds: float, seed: int,
        pair_limit: int, preconditioner: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    rng = random.Random(seed)
    layers = (structured_seed(nonlin, affine,
              json.loads(preconditioner.read_text())["substitution_ops"])
              if preconditioner else layout(nonlin, affine))
    current_key, current = score(layers, pair_limit)
    best_key, best = current_key, current
    best_layers = layers
    started = time.monotonic()
    iterations = 0
    while time.monotonic() - started < seconds:
        proposed = mutate(layers, rng)
        proposed_key, proposed_info = score(proposed, pair_limit)
        temperature = 1 + 8 * (1 - (iterations % 500) / 500)
        delta = (proposed_key[1] - current_key[1])
        if proposed_key < current_key or rng.random() < math.exp(-delta / temperature):
            layers, current_key, current = proposed, proposed_key, proposed_info
        if proposed_key < best_key:
            best_key, best, best_layers = proposed_key, proposed_info, proposed
        iterations += 1
    result = {"status": "complete", "nonlin": nonlin, "affine": affine,
              "seed": seed, "seconds": time.monotonic() - started,
              "iterations": iterations, "pair_limit": pair_limit,
              "best_score": best_key, "historical_rank": best["historical_rank"],
              "feature_count": best["feature_count"], "exact": best["exact"]}
    if best["exact"]:
        history_gates = tuple(
            ("layer", tuple(
                ({"ccx": "rccx"}.get(layer["kind"], layer["kind"]), *gate)
                for gate in layer["gates"]
            ))
            for layer in best_layers
        )
        circuit = compile_u3_cx(build_phase_history_circuit(
            history_gates, best["taps"], 18
        ))
        qasm_path = out / f"direct_v3_d{circuit.depth()}_cx{circuit.count_ops().get('cx', 0)}.qasm"
        from qiskit import qasm2
        qasm_path.write_text(qasm2.dumps(circuit))
        result["qasm"] = str(qasm_path)
    (out / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--nonlin", type=int, default=7)
    parser.add_argument("--affine", type=int, default=18)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--seed", type=int, default=26185)
    parser.add_argument("--pair-limit", type=int, default=8)
    parser.add_argument("--preconditioner", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.outdir, args.nonlin, args.affine, args.seconds,
                         args.seed, args.pair_limit, args.preconditioner), indent=2))


if __name__ == "__main__":
    main()
