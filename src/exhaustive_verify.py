"""CLI Entrypoint: Exhaustive sparse verification across all 4096 basis inputs."""

import sys
import json
from classiq_synth.core.verify import exhaustive_verify


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/exhaustive_verify.py <circuit.qasm> [max_width]")
        sys.exit(1)

    path = sys.argv[1]
    max_width = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    report = exhaustive_verify(path, max_width=max_width, write_report=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
