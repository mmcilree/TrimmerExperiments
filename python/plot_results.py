from matplotlib import ticker

from get_results import get_all_solver_data, eprint, TOOLS, TOOL_LABELS
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import pandas as pd

SOLVERS = [
    "clique",
    "cp",
    "kissat-satsuma",
    "pacose",
    "roundingsat",
    "sip",
]


COLORS = [
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]


def single_scatter_plot(solver, ax: Axes, x_field, y_field, color, size=8):
    if any(x_field > 0) and any(y_field > 0):
        ax.scatter(x_field, y_field, marker="X", color=color, s=size)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(solver, fontsize=14, fontweight="bold", pad=3, color="#222222")
    ax.tick_params(axis="both", which="both", labelsize=11, length=3)
    ax.xaxis.set_major_formatter(ticker.LogFormatterSciNotation(labelOnlyBase=True))
    ax.yaxis.set_major_formatter(ticker.LogFormatterSciNotation(labelOnlyBase=True))
    ax.axline((1, 1), (10, 10), color="#aaaaaa", lw=0.8, ls="--", zorder=1)


def scatter_plots_for_each_solver(dfs, x_fields, y_fields):
    NUM_ROWS = 3
    NUM_COLS = 2
    fig, axes = plt.subplots(
        NUM_ROWS,
        NUM_COLS,
        figsize=(8.3, 11.7),
        squeeze=False,
    )

    row = 0
    col = 0
    used = set()
    for solver, color in zip(SOLVERS, COLORS):
        df = dfs[solver]
        mask = pd.Series(True, index=df.index)
        for tool in TOOLS:
            mask = mask & (df[f"{tool}_succeeded"] == 0)
        df = df[mask]
        x_data = df[x_fields].sum(axis=1)
        y_data = df[y_fields].sum(axis=1)
        single_scatter_plot(solver, axes[row][col], x_data, y_data, color)
        used.add((row, col))
        row = (row + 1) % NUM_ROWS
        col = (col + 1) if row == 0 else col

    for r in range(NUM_ROWS):
        for c in range(NUM_COLS):
            if (r, c) not in used:
                axes[r][c].set_visible(False)
    return fig


def success_counts(df: pd.DataFrame, tool: str) -> tuple[int, int]:
    col = f"{tool}_succeeded"
    time_exit = f"{tool}_time_exit_code"

    if col not in df.columns:
        return 0, 0
    n_failed = int(df[col].sum())
    n_succeeded = len(df) - n_failed
    n_timeout = len(df[df[time_exit] == 124])
    n_failed -= n_timeout
    return n_succeeded, n_timeout, n_failed


def single_bar_chart(solver: str, ax: Axes, df: pd.DataFrame, color: str):
    succeeded = []
    failed = []
    timeout = []
    for tool in TOOLS:
        s, t, f = success_counts(df, tool)
        succeeded.append(s)
        failed.append(f)
        timeout.append(t)

    x = range(len(TOOLS))
    ax.bar(x, succeeded, color=color, alpha=0.85, label="succeeded")
    ax.bar(x, failed, bottom=succeeded, color="#888888", alpha=0.85, label="failed")
    bottom_timeout = [s + f for s, f in zip(succeeded, failed)]
    ax.bar(
        x,
        timeout,
        bottom=bottom_timeout,
        color="#cccccc",
        alpha=0.85,
        label="timeout",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(TOOL_LABELS, fontsize=12, rotation=30, ha="right")
    ax.set_title(solver, fontsize=14, fontweight="bold", pad=3, color="#1B1010")
    ax.tick_params(axis="y", labelsize=11)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))


def bar_charts_for_each_solver(dfs: dict) -> Figure:
    NUM_ROWS = 3
    NUM_COLS = 2
    fig, axes = plt.subplots(
        NUM_ROWS,
        NUM_COLS,
        figsize=(8.3, 11.7),
        squeeze=False,
    )

    row = 0
    col = 0
    used = set()
    legend_added = False
    for solver, color in zip(SOLVERS, COLORS):
        ax = axes[row][col]
        single_bar_chart(solver, ax, dfs[solver], color)
        if not legend_added:
            ax.legend(fontsize=12, loc="upper right")
            legend_added = True
        used.add((row, col))
        row = (row + 1) % NUM_ROWS
        col = (col + 1) if row == 0 else col

    for r in range(NUM_ROWS):
        for c in range(NUM_COLS):
            if (r, c) not in used:
                axes[r][c].set_visible(False)

    return fig


if __name__ == "__main__":
    dfs = get_all_solver_data()
    fig = scatter_plots_for_each_solver(
        dfs, ["elab_time", "verif_elab_time"], ["trim_time", "verif_trim_time"]
    )
    fig.suptitle(
        "Trimmer Time + CakePB Check Time (s)\nvs. VeriPB Elab. Time + CakePB Check Time (s)\n(Where all of the above succeeded)",
        y=0.98,
        fontsize=16,
    )

    fig.tight_layout(rect=[0.04, 0, 1, 0.96])
    fig.savefig("scatter_plots.pdf", bbox_inches="tight", dpi=300, pad_inches=1)
    fig_bars = bar_charts_for_each_solver(dfs)
    fig_bars.suptitle(
        "Failure Rates",
        y=0.98,
        fontsize=16,
    )

    fig_bars.tight_layout(rect=[0, 0, 1, 0.96])
    fig_bars.savefig("failure_rates.pdf", bbox_inches="tight", dpi=300, pad_inches=1)
