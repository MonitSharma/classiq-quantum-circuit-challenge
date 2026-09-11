"""Exact modular feasibility screen for natural arbitrary-angle phase tracks."""

import json
from pathlib import Path

import z3

from search import logo
from .row_pair_analysis import analyze, codebook


def feature_row(z: int, x5: int, y5: int, names: tuple[str, ...], codes: dict[int, int]):
    values = {
        "constant": 1,
        "x5": x5,
        "y5": y5,
        **{f"c{i}": (codes[z] >> i) & 1 for i in range(5)},
    }
    return [values[name] for name in names]


def feasible_for_control(x_low: int, names: tuple[str, ...], codes: dict[int, int]):
    theta = [z3.Real(f"theta_{j}") for j in range(len(names))]
    solver = z3.Solver()
    for x5 in range(2):
        for y in range(64):
            z = y & 31
            y5 = y >> 5
            row = feature_row(z, x5, y5, names, codes)
            lift = z3.Int(f"k_{x5}_{y}")
            target = int(logo(x_low | (x5 << 5), y))
            solver.add(sum(value * angle for value, angle in zip(row, theta))
                       == target + 2 * lift)
    return solver.check() == z3.sat


def screen():
    result = analyze()
    cb = codebook(result)
    codes = {int(z): int(code) for z, code in cb["z_to_code"].items()}
    feature_sets = [
        ("constant", "c0", "c1", "c2", "c3", "c4"),
        ("constant", "x5", "c0", "c1", "c2", "c3", "c4"),
        ("constant", "y5", "c0", "c1", "c2", "c3", "c4"),
        ("constant", "x5", "y5", "c0", "c1", "c2", "c3", "c4"),
    ]
    outputs = []
    for names in feature_sets:
        controls = [feasible_for_control(x_low, names, codes) for x_low in range(32)]
        outputs.append({
            "features": list(names),
            "controls_checked": len(controls),
            "all_control_slices_feasible": all(controls),
            "feasible_control_slices": sum(controls),
        })
    return {
        "model": "exact_modular_real_angle_phase_bank",
        "control_bits": "x0..x4",
        "side_features": outputs,
        "interpretation": (
            "Feasibility means the target sign table lies in the modular phase "
            "manifold for the listed binary features. It does not synthesize or "
            "verify a complete quantum circuit."
        ),
    }


def write(path="artifacts/three_sweep/arbitrary_angle_screen.json"):
    result = screen()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    write()

