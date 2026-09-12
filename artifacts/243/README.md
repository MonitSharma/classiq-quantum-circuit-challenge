# Verified two-stage oracle

Depth **243**, CX **971**, width **18**. This improves the preserved 258-depth
oracle; sub-180 and the observed 183-depth leaderboard target remain unfinished.

`two_stage_243.qasm` is the authoritative standalone oracle.
`two_stage_243.qmod` mirrors every gate and adds twelve Hadamards only in its
`main` synthesis harness. It has not been cloud-resynthesized or submitted.

All 4096 basis inputs and three independent dense states pass verification.
The exact QASM SHA is
`adb3093877907683fd70dcf6bc3a4043f4b4dc2f6999ad118f8fc996d839f4f1`.

Rebuild from the workspace root into a fresh directory:

```sh
.venv/bin/python src/post258_two_stage_build.py --record artifacts/243/class_codes.json --kernel-file artifacts/243/kernel.qasm --outdir /tmp/classiq_243_fresh
```

See [the research report](../../docs/POST258_RESEARCH.md) for construction,
verification, source references, finite search results, and remaining limits.
