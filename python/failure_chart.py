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


def success_counts(df: pd.DataFrame, tool: str) -> tuple[int, int]:
    col = f"{tool}_succeeded"
    time_exit = f"{tool}_time_exit_code"

    if col not in df.columns:
        return 0, 0
    n_failed = len(df[df[col] == False])
    n_succeeded = len(df[df[col] == True])
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
    fig_bars = bar_charts_for_each_solver(dfs)
    fig_bars.suptitle(
        "Failure Rates",
        y=0.98,
        fontsize=16,
    )

    fig_bars.tight_layout(rect=[0, 0, 1, 0.96])
    fig_bars.savefig("failure_rates.pdf", bbox_inches="tight", dpi=300, pad_inches=1)
