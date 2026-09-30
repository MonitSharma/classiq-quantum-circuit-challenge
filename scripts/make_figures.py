#!/usr/bin/env python3
"""Regenerate every figure in docs/figures/ from the repository contents.

Inputs (all tracked in the repository):
  * the challenge predicate (scripts/verify_circuit.py, identical to src/classiq_synth/core/oracle.py)
  * artifacts/115/conditional_loader_115_cx566.qasm         (best circuit)
  * docs/figures/data/interface_115.json                     (code wires and ready times)
  * artifacts/115/recipes/kernel_co.npy                      (63-term phase kernel)
  * artifacts/115/recipes/cx569/*.pkl                        (loader rotation supports, optional)
  * results/verified_circuits.csv                            (scripts/collect_results.py)

Usage:
    python scripts/make_figures.py            # writes docs/figures/fig*.png
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import pickle
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
# pyrefly: ignore [missing-import]
import verify_circuit as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
BEST = ROOT / "artifacts/111/conditional_loader_111_cx557.qasm"

# Okabe-Ito palette (colour-blind safe)
C_X, C_Y, C_K = "#0072B2", "#E69F00", "#009E73"
C_ACC, C_GREY, C_INK = "#D55E00", "#8C8C8C", "#222222"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "normal",
    "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.8, "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
    "mathtext.fontset": "dejavusans",
})


def panel(ax, letter, x=-0.12, y=1.04):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="left")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)
    print("wrote", (OUT / f"{name}.png").relative_to(ROOT))


def logo_matrix():
    return np.array([[vc.logo(x, y) for x in range(64)] for y in range(64)], dtype=int)  # [y, x]


def gate_layers(gates, n=18):
    front = [0] * n
    layers = []
    for g in gates:
        wires = (g[1], g[2]) if g[0] == "cx" else (g[1],)
        t = max(front[w] for w in wires) + 1
        for w in wires:
            front[w] = t
        layers.append(t)
    return layers, max(front)


def classify(gates, layers, iface):
    """Attribute each gate to a stage.

    Code wire w with ready time r_w carries the phase kernel in layers r_w+1 .. T-r_w.  A gate belongs to the
    kernel when every wire it touches is a code wire inside its window; otherwise it belongs to the loader
    (first half) or the unloader (second half) of its side."""
    T = iface["T"]
    side = {q: s for s, qs in iface["side_qubits"].items() for q in qs}
    ready = {c["qubit"]: c["ready"] for c in iface["code_wires"]}
    stages = []
    for g, t in zip(gates, layers):
        wires = (g[1], g[2]) if g[0] == "cx" else (g[1],)
        if all(w in ready and ready[w] < t <= T - ready[w] for w in wires):
            stages.append("kernel")
        else:
            s = side[wires[0]]
            stages.append(f"{'load' if t <= T / 2 else 'unload'}_{s}")
    return stages


# --------------------------------------------------------------------------- figure 1
def fig_problem():
    M = logo_matrix()
    fig = plt.figure(figsize=(10.2, 3.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.1], wspace=0.32)

    ax = fig.add_subplot(gs[0])
    ax.imshow(M, origin="lower", cmap=matplotlib.colors.ListedColormap(["#F3F3F3", "#3B3B3B"]),
              extent=(-0.5, 63.5, -0.5, 63.5), interpolation="nearest")
    style = dict(fill=False, lw=1.0, ec=C_ACC)
    ax.add_patch(Rectangle((1.5, 28.5), 25, 25, **style))
    ax.add_patch(Rectangle((25.5, 38.5), 24, 5, **style))
    ax.add_patch(Circle((55, 41), np.sqrt(42), **style))
    ax.add_patch(Circle((40, 19), np.sqrt(72), **style))
    for txt, (tx, ty) in {"square": (14, 56), "bar": (38, 46), "disc $D_1$": (55, 50.5), "disc $D_2$": (40, 5)}.items():
        ax.text(tx, ty, txt, ha="center", va="center", fontsize=8, color=C_ACC)
    ax.set_xlim(-0.5, 63.5); ax.set_ylim(-0.5, 63.5)
    ax.set_xticks([0, 16, 32, 48, 63]); ax.set_yticks([0, 16, 32, 48, 63])
    ax.set_xlabel("x  (qubits q0–q5)"); ax.set_ylabel("y  (qubits q6–q11)")
    ax.set_title(f"Target: {M.sum():,} of 4,096 points marked", fontsize=9.5, pad=8)
    panel(ax, "a", x=-0.22, y=1.03)

    # b: rows and columns grouped by identical pattern
    ax = fig.add_subplot(gs[1])
    def classes(rows):
        pats, cls = {}, []
        for r in rows:
            cls.append(pats.setdefault(tuple(r), len(pats)))
        return np.array(cls), len(pats)
    ycls, ny = classes(M)          # row pattern for each y
    xcls, nx = classes(M.T)        # column pattern for each x
    # order classes by the position of their first member so the picture stays recognisable
    yo = np.argsort(ycls, kind="stable"); xo = np.argsort(xcls, kind="stable")
    ax.imshow(M[np.ix_(yo, xo)], origin="lower", cmap=matplotlib.colors.ListedColormap(["#F3F3F3", "#3B3B3B"]),
              extent=(-0.5, 63.5, -0.5, 63.5), interpolation="nearest")
    for b in np.flatnonzero(np.diff(ycls[yo])) + 0.5:
        ax.axhline(b, color=C_Y, lw=0.7)
    for b in np.flatnonzero(np.diff(xcls[xo])) + 0.5:
        ax.axvline(b, color=C_X, lw=0.7)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel(f"x grouped into {nx} column classes", color=C_X)
    ax.set_ylabel(f"y grouped into {ny} row classes", color=C_Y)
    ax.set_title("Rows and columns grouped by pattern", fontsize=9.5, pad=8)
    panel(ax, "b", x=-0.2, y=1.03)

    # c: size of the phase description
    ax = fig.add_subplot(gs[2])
    F = np.array([1 - 2 * vc.logo(i % 64, i // 64) for i in range(4096)], float)
    Hn = np.array([[1.0]])
    for _ in range(12):
        Hn = np.block([[Hn, Hn], [Hn, -Hn]])
    walsh = int(np.sum(np.abs((Hn @ F)[1:]) > 1e-9))          # non-constant parity terms of f
    co = np.load(ROOT / "artifacts/115/recipes/kernel_co.npy")
    kterms = int(np.sum(np.abs(co[1:]) > 1e-10))
    rot = {}
    for s, p in {"x": "artifacts/115/recipes/cx569/x_loader_xg_r36_32_1.pkl",
                 "y": "artifacts/115/recipes/cx569/y_loader_v34_1_yw005_3.pkl"}.items():
        try:
            D = pickle.load(open(ROOT / p, "rb"))
            rot[s] = sum(len(D["targets"][i]) for i in range(3))
        except Exception:
            rot[s] = 89
    labels = ["parity terms of $f$ on the 12 input bits",
              "phase-kernel terms on the 8 code bits",
              "x-loader rotations (3 label bits)", "y-loader rotations (3 label bits)"]
    vals = [walsh, kterms, rot["x"], rot["y"]]
    cols = [C_GREY, C_K, C_X, C_Y]
    yy = np.arange(len(vals))[::-1] * 1.0
    ax.barh(yy, vals, color=cols, height=0.42)
    for y0, v, lab in zip(yy, vals, labels):
        ax.text(10.5, y0 + 0.36, lab, va="center", ha="left", fontsize=8)
        ax.text(v * 1.1, y0, f"{v:,}", va="center", fontsize=8.5, fontweight="bold")
    ax.set_xscale("log"); ax.set_xlim(10, 3e4); ax.set_ylim(-0.45, 3.75)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_xlabel("number of parity rotations (log scale)")
    ax.set_title("Size of the phase polynomial", fontsize=9.5, pad=8)
    ax.set_box_aspect(0.86)
    panel(ax, "c", x=-0.04, y=1.03)
    save(fig, "fig1_problem")


# --------------------------------------------------------------------------- figure 2
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(10.2, 3.4))
    ax.set_xlim(0, 111); ax.set_ylim(-1.6, 10.9)
    ax.axis("off")
    T = 111
    bands = {"x": (6.2, 9.8), "y": (0.2, 3.8)}
    for s, (lo, hi) in bands.items():
        col = C_X if s == "x" else C_Y
        n = "x" if s == "x" else "y"
        ax.text(-1.5, (lo + hi) / 2, f"{n} register\n6 inputs + 3 ancillas", ha="right", va="center", fontsize=8.5, color=col)
        for k in range(9):
            yk = lo + (hi - lo) * (k + 0.5) / 9
            ax.plot([0, T], [yk, yk], color="#D9D9D9", lw=0.6, zorder=0)
    rx, ry = 43, 45                                           # latest code bit per side
    def box(x0, x1, lo, hi, fc, text, tc="white", fs=8.5):
        ax.add_patch(FancyBboxPatch((x0, lo), x1 - x0, hi - lo, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc=fc, ec="none", zorder=2))
        ax.text((x0 + x1) / 2, (lo + hi) / 2, text, ha="center", va="center", color=tc, fontsize=fs, zorder=3)
    box(0.5, rx, 6.4, 9.6, C_X, "x loader  $U_x$\n$|x\\rangle|0\\rangle \\mapsto |x\\rangle|c(x)\\rangle$\nlabels closed onto 3 wires")
    box(T - rx, T - 0.5, 6.4, 9.6, C_X, "x unloader  $U_x^{\\dagger}$")
    box(0.5, ry, 0.4, 3.6, C_Y, "y loader  $U_y$\n$|y\\rangle|0\\rangle \\mapsto |y\\rangle|c(y)\\rangle$")
    box(T - ry, T - 0.5, 0.4, 3.6, C_Y, "y unloader  $U_y^{\\dagger}$")
    # kernel spanning both registers
    box(ry + 1.2, T - ry - 1.2, 0.4, 9.6, C_K,
        "phase kernel\n$e^{i\\pi F(c_x, c_y)}$\n63 parity\nrotations on\n8 code wires", fs=8.2)
    ax.text(rx / 2, 6.1, "ready: code bits at layers 39, 40, 41, 43", ha="center", va="top", fontsize=7.5, color=C_X)
    ax.text(ry / 2, 0.1, "ready: code bits at layers 33, 37, 39, 45", ha="center", va="top", fontsize=7.5, color=C_Y)
    ax.annotate("", xy=(0, -0.75), xytext=(T, -0.75), arrowprops=dict(arrowstyle="<->", lw=0.8, color=C_INK))
    ax.text(T / 2, -0.95, "111 layers", ha="center", va="top", fontsize=8.5)
    ax.text(T / 2, 10.45, r"$U = (U_x^{\dagger} \otimes U_y^{\dagger})\; K \;(U_x \otimes U_y)$,   "
            r"$K = \exp\,(\,i \sum_S \theta_S\, p_S(c_x, c_y))$,   $p_S$ = parity of the code bits in $S$",
            ha="center", va="center", fontsize=9, color="#333333")
    save(fig, "fig2_pipeline")


# --------------------------------------------------------------------------- figure 3
def fig_schedule():
    iface = json.loads((ROOT / "docs/figures/data/interface_111.json").read_text())
    n, gates, _ = vc.parse_qasm(ROOT / iface["circuit"])
    layers, T = gate_layers(gates, n)
    stages = classify(gates, layers, iface)
    col = {"load_x": C_X, "unload_x": C_X, "load_y": C_Y, "unload_y": C_Y, "kernel": C_K}
    order = [0, 1, 2, 3, 4, 5, 15, 16, 17, 6, 7, 8, 9, 10, 11, 12, 13, 14]     # x register, then y register
    row = {q: len(order) - 1 - i for i, q in enumerate(order)}
    code = {c["qubit"]: c for c in iface["code_wires"]}

    fig = plt.figure(figsize=(10.2, 5.1))
    gs = fig.add_gridspec(2, 1, height_ratios=[4.2, 1.2], hspace=0.06)
    ax = fig.add_subplot(gs[0])
    for g, t, s in zip(gates, layers, stages):
        wires = (g[1], g[2]) if g[0] == "cx" else (g[1],)
        for w in wires:
            ax.add_patch(Rectangle((t - 1, row[w] + 0.08), 1, 0.84, fc=col[s], ec="none",
                                   alpha=1.0 if g[0] == "cx" else 0.45))
        if g[0] == "cx":
            ax.plot([t - 0.5, t - 0.5], [row[g[1]] + 0.5, row[g[2]] + 0.5], color="#333333", lw=0.2, alpha=0.25)
    for q, c in code.items():                                   # kernel window brackets
        ax.plot([c["ready"], T - c["ready"]], [row[q] + 0.5] * 2, color="black", lw=0.6, alpha=0.0)
        ax.text(T + 0.8, row[q] + 0.5, f"code bit, ready {c['ready']}", va="center", fontsize=7, color=C_K)
    ax.axhline(8.98, color="#555555", lw=0.6)
    names = {**{i: f"x{i}" for i in range(6)}, **{6 + i: f"y{i}" for i in range(6)}, **{12 + i: "anc" for i in range(6)}}
    ax.set_yticks([row[q] + 0.5 for q in order])
    ax.set_yticklabels([f"{names[q]}  q{q}" for q in order], fontsize=7)
    ax.set_xlim(0, T); ax.set_ylim(0, 18)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_title("Gate-level schedule of the champion 111-layer circuit (557 CX, 423 U3)", fontsize=10, pad=22)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=C_X, label="x loader / unloader"), Patch(fc=C_Y, label="y loader / unloader"),
                       Patch(fc=C_K, label="phase kernel"), Patch(fc="#999999", label="CX (solid)"),
                       Patch(fc="#999999", alpha=0.45, label="single-qubit U3 (light)")],
              ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7.5, handlelength=1.2)

    ax2 = fig.add_subplot(gs[1])
    counts = {k: np.zeros(T) for k in ["load_x", "load_y", "kernel", "unload_x", "unload_y"]}
    for g, t, s in zip(gates, layers, stages):
        counts[s][t - 1] += 2 if g[0] == "cx" else 1
    xs = np.arange(1, T + 1)
    bottom = np.zeros(T)
    for key, c in [("load_x", C_X), ("unload_x", C_X), ("load_y", C_Y), ("unload_y", C_Y), ("kernel", C_K)]:
        ax2.bar(xs - 0.5, counts[key], bottom=bottom, width=1.0, color=c, linewidth=0)
        bottom += counts[key]
    ax2.axhline(18, color=C_GREY, lw=0.6, ls="--")
    ax2.text(1, 18.6, "18 qubits", fontsize=7, color=C_GREY, va="bottom")
    ax2.set_xlim(0, T); ax2.set_ylim(0, 21)
    ax2.set_ylabel("busy\nqubits", fontsize=8)
    ax2.set_xlabel("layer")
    save(fig, "fig3_schedule")
    return gates, layers, stages, iface


# --------------------------------------------------------------------------- figure 4
def fig_interface(gates, layers, stages, iface):
    T = iface["T"]
    cws = sorted(iface["code_wires"], key=lambda c: (c["side"], c["ready"]))
    fig, ax = plt.subplots(figsize=(10.2, 3.0))
    for i, c in enumerate(cws):
        y = len(cws) - 1 - i
        col = C_X if c["side"] == "x" else C_Y
        r = c["ready"]
        ax.barh(y, r, left=0, color=col, alpha=0.85, height=0.62)
        ax.barh(y, r, left=T - r, color=col, alpha=0.85, height=0.62)
        ax.barh(y, T - 2 * r, left=r, color=C_K, alpha=0.18, height=0.62)
        ks = [t for g, t, s in zip(gates, layers, stages) if s == "kernel" and c["qubit"] in ((g[1], g[2]) if g[0] == "cx" else (g[1],))]
        kc = [t for g, t, s in zip(gates, layers, stages) if s == "kernel" and g[0] == "cx" and c["qubit"] in (g[1], g[2])]
        ax.scatter(np.array(ks) - 0.5, [y] * len(ks), s=6, color=C_K, zorder=3, marker="s", linewidths=0)
        ax.text(r / 2, y, f"ready {r}", ha="center", va="center", color="white", fontsize=7.5)
        ax.text(T + 1, y, f"window {T - 2 * r:>2}, used {len(ks):>2}", va="center", fontsize=7.5, family="DejaVu Sans Mono")
        ax.text(-1, y, f"{c['side']} code (q{c['qubit']})", ha="right", va="center", fontsize=7.8, color=col)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_xlim(0, T); ax.set_xlabel("layer")
    ax.axvline(T / 2, color="#999999", lw=0.6, ls=":")
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    ax.legend(handles=[Patch(fc=C_X, label="x loader / unloader"), Patch(fc=C_Y, label="y loader / unloader"),
                       Patch(fc=C_K, alpha=0.18, label="kernel window"),
                       Line2D([], [], color=C_K, marker="s", ls="none", ms=3, label="layer with a kernel gate")],
              ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7.5, handlelength=1.2)
    ax.set_title("Kernel windows of the eight code wires (T = 111)", fontsize=9.5, pad=20)
    save(fig, "fig4_interface")


# --------------------------------------------------------------------------- figure 5
# Clean era descriptions with staggered vertical positions for zero overlap and no broken hyphens
ERAS = [
    (0.0, 2.5, "lookups &\nmultiplexers", 900),
    (2.5, 4.5, "comparator &\ndistrib. lookup", 750),
    (4.5, 8.5, "class codes +\n8-bit phase kernel", 900),
    (8.5, 10.5, "conditional\nloaders", 750),
    (10.5, 20.3, "loader–kernel co-design\n(ready times, mod-2π lift,\nexact scheduling, relabeling)", 900),
]


def fig_progress():
    rows = list(csv.DictReader(open(ROOT / "results/verified_circuits.csv")))
    for r in rows:
        r["depth"] = int(r["depth"])
        r["cx"] = int(r["cx"])
        r["date"] = dt.date.fromisoformat(r["date_added"]) if r["date_added"] else None
    start = dt.date(2026, 9, 8)
    dated = sorted([r for r in rows if r["date"] and r["depth"] < 600], key=lambda r: (r["date"], -r["depth"]))

    fig = plt.figure(figsize=(10.2, 3.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.22)

    # ----------------------------------------------------------------------- Panel (a)
    ax = fig.add_subplot(gs[0])

    for k, (d0, d1, lab, y_pos) in enumerate(ERAS):
        ax.axvspan(d0, d1, color="#000000", alpha=0.035 if k % 2 == 0 else 0.0, lw=0)
        ax.text((d0 + d1) / 2, y_pos, lab, ha="center", va="top", fontsize=7.2, color="#444444", linespacing=1.15)

    best, pts = 10 ** 9, []
    for r in dated:
        if r["depth"] < best:
            best = r["depth"]
            day = float((r["date"] - start).days)
            if best == 113 and pts and pts[-1][0] == day:
                day += 0.3  # stagger day 19 progress for 114 -> 113
            elif best == 112 and pts and pts[-1][0] == day:
                day += 0.6  # stagger day 19 progress for 113 -> 112
            elif best == 111 and pts and pts[-1][0] == day:
                day += 0.9  # stagger day 19 progress for 112 -> 111
            pts.append((day, best))

    ax.scatter([(r["date"] - start).days for r in dated], [r["depth"] for r in dated],
               s=10, color=C_GREY, zorder=2, linewidths=0, label="other verified circuits")

    xs = [p[0] for p in pts] + [20.2]
    ys = [p[1] for p in pts] + [pts[-1][1]]
    ax.step(xs, ys, where="post", color=C_INK, lw=1.3, zorder=3, label="best verified depth")

    # Star marker for depth 111 (current best depth); non-star for historical points
    non_champ = [p for p in pts if p[1] > 111]
    ax.scatter([p[0] for p in non_champ], [p[1] for p in non_champ],
               s=14, color=C_INK, marker="o", zorder=4)

    champ_pts = [p for p in pts if p[1] == 111]
    if champ_pts:
        ax.scatter([p[0] for p in champ_pts], [p[1] for p in champ_pts],
                   s=48, marker="*", color=C_INK, zorder=5)

    for d, v in pts:
        if v in (524, 456, 224, 185, 124, 118, 115, 111):
            ox, oy = (3, 4)
            if v == 115:
                ox, oy = (-6, 5)
            elif v == 111:
                ox, oy = (5, -3)
            ax.annotate(str(v), xy=(d, v), xytext=(ox, oy), textcoords="offset points",
                        fontsize=7.5, color=C_INK)

    ax.set_yscale("log")
    ax.set_ylim(95, 1050)
    ax.set_xlim(-0.3, 20.8)
    ax.set_xticks(range(0, 21, 2))
    ax.set_yticks([111, 150, 200, 300, 500])
    ax.set_yticklabels(["111", "150", "200", "300", "500"])
    ax.minorticks_off()
    ax.set_xlabel("days since the first verified circuit (8 Sept 2026)")
    ax.set_ylabel("depth (log scale)")
    ax.legend(loc="lower left", fontsize=7.5)
    ax.set_title("Best verified depth over the project  (default synthesis: 5,329)", fontsize=9.5)
    panel(ax, "a", x=-0.1)

    # ----------------------------------------------------------------------- Panel (b)
    ax = fig.add_subplot(gs[1])
    sub = [r for r in rows if r["depth"] <= 125]

    # Non-milestone points: subtle grey circles
    ax.scatter([r["cx"] for r in sub], [r["depth"] for r in sub],
               s=16, color=C_GREY, marker="o", linewidths=0, zorder=2)

    # Pareto front line:
    pareto_pts = [(557, 111), (564, 114), (565, 116), (576, 117), (584, 121), (618, 123), (626, 125)]
    px = [p[0] for p in pareto_pts]
    py = [p[1] for p in pareto_pts]
    ax.plot(px, py, color="#444444", linestyle="--", lw=1.1, zorder=3, label="Pareto front")

    # Submitted circuit: 111 / 557 CX (prominent star marker)
    ax.scatter(557, 111, color=C_INK, marker="*", s=110, zorder=8)
    ax.annotate("111 / 557 CX\n(submitted)", xy=(557, 111), xytext=(-8, 0), textcoords="offset points",
                fontsize=7.5, ha="right", va="center", color=C_INK, fontweight="bold")

    # Key historical frontier milestones:
    anchors = [
        (564, 114, "114 / 564 CX", (-8, 2), "right", "bottom"),
        (565, 116, "116 / 565 CX", (-8, 2), "right", "bottom"),
        (584, 121, "121 / 584 CX", (-8, 2), "right", "bottom"),
        (626, 125, "125 / 626 CX", (-8, 2), "right", "bottom"),
    ]
    for x, y, text, off, ha, va in anchors:
        ax.scatter(x, y, color=C_INK, marker="o", s=22, zorder=5)
        ax.annotate(text, xy=(x, y), xytext=off, textcoords="offset points",
                    fontsize=7.5, ha=ha, va=va, color=C_INK)

    ax.set_xlabel("CX count")
    ax.set_ylabel("depth")
    ax.set_xlim(525, 638)
    ax.set_ylim(108.5, 126.5)
    ax.set_yticks([111, 113, 115, 117, 119, 121, 123, 125])
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    ax.set_title("Depth and CX count of verified circuits (depth ≤ 125)", fontsize=9.5)
    panel(ax, "b", x=-0.16)
    save(fig, "fig5_progress")


# --------------------------------------------------------------------------- figure 6
def fig_verification():
    rep = vc.verify(BEST)
    err = rep["per_input_error"]
    fig = plt.figure(figsize=(10.2, 3.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1.12, 1.1], wspace=0.66)
    M = logo_matrix()
    # a: sign of the simulated diagonal
    n, gates, _ = vc.parse_qasm(BEST)
    idx, amp, _, _ = vc.simulate_basis_inputs(gates)
    home = idx == np.arange(4096)[:, None]
    diag = np.sum(amp * home, axis=1)
    diag = diag / (diag[0] / abs(diag[0]))
    ax = fig.add_subplot(gs[0])
    ax.imshow(diag.real.reshape(64, 64), origin="lower", cmap=matplotlib.colors.ListedColormap(["#3B3B3B", "#F3F3F3"]),
              vmin=-1, vmax=1, interpolation="nearest")
    ax.set_title("Simulated sign of $\\langle x,y,0|U|x,y,0\\rangle$", fontsize=9.5)
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.set_xticks([0, 32, 63]); ax.set_yticks([0, 32, 63])
    mism = int(np.sum(np.sign(diag.real.reshape(64, 64)) != (1 - 2 * M)))
    ax.set_xlabel(f"x      (mismatches with target: {mism})")
    panel(ax, "a", x=-0.25)

    ax = fig.add_subplot(gs[1])
    im = ax.imshow(np.log10(err.reshape(64, 64) + 1e-18), origin="lower", cmap="viridis", interpolation="nearest")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.set_title("log$_{10}$\nerror", fontsize=7.5)
    ax.set_title("Error per input", fontsize=9.5)
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.set_xticks([0, 32, 63]); ax.set_yticks([0, 32, 63])
    panel(ax, "b", x=-0.25)

    ax = fig.add_subplot(gs[2])
    ax.hist(np.log10(err + 1e-18), bins=40, color=C_K, alpha=0.85)
    ax.axvline(np.log10(err.max()), color=C_ACC, lw=1)
    ax.text(np.log10(err.max()), ax.get_ylim()[1] * 0.92, f" max {err.max():.1e}", color=C_ACC, fontsize=7.8)
    ax.set_xlabel("log$_{10}$ | amplitude error |  (all 4,096 inputs)")
    ax.set_ylabel("number of inputs")
    ax.set_title("Distribution over all inputs", fontsize=9.5)
    panel(ax, "c", x=-0.2)
    save(fig, "fig6_verification")


if __name__ == "__main__":
    fig_problem()
    fig_pipeline()
    g, l, s, i = fig_schedule()
    fig_interface(g, l, s, i)
    fig_progress()
    fig_verification()
