"""Evaluate a u3/cx checkpoint with the exact target MPO objective."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mpo_contract import apply_u3_cx_qasm, process_fidelity, target_mpo
from mpo_target import DEFAULT_ORDER


def verify(path: str | Path) -> dict:
    physical_to_slot = {physical: slot for slot, physical in enumerate(DEFAULT_ORDER)}
    candidate = apply_u3_cx_qasm(str(path), physical_to_slot)
    value = process_fidelity(candidate, target_mpo())
    report = {
        "qasm": str(Path(path)),
        "mpo_process_fidelity": value,
        "verification": "exact MPO contraction of serialized u3/cx circuit; approximate target is expected",
    }
    output = Path(path).with_suffix(".mpo.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[1]), indent=2))
