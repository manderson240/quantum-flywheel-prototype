"""Figures for the prototype report, built only from the saved JSON in results/ (no API calls)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt


R = Path(__file__).parent / "results"
F = Path(__file__).parent / "figures"
COL = {"native": "#8a8f98", "rcm": "#1f6feb", "random": "#d29922"}


def fig_kicked_ising() -> None:
    rows = json.loads((R / "kicked_ising_hh3_s5.json").read_text())
    th = [r["theta_h"] for r in rows]
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    ax.plot(
        th,
        [r["exact"] if "exact" in r else r["exact_local"] for r in rows],
        "k-",
        lw=2,
        label="exact (local statevector)",
    )
    ax.plot(th, [r["pp_0.001"] for r in rows], "o--", color="#d29922", label="Pauli-path δ=1e-3")
    ax.plot(th, [r["pp_0.0001"] for r in rows], "s--", color="#1f6feb", label="Pauli-path δ=1e-4")
    ax.plot(
        th, [r["mps_chi32"] for r in rows], "^:", color="#8a8f98", label="MPS χ=32 (index order)"
    )
    ax.set_xlabel(r"$\theta_h$")
    ax.set_ylabel(r"$\langle M\rangle$")
    ax.set_title("19-qubit heavy-hex kicked Ising, 5 steps", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(F / "fig1_kicked_ising.png", dpi=200)


def fig_ordering() -> None:
    d = json.loads((R / "mps_ordering_hh3_s5.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, th, lab in zip(axes, ("pi4", "3pi8"), (r"$\theta_h=\pi/4$", r"$\theta_h=3\pi/8$")):
        for order in ("native", "random", "rcm"):
            pts = [
                (r["chi"], r["abs_err"])
                for r in d["runs"]
                if r["theta"] == th and r["order"] == order
            ]
            ax.plot(
                *zip(*pts),
                "o-",
                color=COL[order],
                label=f"{order} (bandwidth {d['bandwidth'][order]})",
            )
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xlabel(r"bond dimension $\chi$")
        ax.set_title(lab, fontsize=9)
    axes[0].set_ylabel(r"$|\langle M\rangle_{MPS}-\langle M\rangle_{exact}|$")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(F / "fig2_ordering.png", dpi=200)


def fig_otoc() -> None:
    p = R / "otoc2_echo_4x4_seeds7-11-13.json"
    if not p.exists():
        print("no OTOC^2 data yet")
        return
    rows = json.loads(p.read_text())
    methods = [
        k for k in rows[0] if k.startswith(("pp_", "mps_")) and not k.endswith(("_s", "_cost"))
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    labels = [f"s{r['seed']}·c{r['cycles']}" for r in rows]
    x = range(len(rows))
    ax.plot(x, [r["exact"] for r in rows], "k_", ms=18, mew=2.5, label="exact")
    for i, k in enumerate(methods):
        off = (i - len(methods) / 2) * 0.07
        lab = k.replace("pp_", "Pauli-path δ=").replace("mps_", "MPS χ=")
        ax.plot([xi + off for xi in x], [r[k] for r in rows], "o", ms=4, label=lab)
    ax.set_xticks(list(x), labels, fontsize=7, rotation=45)
    ax.set_ylabel(r"OTOC$^{(2)}$")
    ax.set_title(
        "16-qubit OTOC² echo circuits at the light-cone front (3 seeds × 4 depths)", fontsize=9
    )
    ax.legend(fontsize=6.5, ncol=7, loc="upper center", bbox_to_anchor=(0.5, -0.28), frameon=False)
    fig.tight_layout()
    fig.savefig(F / "fig3_otoc2.png", dpi=200, bbox_inches="tight")


def fig_bracket() -> None:
    p = R / "floquet_oracle19.json"
    if not p.exists():
        return
    rows = json.loads(p.read_text())
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True)
    for ax, ob in zip(axes, ("mag", "zzd2", "zzd3")):
        rr = [r for r in rows if r["obs"] == ob]
        c = [r["cycles"] for r in rr]
        lo = [r["pau_0.0001"] for r in rr]
        hi = [r["mps_64"] for r in rr]
        ax.fill_between(c, lo, hi, color="#1f6feb", alpha=0.15, label="bracket")
        ax.plot(c, hi, "^-", color="#8a8f98", ms=3, label="MPS χ=64 (too high)")
        ax.plot(c, lo, "v-", color="#d29922", ms=3, label="Pauli-path δ=1e-4 (too low)")
        ax.plot(c, [r["exact"] for r in rr], "k.-", lw=1.5, label="exact")
        ax.set_title({"mag": "magnetization", "zzd2": "ZZ, d=2", "zzd3": "ZZ, d=3"}[ob], fontsize=9)
        ax.set_xlabel("Floquet cycles")
    axes[0].set_ylabel("expectation value")
    axes[0].legend(fontsize=6, loc="upper left")
    fig.tight_layout()
    fig.savefig(F / "fig4_bracket19.png", dpi=200)


if __name__ == "__main__":
    F.mkdir(exist_ok=True)
    fig_kicked_ising()
    fig_ordering()
    fig_otoc()
    fig_bracket()
    print("figures:", sorted(p.name for p in F.glob("*.png")))
