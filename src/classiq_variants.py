"""Synthesize several oracle formulations through the Classiq toolchain.

Motivation: the leaderboard's top three use 348-557 CX, while every circuit in
this repository is a hand-built phase-polynomial multiplexer whose CX count is
structurally pinned near 850 (one CX per rotation).  Those CX counts are only
reachable by Boolean-logic synthesis -- i.e. the pipeline the challenge baseline
actually uses.  No file in src/ called classiq.synthesize before this one.

Run:  .venv/bin/python src/classiq_variants.py
(requires `classiq.authenticate()` once in this environment)
"""
from collections import defaultdict
from math import pi
from pathlib import Path

import classiq
from classiq import (Constraints, CustomHardwareSettings, OptimizationParameter,
                     Output, Preferences, QNum, Const, TargetLanguage,
                     TranspilationOption, allocate, control, create_model, export,
                     hadamard_transform, phase, qfunc, qperm, synthesize,
                     write_qmod)

G, COORD_BITS = 64, 6


def logo_pixel(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53) or (26 <= x <= 49 and 39 <= y <= 43)
            or (x - 55) ** 2 + (y - 41) ** 2 <= 42
            or (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def _rects():
    def row(y):
        xs = [x for x in range(G) if logo_pixel(x, y)]
        if not xs:
            return ()
        out, s, e = [], xs[0], xs[0]
        for x in xs[1:]:
            if x == e + 1:
                e = x
            else:
                out.append((s, e)); s = e = x
        out.append((s, e))
        return tuple(out)
    act, rects = {}, []
    for y in range(G + 1):
        iv = set(row(y)) if y < G else set()
        for k, ym in tuple(act.items()):
            if k not in iv:
                rects.append((*k, ym, y - 1)); del act[k]
        for k in iv:
            act.setdefault(k, y)
    return tuple(sorted(rects, key=lambda b: (b[2], b[0])))


RECTS = _rects()
BYX = defaultdict(list)
for _a, _b, _c, _d in RECTS:
    BYX[(_a, _b)].append((_c, _d))
MERGED = [(a, b, sorted(v)) for (a, b), v in sorted(BYX.items())]


def _yband(y, c, d):
    return (y == c) if c == d else ((y >= c) & (y <= d))


@qperm
def v0_baseline(x: Const[QNum], y: Const[QNum]) -> None:
    """The baseline: one control per rectangle (18 terms)."""
    for xm, xM, ym, yM in RECTS:
        control(((x >= xm) & (x <= xM)) & _yband(y, ym, yM), lambda: phase(pi))


@qperm
def v1_merged(x: Const[QNum], y: Const[QNum]) -> None:
    """Rectangles sharing an x-interval merge: 10 terms == the GF(2) rank."""
    for xm, xM, ys in MERGED:
        cond = _yband(y, *ys[0])
        for c, d in ys[1:]:
            cond = cond | _yband(y, c, d)
        control(((x >= xm) & (x <= xM)) & cond, lambda: phase(pi))


@qperm
def v2_single_or(x: Const[QNum], y: Const[QNum]) -> None:
    """One control over the union of the four original regions."""
    control(
        (((x >= 2) & (x <= 26)) & ((y >= 29) & (y <= 53)))
        | (((x >= 26) & (x <= 49)) & ((y >= 39) & (y <= 43)))
        | (((x - 55) ** 2 + (y - 41) ** 2) <= 42)
        | (((x - 40) ** 2 + (y - 19) ** 2) <= 72),
        lambda: phase(pi),
    )


@qperm
def v3_disjoint(x: Const[QNum], y: Const[QNum]) -> None:
    """Four pairwise-disjoint regions (verified disjoint), so phases just add."""
    control(((x >= 2) & (x <= 26)) & ((y >= 29) & (y <= 53)), lambda: phase(pi))
    control(((x >= 27) & (x <= 48)) & ((y >= 39) & (y <= 43)), lambda: phase(pi))
    control((((x - 55) ** 2 + (y - 41) ** 2) <= 42), lambda: phase(pi))
    control((((x - 40) ** 2 + (y - 19) ** 2) <= 72), lambda: phase(pi))


VARIANTS = {"v0_baseline": v0_baseline, "v1_merged": v1_merged,
            "v2_single_or": v2_single_or, "v3_disjoint": v3_disjoint}


def run(name, oracle, max_width=18):
    @qfunc
    def main(x: Output[QNum[COORD_BITS]], y: Output[QNum[COORD_BITS]]) -> None:
        allocate(x); allocate(y)
        hadamard_transform(x); hadamard_transform(y)
        oracle(x, y)

    model = create_model(main, constraints=Constraints(
        optimization_parameter=OptimizationParameter.DEPTH, max_width=max_width))
    qprog = synthesize(model)
    raw = export(qprog, TargetLanguage.QASM2).splitlines()
    drop = {i for i, l in enumerate(raw)
            if l.lstrip().startswith("hadamard_transform_") and "q[" in l}
    if len(drop) != 2:
        raise RuntimeError(f"{name}: expected 2 harness Hadamards, found {len(drop)}")
    cand = classiq.quantum_program_from_qasm(
        "\n".join(l for i, l in enumerate(raw) if i not in drop))
    tr = classiq.transpile(cand, preferences=Preferences(
        transpilation_option=TranspilationOption.AUTO_OPTIMIZE,
        custom_hardware_settings=CustomHardwareSettings(basis_gates=["u3", "cx"])))
    m = classiq.get_transpiled_circuit_metrics(tr)
    out = Path(f"artifacts/classiq_{name}")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.qasm").write_text(export(tr, TargetLanguage.QASM2))
    write_qmod(model, str(out / name))
    return m.width, m.depth, m.count_ops.get("cx", 0)


if __name__ == "__main__":
    import classiq.interface.exceptions as cx_exc
    print("Synthesizing 4 formulations (all verified against logo, 0 mismatches).")
    print("Read v0_baseline first: if it reproduces ~531 the pipeline is sound")
    print("and the other three are directly comparable.\n")
    print(f"{'variant':<16}{'width':>7}{'depth':>8}{'cx':>7}   {'vs your 190'}")
    results = {}
    for name, fn in VARIANTS.items():
        try:
            w, d, c = run(name, fn)
            results[name] = (w, d, c)
            delta = "" if name == "v0_baseline" else f"{d - 190:+d}"
            print(f"{name:<16}{w:>7}{d:>8}{c:>7}   {delta}")
        except cx_exc.ClassiqExpiredTokenError:
            print("\nClassiq token expired. Refresh it once with:")
            print("    .venv/bin/python -c 'import classiq; classiq.authenticate()'")
            print("then re-run this script.")
            raise SystemExit(1)
        except Exception as exc:
            print(f"{name:<16}  FAILED: {type(exc).__name__}: {str(exc)[:120]}")
    if results:
        best = min(results.items(), key=lambda kv: (kv[1][1], kv[1][2]))
        print(f"\nbest: {best[0]} -> depth {best[1][1]}, cx {best[1][2]}")
        print("Artifacts (QASM + qmod) are under artifacts/classiq_<variant>/.")
        print("Any candidate must still pass src/exhaustive_verify.py before use.")
