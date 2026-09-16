"""Audit saved Direct-E trajectories against the existing history engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase_history_search import TARGET, replay_history


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINTS = (
    "artifacts/direct_e_v2_n6_a26_s16185/best.json",
    "artifacts/direct_e_v2_n7_a19_s16186/best.json",
    "artifacts/direct_e_v2_n7_a18_s16188/best.json",
    "artifacts/direct_e_v2_n8_a12_s16187/best.json",
    "artifacts/direct_e_v2_seeded_n6_a26_s26186/best.json",
    "artifacts/direct_e_v2_seeded_n7_a18_s26185/best.json",
    "artifacts/direct_e_v2_seeded_n8_a12_s26187/best.json",
    "artifacts/direct_e_v2_greedy_control_n7_a18_s26185/best.json",
)


def as_history_layers(records: list[dict]) -> tuple[tuple, ...]:
    result = []
    for layer in records:
        kind = {"ccx": "rccx"}.get(layer["kind"], layer["kind"])
        primitives = tuple((kind, *gate) for gate in layer["gates"])
        result.append(("layer", primitives))
    return tuple(result)


def audit(path: Path) -> dict:
    data = json.loads(path.read_text())
    final, basis, snapshots = replay_history(as_history_layers(data["layers"]))
    solution = basis.solve(TARGET)
    return {
        "checkpoint": str(path.relative_to(ROOT)),
        "final_midpoint_error": data["distance"],
        "primitive_events": len(snapshots) - 1,
        "historical_unique_signals": len(basis.signals),
        "historical_rank": basis.rank,
        "target_in_history_span": solution is not None,
        "target_remainder_hamming": basis.remainder(TARGET).bit_count(),
        "final_semantic_hash": __import__("hashlib").blake2b(
            b"".join(v.to_bytes(512, "little") for v in final), digest_size=16
        ).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/direct_e_v2_history_audit/report.json")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or [ROOT / path for path in DEFAULT_CHECKPOINTS]
    rows = [audit(path) for path in paths]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"status": "complete", "rows": rows}, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
