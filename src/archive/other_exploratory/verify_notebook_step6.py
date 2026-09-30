"""Run the original notebook's saved-QASM verifier without executing synthesis."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import warnings

import numpy as np
from classiq import ExecutionSession, TranspilationOption


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qasm", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    notebook = root / "classiq-challenge-baseline (1).ipynb"
    cells = json.loads(notebook.read_text())["cells"]
    target = "".join(cells[4]["source"])
    verifier = "".join(cells[16]["source"])
    assert "def logo_pixel(" in target and "def qasm_metrics(" in verifier
    assert "with ExecutionSession(" in verifier
    source = args.qasm.read_bytes()
    namespace = dict(
        QASM_PATH=args.qasm, GRID_SIZE=64, COORD_BITS=6, np=np, re=re,
        warnings=warnings, ExecutionSession=ExecutionSession,
        TranspilationOption=TranspilationOption,
    )
    exec(compile(target, str(notebook) + ":cell4", "exec"), namespace)
    exec(compile(verifier, str(notebook) + ":cell16", "exec"), namespace)
    assert args.qasm.read_bytes() == source, "Saved QASM changed during verification"
    report = dict(
        qasm=str(args.qasm.resolve()), sha256=hashlib.sha256(source).hexdigest(),
        notebook_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),
        verifier="Unmodified notebook cells 4 and 16; Classiq simulator",
        width=namespace["submission_width"], depth=namespace["depth"],
        cx_count=namespace["cx_count"],
        random_states=len(namespace["random_phases"]),
        random_phases=namespace["random_phases"].tolist(),
        max_error=float(namespace["max_error"]),
        ancilla_error=float(namespace["ancilla_error"]),
        normalization_error=float(namespace["normalization_error"]),
    )
    args.qasm.with_suffix(".step6.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
