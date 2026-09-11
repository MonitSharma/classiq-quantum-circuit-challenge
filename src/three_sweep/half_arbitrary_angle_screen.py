"""Modular phase feasibility screen for the 3+3 row-code banks."""

import json
from pathlib import Path

import z3

from search import logo
from .half_row_loader import half_codes


def feasible_for_control(x_low: int, names: tuple[str, ...], codes: dict):
    theta = [z3.Real(f"theta_{j}") for j in range(len(names))]
    solver = z3.Solver()
    for x5 in range(2):
        for y in range(64):
            z = y & 31
            y5 = y >> 5
            lower = int(codes["z_to_lower_code"][str(z)])
            upper = int(codes["z_to_upper_code"][str(z)])
            values = {
                "constant": 1,
                "x5": x5,
                "y5": y5,
                **{f"l{i}": (lower >> i) & 1 for i in range(3)},
                **{f"u{i}": (upper >> i) & 1 for i in range(3)},
            }
            lift = z3.Int(f"k_{x5}_{y}")
            target = int(logo(x_low | (x5 << 5), y))
            solver.add(sum(values[name] * angle for name, angle in zip(names, theta))
                       == target + 2 * lift)
    return solver.check() == z3.sat


def screen():
    codes = half_codes()
    feature_sets = [
        ("constant", "l0", "l1", "l2", "u0", "u1", "u2"),
        ("constant", "x5", "y5", "l0", "l1", "l2", "u0", "u1", "u2"),
    ]
    result = []
    for names in feature_sets:
        feasible = [feasible_for_control(x, names, codes) for x in range(32)]
        result.append({
            "features": list(names),
            "controls_checked": len(feasible),
            "all_control_slices_feasible": all(feasible),
            "feasible_control_slices": sum(feasible),
        })
    return {
        "model": "exact_modular_real_angle_phase_bank",
        "control_bits": "x0..x4",
        "side_features": result,
        "interpretation": "Feasibility is abstract only; no circuit has been synthesized.",
    }


def write(path="artifacts/three_sweep/half_row_loader/arbitrary_angle_screen.json"):
    result = screen()
    Path(path).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    write()

