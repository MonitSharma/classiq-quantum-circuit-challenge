"""Calibrate historical list decoding on the strongest saved Direct-E run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from direct_e_history_audit import as_history_layers
from history_list_decoder import calibrate
from phase_history_search import HistoricalBasis, TARGET, replay_history


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "artifacts/direct_e_v2_seeded_n7_a18_s26185/best.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/direct_e_v2_history_decoder_calibration/report.json")
    args = parser.parse_args()
    data = json.loads(args.checkpoint.read_text())
    _, basis, _ = replay_history(as_history_layers(data["layers"]))
    independent = HistoricalBasis()
    values = []
    for signal in basis.signals[1:]:
        before = independent.rank
        independent.add(signal.value, signal.step, signal.wire)
        if independent.rank > before:
            values.append(signal.value)
    rows = calibrate(TARGET, values)
    best = min(rows, key=lambda row: row["distance"])
    report = {
        "status": "complete",
        "checkpoint": str(args.checkpoint.relative_to(ROOT)),
        "final_midpoint_error": data["distance"],
        "historical_rank": basis.rank,
        "gaussian_remainder_weight": basis.remainder(TARGET).bit_count(),
        "best_list_decoded_distance": best["distance"],
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
