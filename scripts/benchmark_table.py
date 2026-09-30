"""Scan milestone artifacts and generate formatted Markdown & LaTeX benchmark tables."""

from pathlib import Path
import json
from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"

# Key architectural milestones in chronological order
MILESTONES = [
    ("Initial Baseline", "jupyter_files/classiq-challenge-baseline (1).ipynb", 5329, 3502, 18, "Era I: Initial Classiq Baseline"),
    ("Direct XAG Rank", "artifacts/archive/xag_rank_True.qasm", 1046, 903, 18, "Era I: Direct XAG synthesis"),
    ("Radius Mux", "artifacts/archive/radius_mux.qasm", 682, 740, 18, "Era I: Radius feature multiplexing"),
    ("Affine Full Mux", "artifacts/524/full_mux_feature_linear_tket_524.qasm", 524, 950, 18, "Era II: Affine 6-feature LUT multiplexer"),
    ("Distributed Lookup", "artifacts/258/distributed_level_258.qasm", 258, 1188, 18, "Era III: 3-stage distributed coordinate lookup"),
    ("Two-Stage Integer Lift", "artifacts/218/two_stage_218.qasm", 218, 897, 18, "Era IV: Parity class codes & integer full-turn cube additions"),
    ("3-Wire CNOT Bridge", "artifacts/185/two_stage_185.qasm", 185, 854, 18, "Era V: CNOT bridge rewrites & ancilla permutations"),
    ("Placement-Free Anneal", "artifacts/148/conditional_loader_148.qasm", 148, 635, 18, "Era VI: Placement-free loaders + simulated annealing"),
    ("Sub-140 Beam Kernel", "artifacts/137/conditional_loader_137.qasm", 137, 624, 18, "Era VII: Window-aware beam kernel search"),
    ("Layer-Synchronous Beam", "artifacts/126/conditional_loader_126.qasm", 126, 634, 18, "Era VII: Synchronous beam loaders + star frames"),
    ("Prefix Restart Beam", "artifacts/123/conditional_loader_123.qasm", 123, 627, 18, "Era VII: Two-step reach heuristic + prefix restarts"),
    ("Lifted Ready-Sum", "artifacts/121/conditional_loader_121.qasm", 121, 584, 18, "Era VII: Ready-sum minimization (Sigma: 356 -> 337)"),
    ("Mod-2pi Lifted Loader", "artifacts/120/conditional_loader_120.qasm", 120, 589, 18, "Era VII: mod-2pi lift of conditional targets over Z_64"),
    ("Directional Freeze Beam", "artifacts/118/conditional_loader_118.qasm", 118, 590, 18, "Era VII: BLKW directional weighting in lbeam4"),
    ("CX-Optimized Milestone", "artifacts/118b/conditional_loader_118b.qasm", 118, 585, 18, "Era VII: Equal depth to 118, 5 fewer CX"),
    ("Historical 117 (Baseline)", "artifacts/117/conditional_loader_117.qasm", 117, 590, 18, "Era VII: Rotation pull-in mechanism ([value_fixed, T-unload])"),
    ("Historical 117 (577 CX)", "artifacts/117/conditional_loader_117_cx577.qasm", 117, 577, 18, "Era VII: Commutation cancellation + exact HiGHS MILP rescheduling (13 fewer CX)"),
    ("Previous Champion (576 CX)", "artifacts/117/conditional_loader_117_cx576.qasm", 117, 576, 18, "Era VII: Optimal tiebreak milestone (14 fewer CX, 576 CX at depth 117)"),
    ("Verified 116 Baseline (573 CX)", "artifacts/116/conditional_loader_116.qasm", 116, 573, 18, "Era VIII: Reachable-code phase freedom & kernel resynthesis (depth 116, 573 CX)"),
    ("Verified 116 Tiebreak (571 CX)", "artifacts/116/conditional_loader_116_cx571.qasm", 116, 571, 18, "Era VIII: Wire-basis normalization + corrected restoration bound (depth 116, 571 CX)"),
    ("Verified 116 Tiebreak (570 CX)", "artifacts/116/conditional_loader_116_cx570.qasm", 116, 570, 18, "Era VIII: Plateau phase array co_47 + calibrated model (depth 116, 570 CX)"),
    ("Verified 116 Milestone (565 CX)", "artifacts/116/conditional_loader_116_cx565.qasm", 116, 565, 18, "Era VIII: Champion x + y1 loader + strict-model T=115 beam kernel (depth 116, 565 CX)"),
    ("Verified 115 Record (566 CX)", "artifacts/115/conditional_loader_115_cx566.qasm", 115, 566, 18, "Era IX: Asymmetric loader pairing + FEM kernel + numerical 3-qubit resynthesis (depth 115, 566 CX)"),
    ("Verified 115 Record (567 CX)", "artifacts/115/conditional_loader_115_cx567.qasm", 115, 567, 18, "Era IX: Asymmetric loader pairing + FEM kernel + SAT CX peephole kpeep (depth 115, 567 CX)"),
    ("Verified 115 Record (568 CX)", "artifacts/115/conditional_loader_115_cx568.qasm", 115, 568, 18, "Era IX: Asymmetric loader pairing + FEM kernel + SAT CX peephole kpeep (depth 115, 568 CX)"),
    ("Verified 115 Tiebreak (569 CX)", "artifacts/115/conditional_loader_115_cx569.qasm", 115, 569, 18, "Era IX: Asymmetric loader pairing + FEM kernel tiebreak variant (depth 115, 569 CX)"),
    ("Initial Submission 115", "artifacts/115/conditional_loader_115.qasm", 115, 575, 18, "Era IX: Asymmetric loader pairing + Fused Exact Model (FEM) kernel (depth 115, 575 CX)"),
    ("Prior Submission 114 (564 CX)", "artifacts/114/conditional_loader_114_cx564.qasm", 114, 564, 18, "Era X: Relabeled conditional target at closing H + CX-penalised kernel + 3-qubit resynthesis (depth 114, 564 CX; Prior Submission)"),
    ("Verified 114 Tiebreak (571 CX)", "artifacts/114/conditional_loader_114_cx571.qasm", 114, 571, 18, "Era X: Relabeled conditional target at closing H (x target 1 loads L1⊕L0) (depth 114, 571 CX)"),
    ("Verified 113 Champion (564 CX)", "artifacts/113/conditional_loader_113_cx564.qasm", 113, 564, 18, "Era XI: Dual-side closing-H relabeling + 4-round numerical 3-qubit resynthesis (depth 113, 564 CX)"),
    ("Verified 113 Variant (568 CX)", "artifacts/113/conditional_loader_113_cx568.qasm", 113, 568, 18, "Era XI: Dual-side closing-H relabeling (x T1, T2 & y T2) + exact MILP scheduling (depth 113, 568 CX)"),
    ("Verified 112 Variant (576 CX)", "artifacts/112/conditional_loader_112_cx576.qasm", 112, 576, 18, "Era XII: Dual-side relabeling + early parity target + exact MILP scheduling (depth 112, 576 CX)"),
    ("Verified 112 Champion (573 CX)", "artifacts/112/conditional_loader_112_cx573.qasm", 112, 573, 18, "Era XII: Dual-side relabeling + early parity target + loader/kernel resynthesis (depth 112, 573 CX; Prior Record)"),
    ("Verified 111 Variant (561 CX)", "artifacts/111/conditional_loader_111_cx561.qasm", 111, 561, 18, "Era XIII: Sparse target supports + exact start-basis screen + FEM kernel + MILP (depth 111, 561 CX)"),
    ("Verified 111 Variant (558 CX)", "artifacts/111/conditional_loader_111_cx558.qasm", 111, 558, 18, "Era XIII: Sparse target supports + numerical 3-qubit resynthesis of block [0, 2, 16] (depth 111, 558 CX)"),
    ("Submitted Champion 111 (557 CX)", "submission/submission.qasm", 111, 557, 18, "Era XIII: Sparse target supports + FEM kernel + 3-qubit resynthesis (depth 111, 557 CX; Official Submission & All-Time Record)"),
]


def generate_markdown_table():
    lines = []
    lines.append("| Milestone / Attempt | Depth | CX Count | Width | Reduction vs Baseline | Key Architectural Innovation |")
    lines.append("|---|:---:|:---:|:---:|:---:|---|")
    baseline_depth = 5329

    for name, rel_path, depth, cx, width, note in MILESTONES:
        reduction = f"{((baseline_depth - depth) / baseline_depth) * 100:.1f}%"
        bold = "**" if depth in (111, 112, 113, 114, 115, 116, 117, 118) and ("Champion" in name or "Record" in name or "CX-Optimized" in name) else ""
        link_name = f"{bold}{name}{bold}"
        lines.append(f"| {link_name} | {bold}{depth}{bold} | {bold}{cx}{bold} | {width} | {reduction} | {note} |")

    return "\n".join(lines)


def generate_latex_table():
    lines = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Optimization Progression across Architectural Eras for the Classiq Challenge Oracle.}")
    lines.append(r"\label{tab:optimization_progression}")
    lines.append(r"\begin{tabular}{lccccp{7.5cm}}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Milestone} & \textbf{Depth} & \textbf{CX Count} & \textbf{Width} & \textbf{Reduction} & \textbf{Key Breakthrough} \\")
    lines.append(r"\hline")
    baseline_depth = 5329

    for name, rel_path, depth, cx, width, note in MILESTONES:
        reduction = f"{((baseline_depth - depth) / baseline_depth) * 100:.1f}\\%"
        if "Champion" in name or "Record" in name:
            lines.append(rf"\textbf{{{name}}} & \textbf{{{depth}}} & \textbf{{{cx}}} & \textbf{{{width}}} & \textbf{{{reduction}}} & \textbf{{{note}}} \\")
        else:
            lines.append(rf"{name} & {depth} & {cx} & {width} & {reduction} & {note} \\")

    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    return "\n".join(lines)


if __name__ == "__main__":
    md = generate_markdown_table()
    latex = generate_latex_table()

    out_md = ROOT / "docs" / "BENCHMARK_TABLE.md"
    out_tex = ROOT / "docs" / "BENCHMARK_TABLE.tex"

    out_md.write_text(f"# Classiq Challenge Benchmark Comparison\n\n{md}\n")
    out_tex.write_text(latex + "\n")

    print(f"Generated Markdown table: {out_md}")
    print(f"Generated LaTeX table: {out_tex}")
    print("\nMarkdown Table Preview:\n")
    print(md[:600] + "...\n")
