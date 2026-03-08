from matplotlib import ticker
import numpy as np

from get_results import get_all_solver_data, eprint, TOOLS, TOOL_LABELS
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.transforms as transforms
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
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
    "#F0E442",
    "#009E73",
    "#D55E00",
]

MARKERS = [
    "x",
    "o",
    "v",
    "^",
    "s",
    "p",
]
PLOT_PATH = "/users/grad/mmcilree/projects/TrimmerExperiments/plots"
if not os.path.exists(PLOT_PATH):
    PLOT_PATH = "/Users/matthewmcilree/PhD_Code/TrimmerExperiments/plots"

NUM_ROWS = 3
NUM_COLS = 2


AX_REL_TRANSFORM = lambda ax: transforms.blended_transform_factory(
    ax.transAxes, ax.transAxes
)
AX_REL_X_TRANSFORM = lambda ax: transforms.blended_transform_factory(
    ax.transData, ax.transAxes
)
AX_REL_Y_TRANSFORM = lambda ax: transforms.blended_transform_factory(
    ax.transAxes, ax.transData
)


def ax_relative_line(ax, horizontal, dist, color, style, label):
    x_rel = (1, dist) if horizontal else (dist, 1)
    y_rel = (2, dist) if horizontal else (dist, 2)
    ax.axline(
        x_rel,
        y_rel,
        color=color,
        ls=style,
        transform=AX_REL_TRANSFORM(ax),
        label=label,
        clip_on=False,
        zorder=-1,
    )

    # Push the subplot inward to leave room for overflow content
    if dist > 1:
        pos = ax.get_position()
        if horizontal:
            ax.set_position([pos.x0, pos.y0, pos.width, pos.height * dist])
        else:
            ax.set_position([pos.x0, pos.y0, pos.width * dist, pos.height])


def single_scatter_plot(
    solver, ax: Axes, df, x_fields, y_fields, color, marker, size=15
):
    df = dfs[solver]

    x_data = df[x_fields].sum(axis=1)
    y_data = df[y_fields].sum(axis=1)
    ax.set_ylim(ymin=y_data.min(), ymax=y_data.max())
    ax.set_xlim(xmin=x_data.min(), xmax=x_data.max())
    x_mask = pd.Series(False, index=df.index)
    for tool in ["trim", "verif_trim"]:
        x_mask = x_mask | (df[f"{tool}_succeeded"] == False)
    y_mask = pd.Series(False, index=df.index)
    for tool in ["elab", "verif_elab"]:
        y_mask = y_mask | (df[f"{tool}_succeeded"] == False)

    x_only_mask = x_mask & ~y_mask
    y_only_mask = y_mask & ~x_mask
    x_fail_data = x_data[x_only_mask]
    y_fail_data = y_data[y_only_mask]
    mask = pd.Series(True, index=df.index)
    for tool in TOOLS:
        mask = mask & (df[f"{tool}_succeeded"] == True)

    x_data = x_data[mask]
    y_data = y_data[mask]

    if any(x_data > 0) and any(y_data > 0):
        ax.scatter(
            x_data,
            y_data,
            marker=marker,
            facecolors="none" if marker != "x" else color,
            lw=0.9,
            color=color,
            s=size,
        )

        ax.scatter(
            x_fail_data,
            np.ones(len(x_fail_data)) * 1.05,
            marker=marker,
            facecolors="none" if marker != "x" else color,
            lw=0.9,
            color=color,
            s=size,
            clip_on=False,
            transform=AX_REL_X_TRANSFORM(ax),
        )

        ax.scatter(
            np.ones(len(y_fail_data)) * 1.05,
            y_fail_data,
            marker=marker,
            facecolors="none" if marker != "x" else color,
            lw=0.9,
            color=color,
            s=size,
            clip_on=False,
            transform=AX_REL_Y_TRANSFORM(ax),
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(solver, y=1.1, fontsize=14, fontweight="bold", pad=5, color="#222222")
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
    for solver, color, marker in zip(SOLVERS, COLORS, MARKERS):
        df = dfs[solver]
        single_scatter_plot(
            solver, axes[row][col], df, x_fields, y_fields, color, marker
        )
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

    fig.tight_layout()
    fig.savefig(
        PLOT_PATH + "/scatter_plots.pdf", bbox_inches="tight", dpi=300, pad_inches=1
    )
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

        overflow = 0.1
        ax_pos = ax.get_position()
        fig_width, fig_height = fig.get_size_inches()
        extra_x = ax_pos.width * fig_width * overflow
        extra_y = ax_pos.height * fig_height * overflow

        from matplotlib.transforms import Bbox

        extent = Bbox(
            [[extent.x0, extent.y0], [extent.x1 + extra_x, extent.y1 + extra_y]]
        )

        fig.savefig(
            f"{PLOT_PATH}/{solver}_scatter.pdf",
            bbox_inches=extent,
            dpi=300,
            backend=SAVE_FIG_BACKEND,
        )
