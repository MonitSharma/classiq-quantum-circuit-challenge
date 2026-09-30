"""CLI Entrypoint: Dense random-state Aer verification against geometric specification."""

import sys
import json
from classiq_synth.core.verify import dense_verify


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/verify.py <circuit.qasm> [num_tests]")
        sys.exit(1)

    path = sys.argv[1]
    tests = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    report = dense_verify(path, tests=tests, write_report=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
