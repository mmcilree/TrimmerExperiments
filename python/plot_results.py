from matplotlib import ticker

from get_results import get_all_solver_data, eprint, TOOLS, TOOL_LABELS
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import pandas as pd
import os
import shutil

# Latex style
if shutil.which("latex"):
    plt.rcParams.update(
        {
            "font.family": "serif",
            "text.usetex": True,
            "pgf.rcfonts": False,
            "pgf.texsystem": "pdflatex",
            "pgf.preamble": "\n".join(
                [
                    r"\usepackage[utf8x]{inputenc}",
                    r"\usepackage[T1]{fontenc}",
                ]
            ),
        }
    )
    SAVE_FIG_BACKEND = "pgf"
else:
    SAVE_FIG_BACKEND = "pdf"

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

PLOT_PATH = "/users/grad/mmcilree/projects/TrimmerExperiments/plots"
if not os.path.exists(PLOT_PATH):
    PLOT_PATH = "/Users/matthewmcilree/PhD_Code/TrimmerExperiments/plots"

NUM_ROWS = 3
NUM_COLS = 2


def single_scatter_plot(solver, ax: Axes, x_field, y_field, color, size=15):
    if any(x_field > 0) and any(y_field > 0):
        ax.scatter(x_field, y_field, marker="x", lw=0.9, color=color, s=size)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(solver, fontsize=14, fontweight="bold", pad=3, color="#222222")
    ax.tick_params(axis="both", which="both", labelsize=11, length=3)
    ax.grid(visible=True)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(ticker.LogFormatterSciNotation(labelOnlyBase=True))
    ax.yaxis.set_major_formatter(ticker.LogFormatterSciNotation(labelOnlyBase=True))
    ax.axline((1, 1), (10, 10), color="#aaaaaa", lw=0.8, ls="--", zorder=0)


def same_fig_separate_plots(dfs, x_fields, y_fields):
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
    return fig, axes


if __name__ == "__main__":
    dfs = get_all_solver_data()
    fig, axes = same_fig_separate_plots(
        dfs, ["elab_time", "verif_elab_time"], ["trim_time", "verif_trim_time"]
    )
    fig.suptitle(
        "Trimmer Time + CakePB Check Time (s)\nvs. VeriPB Elab. Time + CakePB Check Time (s)\n(Where all of the above succeeded)",
        y=0.98,
        fontsize=16,
    )

    fig.tight_layout(rect=[0.04, 0, 1, 0.96])
    fig.savefig(
        PLOT_PATH + "/scatter_plots.pdf", bbox_inches="tight", dpi=300, pad_inches=1
    )
    exit(0)
    for solver, (row, col) in zip(
        SOLVERS, [(r, c) for c in range(NUM_COLS) for r in range(NUM_ROWS)]
    ):
        ax = axes[row][col]
        # Temporarily hide the title
        title = ax.get_title()
        ax.set_title("")

        extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(
            fig.dpi_scale_trans.inverted()
        )
        fig.savefig(
            f"{PLOT_PATH}/{solver}_scatter.pdf",
            bbox_inches=extent,
            dpi=300,
            backend=SAVE_FIG_BACKEND,
        )
