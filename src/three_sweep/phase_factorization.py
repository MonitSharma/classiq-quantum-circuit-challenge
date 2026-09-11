"""Lower-bound the simple pi-angle phase-track model.

For fixed five control bits u, a bank of pi-angle RZ tracks whose target
features depend only on the remaining coordinates produces an affine GF(2)
combination of side-feature columns.  The row-space rank of the exact phase
table therefore lower-bounds the number of independent side features, with
one dimension reserved for a control-only/global phase.
"""

import json
from pathlib import Path

from .phase_rank_screen import screen


def analyze():
    report = screen()
    rows = []
    for item in report["results"]:
        rows.append({
            "chosen_bits": item["chosen_bits"],
            "gf2_phase_row_rank": item["gf2_rank"],
            "minimum_nonconstant_pi_tracks": max(0, item["gf2_rank"] - 1),
            "sign_rank": item["sign_rank"],
        })
    best = min(rows, key=lambda item: (item["minimum_nonconstant_pi_tracks"], item["sign_rank"]))
    return {
        "model": "pi_angle_RZ_tracks_with_arbitrary_side_boolean_features",
        "partitions": len(rows),
        "best_partition": best,
        "minimum_over_all_partitions": min(item["minimum_nonconstant_pi_tracks"] for item in rows),
        "interpretation": (
            "Five or six side-feature tracks cannot represent the exact phase "
            "in this restricted pi-angle UCR model. This is not an impossibility "
            "result for arbitrary-angle or non-UCR circuits."
        ),
    }


def write(path="artifacts/three_sweep/phase_factorization_screen.json"):
    result = analyze()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    write()

