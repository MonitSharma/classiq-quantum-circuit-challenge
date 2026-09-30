"""Bounded Direct-E v3 prototype with selective historical CZ features."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

from direct_e_v2 import layout, mutate, semantic, structured_seed
from history_list_decoder import decode, phase_weight
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


def guided_mutate(layers: list[dict], rng: random.Random, guidance: list[int]) -> list[dict]:
    if not guidance:
        return mutate(layers, rng)
    proposed = [{"kind": layer["kind"], "gates": [list(g) for g in layer["gates"]]}
                for layer in layers]
    nonlinear = [i for i, layer in enumerate(proposed) if layer["kind"] == "ccx"]
    if not nonlinear:
        return mutate(layers, rng)
    layer_index = rng.choice(nonlinear)
    layer = proposed[layer_index]
    used = {wire for gate in layer["gates"] for wire in gate}
    free = [wire for wire in range(18) if wire not in used]
    if len(free) < 3:
        return mutate(layers, rng)
    wires = semantic(proposed[:layer_index])
    ranked = []
    for ai, a in enumerate(free):
        for b in free[ai + 1:]:
            product = wires[a] & wires[b]
            gain = phase_weight(TARGET) - phase_weight(TARGET ^ product)
            ranked.append((-gain, min((product ^ node).bit_count() for node in guidance), a, b))
    candidates = sorted(ranked)[:8]
    best = None
    for _, _, a, b in candidates:
        for target in free:
            if target in (a, b):
                continue
            candidate = [{"kind": item["kind"], "gates": [list(g) for g in item["gates"]]}
                         for item in proposed]
            candidate[layer_index]["gates"].append([a, b, target])
            key, _ = score(candidate, pair_limit=4)
            if best is None or key < best[0]:
                best = (key, candidate)
    return best[1] if best else mutate(layers, rng)


def run(out: Path, nonlin: int, affine: int, seconds: float, seed: int,
        pair_limit: int, preconditioner: Path | None = None,
        guidance_path: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    rng = random.Random(seed)
    guidance = []
    if guidance_path:
        nodes = json.loads(guidance_path.read_text())["nodes"]
        nodes.sort(key=lambda node: (not node["output_root"],
                                     -node["fanout"], node["layer"], node["signal_id"]))
        guidance = [int(node["truth_table"]) for node in nodes[:256]]
    layers = (structured_seed(nonlin, affine,
              json.loads(preconditioner.read_text())["substitution_ops"])
              if preconditioner else layout(nonlin, affine))
    current_key, current = score(layers, pair_limit)
    best_key, best = current_key, current
    best_layers = layers
    started = time.monotonic()
    iterations = 0
    while time.monotonic() - started < seconds:
        proposed = guided_mutate(layers, rng, guidance) if guidance else mutate(layers, rng)
        proposed_key, proposed_info = score(proposed, pair_limit)
        temperature = 1 + 8 * (1 - (iterations % 500) / 500)
        delta = (proposed_key[1] - current_key[1])
        if proposed_key < current_key or rng.random() < math.exp(-delta / temperature):
            layers, current_key, current = proposed, proposed_key, proposed_info
        if proposed_key < best_key:
            best_key, best, best_layers = proposed_key, proposed_info, proposed
            (out / "best.json").write_text(json.dumps({
                "iteration": iterations, "best_score": best_key,
                "decoder_distance": best["decoder_distance"],
                "historical_rank": best["historical_rank"],
                "feature_count": best["feature_count"],
                "layers": best_layers,
            }, indent=2) + "\n")
        iterations += 1
    result = {"status": "complete", "nonlin": nonlin, "affine": affine,
              "seed": seed, "seconds": time.monotonic() - started,
              "iterations": iterations, "pair_limit": pair_limit,
              "guidance": str(guidance_path) if guidance_path else None,
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
        from exhaustive_verify import exhaustive
        exhaustive(qasm_path)
        verification = json.loads(qasm_path.with_suffix(".exhaustive.json").read_text())
        result["qasm"] = str(qasm_path)
        result["verification"] = verification
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
    parser.add_argument("--guidance", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.outdir, args.nonlin, args.affine, args.seconds,
                         args.seed, args.pair_limit, args.preconditioner,
                         args.guidance), indent=2))


if __name__ == "__main__":
    main()
