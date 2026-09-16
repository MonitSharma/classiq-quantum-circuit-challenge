from pathlib import Path
from functools import reduce
from typing import Any, Optional
from egglog import *
from dag import linearized_circuit_from_dag
from rules import load_rules_from
from circ import *
from fractions import Fraction
from fidelity import compute_fidelity_from_qasm, ERROR_RATES
import time, gc, re, sys
from qiskit import qasm2
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.visualization import dag_drawer
from qiskit.qasm2 import dumps as qasm2_dumps
from qiskit.dagcircuit.dagnode import DAGNode, DAGOpNode, DAGInNode, DAGOutNode
from qiskit.dagcircuit import DAGCircuit, DAGCircuitError
from qiskit.circuit import Instruction, Parameter, ParameterExpression
try:
    from egglog.bindings import PrintOverallStatistics
except Exception:
    PrintOverallStatistics = None
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
import re, time, ast

# configs
sys.setrecursionlimit(204800)
STAGE_EXPLORE_STEP = 10
_CX_LINE = re.compile(r'^\s*cx\b', re.IGNORECASE)

_RZ_LINE = re.compile(
    r'^\s*rz\s*\(\s*(?P<expr>.+)\s*\)\s*(?P<qreg>[A-Za-z_]\w*)\[\s*(?P<idx>\d+)\s*\]\s*;\s*$',
    re.IGNORECASE,
)

def _eval_angle(expr: str) -> tuple[Fraction, Fraction]:
    """Return (a,b) s.t. angle == a*pi + b, both Fractions."""
    # normalize 'PI'/'Pi' -> 'pi'
    expr = re.sub(r'\bpi\b', 'pi', expr, flags=re.IGNORECASE)
    node = ast.parse(expr, mode="eval")

    def add(x, y): return (x[0]+y[0], x[1]+y[1])
    def sub(x, y): return (x[0]-y[0], x[1]-y[1])
    def mul(x, s): return (x[0]*s, x[1]*s)  # scalar s (Fraction)

    def walk(n):
        if isinstance(n, ast.Expression): return walk(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return (Fraction(0), Fraction(n.value))
        if isinstance(n, ast.Name) and n.id == 'pi':
            return (Fraction(1), Fraction(0))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            a, b = walk(n.operand); s = 1 if isinstance(n.op, ast.UAdd) else -1
            return (a*s, b*s)
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, (ast.Add, ast.Sub)):
                l, r = walk(n.left), walk(n.right)
                return add(l, r) if isinstance(n.op, ast.Add) else sub(l, r)
        if isinstance(n.op, ast.Mult):
            l, r = walk(n.left), walk(n.right)  # (a_l, b_l), (a_r, b_r)
            if l[0] and r[0]:
                raise ValueError("pi*pi not supported")
            if r[0] == 0:
                return mul(l, r[1])   # (a_l, b_l) * scalar
            if l[0] == 0:
                return mul(r, l[1])   # (a_r, b_r) * scalar
            raise ValueError("unexpected mult case")

        if isinstance(n.op, ast.Div):
            l, r = walk(n.left), walk(n.right)
            if r[0] != 0:
                raise ValueError("division by (a*pi + b) not supported")
            return mul(l, Fraction(1, 1) / r[1])
        raise ValueError("unsupported syntax")
    return walk(node)

def _fmt_pi(a: Fraction) -> str:
    if a == 0: return ""
    sign = "-" if a < 0 else ""
    a = abs(a)
    if a == 1: return f"{sign}pi"
    if a.denominator == 1: return f"{sign}{a.numerator}*pi"
    if a.numerator == 1: return f"{sign}pi/{a.denominator}"
    return f"{sign}{a.numerator}*pi/{a.denominator}"

def _fmt_num(b: Fraction) -> str:
    # compact decimal; keep integers exact
    if b.denominator == 1: return str(b.numerator)
    return f"{float(b):.17g}"

def drop_redundant_rz(qasm_text: str) -> str:
    out = []
    for lineno, line in enumerate(qasm_text.splitlines(), 1):
        m = _RZ_LINE.match(line)
        if not m:
            out.append(line); continue

        expr = m.group("expr").strip()
        # print(f"[rz] in  line #{lineno}: {line.strip()}")
        # print(f"[rz] in  angle#{lineno}: {expr}")

        a, b = _eval_angle(m.group("expr"))
        # drop if angle == 0  or  angle == 2k*pi  (i.e., b==0 and a even integer)
        if b == 0 and a.denominator == 1 and (a.numerator % 2 == 0):
            # print(f"[rz] drop line #{lineno}: angle ≡ 0 (mod 2π); a={a}, b={b}")
            continue
        if a == 0 and b == 0:
            # print(f"[rz] drop line #{lineno}: angle == 0; a={a}, b={b}")
            continue


        parts = []
        s_pi = _fmt_pi(a)
        s_num = _fmt_num(b) if b != 0 else ""
        if s_pi and s_num:
            # handle signs nicely: join as "num + pi" or "num - pi"
            if s_pi.startswith("-"):
                parts = [s_num, "- ", s_pi[1:]]
            else:
                parts = [s_num, " + ", s_pi]
        else:
            parts = [s_pi or s_num]

        angle = "".join(parts)
        new_line = f"rz({angle}) {m.group('qreg')}[{m.group('idx')}];"
        # print(f"[rz] out angle#{lineno}: {angle}   (a={a}, b={b})")
        # print(f"[rz] out line #{lineno}: {new_line}")

        out.append(new_line)
    return "\n".join(out)

def dump_egraph_json(eg, out_path: str):
    be = eg._egraph  
    try:
        ser = be.serialize()      
    except TypeError:
        ser = be.serialize([])    
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(ser.to_json())

# ---------- util ----------
def count_cx(qasm_text: str) -> int:
    return sum(1 for line in qasm_text.splitlines() if _CX_LINE.match(line))

def count_total(qasm_text: str) -> int:
    header = {"openqasm", "include", "qreg", "creg"}
    n = 0
    for raw in qasm_text.splitlines():
        s = raw.split("//", 1)[0].strip()
        if not s:
            continue
        first = s.split(None, 1)[0].lower()
        if first in header:
            continue
        n += 1
    return n


def _count_enodes_eclasses(eglow):
    ser = eglow.serialize([])
    j = json.loads(ser.to_json())
    if "nodes" in j:
        num_enodes = len(j["nodes"])
        if "classes" in j:
            num_eclasses = len(j["classes"])
        else:
            num_eclasses = len({node["eclass"] for node in j["nodes"].values()
                                if isinstance(j["nodes"], dict)})
    elif "classes" in j:
        classes = j["classes"]
        num_eclasses = len(classes)
        if isinstance(classes, dict):
            num_enodes = sum(len(c.get("nodes", [])) for c in classes.values())
        else:
            num_enodes = sum(len(c.get("nodes", [])) for c in classes)
    else:
        def _walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    yield from _walk(v)
                if "eclass" in obj:
                    yield obj["eclass"]
            elif isinstance(obj, list):
                for v in obj:
                    yield from _walk(v)
        eclass_ids = list(_walk(j))
        num_enodes = len(eclass_ids)
        num_eclasses = len(set(eclass_ids))
    return num_enodes, num_eclasses


def run_once(rule_set, origin_circ, explore_step=STAGE_EXPLORE_STEP):
    eg = EGraph()
    eg.register(origin_circ)

    # en_before, ec_before = _count_enodes_eclasses(eg._egraph)
    # print(f"[before] enodes={en_before}, eclasses={ec_before}")

    _, before_cost = eg.extract(origin_circ, include_cost=True)
    t = time.perf_counter()
    eg.run(ruleset(*rule_set) * explore_step)
    t2 = time.perf_counter()
    print(f"[rewrite] time: {t2 - t:.3f}s")
    
    # en_after, ec_after = _count_enodes_eclasses(eg._egraph)
    # print(f"[after ] enodes={en_after}, eclasses={ec_after} (+{en_after-en_before} / +{ec_after-ec_before})")
    t = time.perf_counter()
    best_expr, after_cost = eg.extract(origin_circ, include_cost=True)
    t2 = time.perf_counter()
    print(f"[extract] time: {t2 - t:.3f}s")
    return best_expr, before_cost, after_cost

def _extract_qasm_header(qasm_text: str) -> str:
    header = []
    for ln in qasm_text.splitlines():
        t = ln.strip()
        if not t or t.startswith("//"):
            continue
        if t.startswith(("OPENQASM", "include", "qreg", "creg", "opaque", "gate")):
            header.append(ln)
            continue
        break
    return "\n".join(header)

def _ensure_header(body: str, header: str) -> str:
    return body if body.lstrip().startswith("OPENQASM") \
                else (header + ("" if header.endswith("\n") else "\n") + body)
def optimize_until_stable(
    rules_path: str = "seq-eg/rules.txt",
    init_qasm_path: str = "seq-eg/demo.qasm",
    work_path: str = "seq-eg/tmp.qasm",
    gate_set: str = "ibm_new",
    lower_st_to_rz: bool = True,
    max_iters: int = 10,
    final_path: str | Path = "seq-eg/final.qasm",
    explore_step_each_stage = STAGE_EXPLORE_STEP,
    rules_once_path: str | None = None,
    # windowing control
    windowed: bool = False,
    window_size: int = 20,
    ilp_disabled: bool = False,
    # anytime budget
    time_limit_sec: float | None = None,
    timeline_csv: str | Path | None = None,
    # step escalation (guided equality saturation)
    escalate: bool = True,
    max_step: int | None = None,
    # per-step qasm snapshots for crash resilience
    snapshot_dir: str | Path | None = None,
) -> str:
    RULES_BATCH = load_rules_from(rules_path)
    RULES_ONCE  = load_rules_from(rules_once_path) if rules_once_path else None

    Path(work_path).parent.mkdir(parents=True, exist_ok=True)
    Path(work_path).write_text(Path(init_qasm_path).read_text())
    init_header = _extract_qasm_header(Path(init_qasm_path).read_text())

    # Snapshot dir for per-step qasm checkpoints (crash resilience)
    snap_dir = None
    if snapshot_dir is not None:
        snap_dir = Path(snapshot_dir)
        snap_dir.mkdir(parents=True, exist_ok=True)

    def _save_step_snapshot(step: int):
        if snap_dir is not None:
            try:
                (snap_dir / f"step{step}.qasm").write_text(Path(work_path).read_text())
            except Exception as e:
                print(f"[snapshot] WARN: failed to write step{step}.qasm: {e}")

    # --- timeline bookkeeping (incremental write) ---
    wall_start = time.perf_counter()
    global_iter = [0]  # mutable counter for continuous iteration numbering
    _tl_fieldnames = ["elapsed", "iter", "step", "cx", "total", "fidelity"]
    _tl_file = None
    _tl_writer = None
    if timeline_csv is not None:
        import csv as _csv
        tl_path = Path(timeline_csv)
        tl_path.parent.mkdir(parents=True, exist_ok=True)
        _tl_file = tl_path.open("w", newline="")
        _tl_writer = _csv.DictWriter(_tl_file, fieldnames=_tl_fieldnames)
        _tl_writer.writeheader()
        _tl_file.flush()

    def _record_snapshot(qasm_text: str, step: int = 0):
        elapsed = time.perf_counter() - wall_start
        cx = count_cx(qasm_text)
        total = count_total(qasm_text)
        fid, _ = compute_fidelity_from_qasm(qasm_text)
        if _tl_writer is not None:
            _tl_writer.writerow(dict(
                elapsed=round(elapsed, 3), iter=global_iter[0],
                step=step, cx=cx, total=total, fidelity=fid,
            ))
            _tl_file.flush()

    def _time_left() -> bool:
        if time_limit_sec is None:
            return True
        return (time.perf_counter() - wall_start) < time_limit_sec

    def _run_ilp(qasm_text: str) -> str:
        """Run ILP compaction on QASM text, return compacted QASM."""
        Path(work_path).write_text(qasm_text)
        circ_in = QuantumCircuit.from_qasm_file(work_path)
        dag_in = circuit_to_dag(circ_in)
        compact_circ = linearized_circuit_from_dag(dag_in, ilp_time_limit_sec=60)
        result = qasm2.dumps(compact_circ)
        Path(work_path).write_text(result)
        return result

    # --- initial ILP ---
    circ_before = QuantumCircuit.from_qasm_file(work_path)
    dag_before = circuit_to_dag(circ_before)
    if ilp_disabled:
        Path(work_path).write_text(Path(init_qasm_path).read_text())
        print("No ILP optimization. Start rewriting")
    else:
        compact_circ = linearized_circuit_from_dag(dag_before, ilp_time_limit_sec=60)
        Path(work_path).write_text(qasm2.dumps(compact_circ))
        print("ILP Solver finished. Start Rewriting")

    current_step = explore_step_each_stage

    # record initial state (iter 0)
    _record_snapshot(Path(work_path).read_text(), step=current_step)

    # --- outer escalation loop (guided equality saturation) ---
    while True:
        for i in range(1, max_iters + 1):
            if not _time_left():
                elapsed = time.perf_counter() - wall_start
                print(f"[timeout] {elapsed:.1f}s >= {time_limit_sec}s; stopping.")
                break

            qasm_in = Path(work_path).read_text()
            qasm_in = drop_redundant_rz(qasm_in)
            before_cx = count_cx(qasm_in)
            before_total = count_total(qasm_in)
            t0 = time.perf_counter()

            # Global e-graph
            circ = parse_qasm_to_circ(qasm_in, gate_set=gate_set, lower_st_to_rz=lower_st_to_rz)
            aft, _, _ = run_once(RULES_BATCH, circ, current_step)
            qasm_out = parse_circ_to_qasm(aft)
            qasm_out = drop_redundant_rz(qasm_out)

            t1 = time.perf_counter()
            after_cx = count_cx(qasm_out)
            after_total = count_total(qasm_out)
            Path(work_path).write_text(_ensure_header(qasm_out, init_header))

            global_iter[0] += 1
            tag = "" if not windowed else f"  [DAG windows <{window_size}]"
            print(f"[iter {global_iter[0]}] cx: {before_cx} -> {after_cx} "
                  f"(Δ={after_cx - before_cx:+d}) total: {before_total} -> {after_total} "
                  f"(Δ={after_total - before_total:+d}) | {t1 - t0:.3f}s | step={current_step}{tag}")

            _record_snapshot(Path(work_path).read_text(), step=current_step)
            _save_step_snapshot(current_step)

            if (after_cx == before_cx and after_total == before_total) or qasm_out.strip() == qasm_in.strip():
                break

        # --- escalation decision ---
        if not escalate:
            break

        if not _time_left():
            print(f"[escalation] no time left; stop.")
            break

        next_step = current_step + 1
        if max_step is not None and next_step > max_step:
            print(f"[escalation] reached cap={max_step}; stop.")
            break

        print(f"[escalation] converged at step={current_step} → escalate to step={next_step}")
        current_step = next_step

        # re-run ILP on current best before next escalation round
        if not ilp_disabled:
            if not _time_left():
                print(f"[escalation] no time left for ILP; stop.")
                break
            print(f"[escalation] re-running ILP on current best...")
            current_qasm = Path(work_path).read_text()
            _run_ilp(current_qasm)
            _record_snapshot(Path(work_path).read_text(), step=current_step)
            print(f"[escalation] ILP done. Continuing with step={current_step}")

        gc.collect()

    # --- close timeline CSV ---
    if _tl_file is not None:
        _tl_file.close()

    final_qasm = Path(work_path).read_text()

    final_path = Path(final_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")
    tmp_path.write_text(final_qasm)
    tmp_path.replace(final_path)
    return final_qasm