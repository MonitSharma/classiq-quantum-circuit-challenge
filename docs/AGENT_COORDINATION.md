# Agent coordination contract

This file is the shared source of truth for concurrent optimization work. Read
it before starting an experiment and update the status row before claiming a
new line of work.

## Protected baseline

The immutable fallback is:

```text
artifacts/531/full_mux_531.qasm
depth 531 / CX 1020 / width 18
```

No agent may overwrite that package or replace it with an unverified result.

## Ownership split

| Agent | Workspace | Exclusive research scope | Artifact prefix |
|---|---|---|---|
| Codex | `/Users/monitsharma/Downloads/classiq` (`main`) | Integration, exhaustive verification, score comparison, documentation, and submission packaging; direct phase/QROM experiments are now closed | `codex_` |
| Claude | `/Users/monitsharma/Downloads/classiq/.claude/worktrees/classiq-quantum-challenge-a40f1f` | A genuinely independent reversible decision-diagram/cofactor compiler; do not use rank/pair terms, direct phase-cube expansion, or ordinary UCR loading as the primary construction | `claude_` |

The two agents must not run the same search with different seeds, duplicate a
closed experiment, or write into the other agent's artifact prefix. A result
that crosses scopes must be explicitly labelled as a comparison, not silently
adopted.

## Current claims

| Line | Owner | Status | Best evidence |
|---|---|---|---|
| Protected complete oracle | shared | verified | 531 / 1020 / 18 |
| Direct phase-only rank expansion | Codex | closed | 1725 / 1225 / 18 |
| Shared-y phase grouping | Codex | closed | 2242 / 1624 / 18 |
| Decision-diagram/cofactor compiler | Claude | available for independent work | no promoted candidate yet |

## Experiment lease

Before starting, add one row under `Active leases` with the experiment name,
owner, output prefix, and expected completion. Do not claim an existing lease.
When finished, change it to `closed` or `promising` and include the exact
QASM hash and verification report path.

### Active leases

| Experiment | Owner | Prefix | Status |
|---|---|---|---|
| Direct phase/QROM sharing | Codex | `codex_` | closed; best complete result 1725/1225 |
| Integration and verification of incoming candidates | Codex | `codex_` | active |
| Independent reversible cofactor compiler | Claude | `claude_` | active; only optimization lease |

## Merge protocol

1. Work only in the assigned worktree and use a new artifact filename.
2. Compile the exact serialized standalone QASM to `u3`/`cx` with
   `qubits_initially_zero=False` for every reusable subcircuit.
3. Run exhaustive verification over all 4,096 inputs and record the matching
   SHA, depth, CX count, width, and ancilla leakage.
4. Update `docs/EXPERIMENTS.md` and `docs/HANDOFF.md` only after verification.
5. Commit in the agent's worktree. The main workspace owner merges the commit
   into `main` with a normal merge and pushes it; no force pushes or resets.

Unverified artifacts may remain locally for debugging, but they must not be
described as improvements or merged into the protected submission package.
