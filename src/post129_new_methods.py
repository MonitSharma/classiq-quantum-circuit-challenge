"""Bounded experiments for post-185 oracle architectures.

This module implements four concrete ideas that had not been measured together
in the workspace:

1. conditionally-clean/cofactor structural screening;
2. Khattar--Gidney MCX synthesis inside the exact geometric oracle;
3. a dirty-borrowing SelectCopy-style 6->3 QROM loader and complete two-pass
   level oracle using the opposite coordinate register as dirty workspace;
4. a decoder -> AND -> XOR (MVI-inspired) exact level oracle plus a CST-style
   ancilla-feasibility clustering screen.

Every emitted full oracle is transpiled to standalone U3/CX with
``qubits_initially_zero=False``. The script itself performs exact classical
truth-table checks; use ``src/exhaustive_verify.py`` on emitted QASM files before
calling a candidate verified.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from qiskit import QuantumCircuit, qasm2
from qiskit.synthesis import synth_mcx_2_clean_kg24, synth_mcx_2_dirty_kg24

from distributed_frame_search import native
from level_encoder_search_fast import CODES, targets_for
from level_oracle import LEVEL, code_of, emit_kernel, kernel_terms, logo
from search import esop, nested_terms, check_terms

N_INPUT = 12
N_POINTS = 1 << N_INPUT


def anf_profile(values: Sequence[int]) -> dict:
    coeff = list(map(int, values))
    n = int(math.log2(len(coeff)))
    assert 1 << n == len(coeff)
    for bit in range(n):
        step = 1 << bit
        for mask in range(len(coeff)):
            if mask & step:
                coeff[mask] ^= coeff[mask ^ step]
    terms = [mask for mask, value in enumerate(coeff) if value]
    return {
        "terms": len(terms),
        "degree": max((mask.bit_count() for mask in terms), default=0),
        "by_degree": {
            str(d): sum(mask.bit_count() == d for mask in terms)
            for d in sorted({mask.bit_count() for mask in terms})
        },
    }


def cofactor_values(selectors: Sequence[int], assignment: int) -> list[int]:
    selectors = tuple(selectors)
    rest = tuple(bit for bit in range(N_INPUT) if bit not in selectors)
    out = []
    for residual in range(1 << len(rest)):
        p = 0
        for j, bit in enumerate(rest):
            p |= ((residual >> j) & 1) << bit
        for j, bit in enumerate(selectors):
            p |= ((assignment >> j) & 1) << bit
        out.append(int(logo(p & 63, (p >> 6) & 63)))
    return out


def cofactor_screen(max_selectors: int = 4) -> dict:
    """Exact raw-selector screen for the conditional-clean branch idea.

    This is a structural falsification gate, not a native-depth estimate. It
    asks whether fixing a few system bits turns every branch into a tiny ANF.
    """
    best = {}
    started = time.monotonic()
    for k in range(1, max_selectors + 1):
        winner = None
        for selectors in itertools.combinations(range(N_INPUT), k):
            profiles = [anf_profile(cofactor_values(selectors, a)) for a in range(1 << k)]
            score = (
                max(p["terms"] for p in profiles),
                sum(p["terms"] for p in profiles),
                max(p["degree"] for p in profiles),
            )
            if winner is None or score < winner[0]:
                winner = score, selectors, profiles
        assert winner is not None
        score, selectors, profiles = winner
        best[str(k)] = {
            "selectors": list(selectors),
            "max_terms": score[0],
            "total_terms": score[1],
            "max_degree": score[2],
            "branches": profiles,
        }
    return {
        "kind": "conditional_clean_cofactor_screen",
        "exact": True,
        "note": "raw-selector structural screen only; no claim of conditional-clean native depth",
        "best": best,
        "elapsed_seconds": time.monotonic() - started,
    }


def _append_mcx(
    qc: QuantumCircuit,
    controls: Sequence[int],
    target: int,
    ancillas: Sequence[int],
    *,
    dirty: bool,
) -> None:
    controls = list(controls)
    if not controls:
        qc.x(target)
    elif len(controls) == 1:
        qc.cx(controls[0], target)
    elif len(controls) == 2:
        qc.ccx(controls[0], controls[1], target)
    else:
        if len(ancillas) < 2:
            raise ValueError("KG24 synthesis needs two ancillary wires")
        synth = (synth_mcx_2_dirty_kg24 if dirty else synth_mcx_2_clean_kg24)(len(controls))
        qc.compose(synth, list(controls) + [target, ancillas[0], ancillas[1]], inplace=True)


def _predicate_circuit(table: int, controls: Sequence[int], target: int,
                       scratch: Sequence[int], *, dirty_scratch: bool = False) -> QuantumCircuit:
    """Compute a six-variable truth table into ``target`` by an exact ESOP."""
    controls = list(controls)
    assert len(controls) == 6
    q = QuantumCircuit(18)
    for mask, value in esop(table, 6):
        active = [controls[i] for i in range(6) if mask >> i & 1]
        neg = [controls[i] for i in range(6)
               if (mask >> i & 1) and not (value >> i & 1)]
        if neg:
            q.x(neg)
        _append_mcx(q, active, target, scratch, dirty=dirty_scratch)
        if neg:
            q.x(neg)
    return q


def kg24_geometry() -> tuple[QuantumCircuit, dict]:
    """Rebuild the exact nested geometric decomposition with KG24 MCX blocks."""
    terms = nested_terms()
    check_terms(terms)
    q = QuantumCircuit(18)
    cube_stats = []
    for x_table, y_table in terms:
        a = _predicate_circuit(x_table, range(6), 12, [14, 15], dirty_scratch=False)
        b = _predicate_circuit(y_table, range(6, 12), 13, [14, 15], dirty_scratch=False)
        cube_stats.append((len(esop(x_table, 6)), len(esop(y_table, 6))))
        q.compose(a, inplace=True)
        q.compose(b, inplace=True)
        q.cz(12, 13)
        q.compose(b.inverse(), inplace=True)
        q.compose(a.inverse(), inplace=True)
    compiled = native(q)
    return compiled, {
        "kind": "kg24_geometry",
        "semantic_exact": True,
        "terms": len(terms),
        "cube_counts": cube_stats,
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
    }


def table_words(targets: Sequence[int]) -> list[int]:
    assert len(targets) == 3
    return [sum(((targets[bit] >> address) & 1) << bit for bit in range(3))
            for address in range(64)]


def _gray_order(bits: int) -> list[int]:
    return [i ^ (i >> 1) for i in range(1 << bits)]


def _set_negative_frame(q: QuantumCircuit, wires: Sequence[int], current: int, desired: int) -> int:
    delta = current ^ desired
    for bit, wire in enumerate(wires):
        if delta >> bit & 1:
            q.x(wire)
    return desired


def _block_load_dirty(
    q: QuantumCircuit,
    high_controls: Sequence[int],
    dirty_words: Sequence[Sequence[int]],
    words: Sequence[int],
) -> None:
    """XOR the selected pair of 3-bit constants into two dirty registers."""
    assert len(high_controls) == 5
    assert len(dirty_words) == 2 and all(len(w) == 3 for w in dirty_words)
    assert len(words) == 64
    dirty_pool = [wire for group in dirty_words for wire in group]
    frame = 0
    for block in _gray_order(5):
        desired = ((1 << 5) - 1) ^ block
        frame = _set_negative_frame(q, high_controls, frame, desired)
        for which in range(2):
            word = words[2 * block + which]
            for bit in range(3):
                if not (word >> bit) & 1:
                    continue
                target = dirty_words[which][bit]
                aux = [wire for wire in dirty_pool if wire != target][:2]
                _append_mcx(q, high_controls, target, aux, dirty=True)
    _set_negative_frame(q, high_controls, frame, 0)


def _select_dirty_word_xor(q: QuantumCircuit, low: int,
                           dirty_words: Sequence[Sequence[int]], outputs: Sequence[int]) -> None:
    """XOR D[low] into outputs without modifying either dirty register."""
    for bit, out in enumerate(outputs):
        d0, d1 = dirty_words[0][bit], dirty_words[1][bit]
        q.cx(d0, out)
        q.ccx(low, d0, out)
        q.ccx(low, d1, out)


def dirty_selectcopy_stage(
    address: Sequence[int],
    dirty: Sequence[int],
    outputs: Sequence[int],
    targets: Sequence[int],
) -> QuantumCircuit:
    """Exact 6->3 XOR lookup using six arbitrary dirty qubits.

    This is the lambda=2 SelectCopy/toggle-detection specialization: load the
    selected pair into two dirty 3-bit words, XOR the selected dirty word into
    the output, undo the pair load, then XOR the restored dirty word again.
    The unknown dirty baseline cancels and all six borrowed wires are restored.
    """
    assert len(address) == 6 and len(dirty) == 6 and len(outputs) == 3
    assert not (set(address) & set(dirty) or set(address) & set(outputs) or set(dirty) & set(outputs))
    words = table_words(targets)
    q = QuantumCircuit(18)
    dirty_words = [list(dirty[:3]), list(dirty[3:])]
    loader = QuantumCircuit(18)
    _block_load_dirty(loader, address[1:], dirty_words, words)
    q.compose(loader, inplace=True)
    _select_dirty_word_xor(q, address[0], dirty_words, outputs)
    q.compose(loader.inverse(), inplace=True)
    _select_dirty_word_xor(q, address[0], dirty_words, outputs)
    return q


def _xor_targets(a: Sequence[int], b: Sequence[int]) -> list[int]:
    return [x ^ y for x, y in zip(a, b)]


def dirty_qrom_oracle() -> tuple[QuantumCircuit, dict]:
    """Complete level oracle using opposite coordinate wires as dirty QROM workspace."""
    ytriple, xtriple = CODES[0]
    yu1 = targets_for("u1", ytriple)
    yu2 = targets_for("u2", ytriple)
    xv1 = targets_for("v1", xtriple)
    xv2 = targets_for("v2", xtriple)
    ystages = [yu1, _xor_targets(yu1, yu2), yu2]
    xstages = [xv1, _xor_targets(xv1, xv2), xv2]

    alpha1, _ = code_of(ytriple, LEVEL["u1"])
    beta1, _ = code_of(xtriple, LEVEL["v1"])
    alpha2, _ = code_of(ytriple, LEVEL["u2"])
    beta2, _ = code_of(xtriple, LEVEL["v2"])
    assert alpha1 == alpha2 and beta1 == beta2
    kterms = kernel_terms(alpha1, beta1)

    q = QuantumCircuit(18)
    stage_metrics = []
    for stage in range(3):
        yq = dirty_selectcopy_stage(range(6, 12), range(6), [12, 13, 14], ystages[stage])
        xq = dirty_selectcopy_stage(range(6), range(6, 12), [15, 16, 17], xstages[stage])
        stage_metrics.append({
            "y_raw_depth": yq.depth(),
            "x_raw_depth": xq.depth(),
            "y_raw_size": yq.size(),
            "x_raw_size": xq.size(),
        })
        q.compose(yq, inplace=True)
        q.compose(xq, inplace=True)
        if stage < 2:
            emit_kernel(q, kterms, [12, 13, 14], [15, 16, 17])
    compiled = native(q)
    return compiled, {
        "kind": "dirty_selectcopy_qrom",
        "semantic_exact": True,
        "borrowed_wires": "opposite six-coordinate register",
        "lambda": 2,
        "stage_metrics": stage_metrics,
        "kernel_terms": kterms,
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
    }


def _truth6(predicate) -> int:
    return sum(int(predicate(v)) << v for v in range(64))


def _mvi_pass_terms(yname: str, xname: str, orientation: str) -> list[tuple[int, int]]:
    """Five disjoint decoder products for [level_y + level_x >= 6]."""
    yt, xt = LEVEL[yname], LEVEL[xname]
    terms = []
    if orientation == "y":
        for u in range(1, 6):
            a = _truth6(lambda y, u=u: yt[y] == u)
            b = _truth6(lambda x, u=u: xt[x] >= 6 - u)
            if a and b:
                terms.append((a, b))
    elif orientation == "x":
        for v in range(1, 6):
            a = _truth6(lambda y, v=v: yt[y] >= 6 - v)
            b = _truth6(lambda x, v=v: xt[x] == v)
            if a and b:
                terms.append((a, b))
    else:
        raise ValueError(orientation)
    for y in range(64):
        for x in range(64):
            got = 0
            for a, b in terms:
                got ^= ((a >> y) & 1) & ((b >> x) & 1)
            assert got == int(yt[y] + xt[x] >= 6)
    return terms


def _decoder_proxy(terms: Sequence[tuple[int, int]]) -> int:
    return sum(len(esop(a, 6)) + len(esop(b, 6)) for a, b in terms)


def _mvi_pass(yname: str, xname: str, orientation: str) -> tuple[QuantumCircuit, dict]:
    terms = _mvi_pass_terms(yname, xname, orientation)
    q = QuantumCircuit(18)
    cubes = []
    for ytable, xtable in terms:
        yp = _predicate_circuit(ytable, range(6, 12), 12, [14, 15], dirty_scratch=False)
        xp = _predicate_circuit(xtable, range(6), 13, [14, 15], dirty_scratch=False)
        cubes.append((len(esop(ytable, 6)), len(esop(xtable, 6))))
        q.compose(yp, inplace=True)
        q.compose(xp, inplace=True)
        q.cz(12, 13)
        q.compose(xp.inverse(), inplace=True)
        q.compose(yp.inverse(), inplace=True)
    return q, {"orientation": orientation, "terms": len(terms), "cube_counts": cubes,
               "proxy_cubes": _decoder_proxy(terms)}


def mvi_decoder_oracle() -> tuple[QuantumCircuit, dict]:
    choices = []
    for pass_names in [("u1", "v1"), ("u2", "v2")]:
        variants = []
        for orientation in ("y", "x"):
            raw, meta = _mvi_pass(*pass_names, orientation)
            compiled = native(raw)
            meta = dict(meta, isolated_depth=compiled.depth(),
                        isolated_cx=compiled.count_ops().get("cx", 0))
            variants.append((compiled.depth(), compiled.count_ops().get("cx", 0), raw, meta))
        variants.sort(key=lambda row: row[:2])
        choices.append((variants[0][2], variants[0][3], [v[3] for v in variants]))
    q = QuantumCircuit(18)
    for raw, _, _ in choices:
        q.compose(raw, inplace=True)
    compiled = native(q)
    for y in range(64):
        for x in range(64):
            got = int(LEVEL["u1"][y] + LEVEL["v1"][x] >= 6) ^ int(
                LEVEL["u2"][y] + LEVEL["v2"][x] >= 6)
            assert got == int(logo(x, y))
    return compiled, {
        "kind": "mvi_decoder",
        "semantic_exact": True,
        "passes": [{"chosen": chosen, "variants": variants} for _, chosen, variants in choices],
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
    }


@dataclass(frozen=True)
class ClusterItem:
    name: str
    variables: frozenset[int]


def replication_redundancy(items: Sequence[ClusterItem]) -> int:
    counts: dict[int, int] = {}
    for item in items:
        for variable in item.variables:
            counts[variable] = counts.get(variable, 0) + 1
    return sum(max(count - 1, 0) for count in counts.values())


def cluster_ancilla_cost(items: Sequence[ClusterItem]) -> int:
    """ClausePack-style cost: one result per item plus variable replication."""
    return len(items) + replication_redundancy(items)


def seedgrow(items: Sequence[ClusterItem], ancillas: int) -> list[list[ClusterItem]]:
    """Small deterministic SeedGrow analogue for the paper's feasibility rule."""
    remaining = list(items)
    clusters: list[list[ClusterItem]] = []
    while remaining:
        def degree(item: ClusterItem) -> int:
            return sum(bool(item.variables & other.variables) for other in remaining if other != item)
        seed = min(remaining, key=lambda item: (degree(item), item.name))
        cluster = [seed]
        remaining.remove(seed)
        while True:
            feasible = []
            for candidate in remaining:
                trial = cluster + [candidate]
                if cluster_ancilla_cost(trial) <= ancillas:
                    overlap = sum(len(candidate.variables & item.variables) for item in cluster)
                    feasible.append((overlap, candidate.name, candidate))
            if not feasible:
                break
            _, _, chosen = min(feasible)
            cluster.append(chosen)
            remaining.remove(chosen)
        clusters.append(cluster)
    return clusters


def cst_screen(ancillas: int = 6) -> dict:
    """Apply CST/ClausePack's replication accounting to our MVI phase terms."""
    items = []
    for p, (yn, xn) in enumerate((("u1", "v1"), ("u2", "v2")), 1):
        options = []
        for orientation in ("y", "x"):
            terms = _mvi_pass_terms(yn, xn, orientation)
            rendered = []
            for i, (ytab, xtab) in enumerate(terms):
                used = set()
                for table, offset in ((ytab, 6), (xtab, 0)):
                    for mask, _ in esop(table, 6):
                        used.update(offset + bit for bit in range(6) if mask >> bit & 1)
                rendered.append(ClusterItem(f"p{p}_{orientation}_{i}", frozenset(used)))
            options.append((_decoder_proxy(terms), rendered, orientation))
        _, chosen, _ = min(options, key=lambda row: row[0])
        items.extend(chosen)
    clusters = seedgrow(items, ancillas)
    return {
        "kind": "cst_clausepack_screen",
        "ancillas": ancillas,
        "items": [{"name": i.name, "variables": sorted(i.variables)} for i in items],
        "clusters": [[i.name for i in cluster] for cluster in clusters],
        "cluster_costs": [cluster_ancilla_cost(cluster) for cluster in clusters],
        "max_cluster_size": max(map(len, clusters), default=0),
        "note": "resource-feasibility screen; not a claim that CST is globally inapplicable",
    }


def save_candidate(outdir: Path, name: str, circuit: QuantumCircuit, report: dict) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}_d{circuit.depth()}_cx{circuit.count_ops().get('cx', 0)}.qasm"
    path.write_text(qasm2.dumps(circuit))
    saved = dict(report, qasm=str(path))
    (outdir / f"{name}.json").write_text(json.dumps(saved, indent=2) + "\n")
    return path


def run(outdir: Path, methods: Sequence[str]) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    if "cofactor" in methods:
        result = cofactor_screen()
        (outdir / "cofactor.json").write_text(json.dumps(result, indent=2) + "\n")
        results["cofactor"] = result
    if "kg24" in methods:
        circuit, result = kg24_geometry()
        path = save_candidate(outdir, "kg24_geometry", circuit, result)
        results["kg24"] = dict(result, qasm=str(path))
    if "qrom" in methods:
        circuit, result = dirty_qrom_oracle()
        path = save_candidate(outdir, "dirty_qrom", circuit, result)
        results["qrom"] = dict(result, qasm=str(path))
    if "mvi" in methods:
        circuit, result = mvi_decoder_oracle()
        path = save_candidate(outdir, "mvi_decoder", circuit, result)
        results["mvi"] = dict(result, qasm=str(path))
    if "cst" in methods:
        result = cst_screen()
        (outdir / "cst.json").write_text(json.dumps(result, indent=2) + "\n")
        results["cst"] = result
    (outdir / "report.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2), flush=True)
    return results


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--methods", default="cofactor,kg24,qrom,mvi,cst")
    args = p.parse_args()
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    unknown = set(methods) - {"cofactor", "kg24", "qrom", "mvi", "cst"}
    if unknown:
        raise SystemExit(f"unknown methods: {sorted(unknown)}")
    run(args.outdir, methods)


if __name__ == "__main__":
    main()
