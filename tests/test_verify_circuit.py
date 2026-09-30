"""Tests for the standalone verifier in scripts/verify_circuit.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_circuit as vc  # noqa: E402

BEST = ROOT / "artifacts/114/conditional_loader_114_cx564.qasm"

def test_best_circuit_passes():
    r = vc.verify(BEST)
    assert r["passed"]
    assert (r["depth"], r["cx"], r["u3"], r["width"]) == (114, 564, 421, 18)
    assert r["max_error"] < 1e-12

def test_target_matches_challenge_counts():
    t = vc.target_phases()
    assert int((t < 0).sum()) == 1097

def test_corrupted_circuit_fails(tmp_path):
    lines = BEST.read_text().splitlines()
    k = next(i for i, l in enumerate(lines) if l.startswith("u3("))
    lines[k] = lines[k].replace("u3(", "u3(0.3+", 1)
    bad = tmp_path / "bad.qasm"
    bad.write_text("\n".join(lines) + "\n")
    assert not vc.verify(bad)["passed"]

def test_dropped_cx_fails(tmp_path):
    lines = BEST.read_text().splitlines()
    k = next(i for i, l in enumerate(lines) if l.startswith("cx "))
    bad = tmp_path / "bad.qasm"
    bad.write_text("\n".join(lines[:k] + lines[k + 1:]) + "\n")
    assert not vc.verify(bad)["passed"]
