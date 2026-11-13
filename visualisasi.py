"""Export journal figures from the same result files used by Streamlit."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
EVENT = "2026-11-12"
LABELS = {
    "abnormal_return_pp": ("Abnormal return", "Percentage points"),
    "abnormal_turnover_bp": ("Abnormal turnover", "Basis points of listed shares"),
    "net_foreign_deviation_bp": ("Net foreign trading", "Basis points of listed shares"),
}
COLORS = ["#21547B", "#C05D2B", "#168278"]


def export(fig, name):
    for extension in ("png", "pdf"):
        fig.savefig(FIGURES / f"{name}.{extension}", dpi=300, facecolor="white")
    plt.close(fig)


def main():
    FIGURES.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.labelcolor": "#26384A",
                         "text.color": "#172B3E", "pdf.fonttype": 42})
    stock = pd.read_csv(RESULTS / "per_saham.csv").query("date == @EVENT and variant == 'screened'")
    panel = stock.pivot(index="ticker", columns="metric", values="estimate").sort_values("abnormal_return_pp")
    fig, axes = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True, layout="constrained")
    fig.suptitle("Stock reactions on the MSCI announcement day", fontsize=17, fontweight="bold")
    for letter, ax, (metric, (label, unit)), color in zip("ABC", axes, LABELS.items(), COLORS):
        values = panel[metric]
        ax.barh(values.index, values, color=color, alpha=.9)
        ax.axvline(0, color="#65788A", lw=.9)
        ax.set_title(f"{letter}  {label}", loc="left", fontweight="bold")
        ax.set_xlabel(unit)
        ax.grid(axis="x", alpha=.20)
        ax.set_axisbelow(True)
    axes[0].invert_yaxis()
    fig.supxlabel("12 November 2026 · Nine affected stocks relative to screened controls · Point estimates", fontsize=9)
    export(fig, "Figure_1_Stock_reactions")

    placebos = pd.read_csv(RESULTS / "placebo.csv").query("variant == 'screened' and sample == 'all_9'")
    stats = pd.read_csv(RESULTS / "peringkat_placebo.csv").query(
        "variant == 'screened' and sample == 'all_9' and placebo_set == 'all_dates'"
    ).set_index("metric")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0), layout="constrained")
    fig.suptitle("Announcement-day estimates and historical placebos", fontsize=17, fontweight="bold")
    for letter, ax, (metric, (label, unit)), color in zip("ABC", axes, LABELS.items(), COLORS):
        x = placebos.loc[placebos["metric"].eq(metric), "estimate"]
        stat = stats.loc[metric]
        ax.hist(x, bins=17, color=color, alpha=.72, edgecolor="white")
        ax.axvline(stat["estimate"], color="#A03035", lw=2, label="12 November")
        ax.set_title(f"{letter}  {label}", loc="left", fontweight="bold")
        ax.set_xlabel(unit)
        ax.set_ylabel("Trading days")
        ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.supxlabel("120 synchronous placebos · Six held-out blocks · Exploratory historical reference", fontsize=9)
    export(fig, "Figure_2_Placebo_distributions")

    event = pd.read_csv(RESULTS / "ringkasan_peristiwa.csv").query("variant == 'screened' and sample == 'all_9'")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0), layout="constrained")
    fig.suptitle("Trading around the November announcement", fontsize=17, fontweight="bold")
    for letter, ax, (metric, (label, unit)), color in zip("ABC", axes, LABELS.items(), COLORS):
        values = event.loc[event["metric"].eq(metric)].sort_values("date")
        ax.plot([0, 1, 2], values["estimate"], color=color, marker="o", lw=1.8)
        ax.axhline(0, color="#8796A6", lw=.8)
        ax.axvline(1, color="#9A5158", ls="--", lw=.8)
        ax.set_xticks([0, 1, 2], ["11 Nov", "12 Nov", "13 Nov"])
        ax.set_title(f"{letter}  {label}", loc="left", fontweight="bold")
        ax.set_ylabel(unit)
    fig.supxlabel("12 November: MSCI announcement · 13 November: domestic HSC-related index changes", fontsize=9)
    export(fig, "Figure_3_Event_window")


if __name__ == "__main__":
    main()
