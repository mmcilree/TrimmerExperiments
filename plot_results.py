import pandas as pd
import os
from pathlib import Path
import numpy as np
import argparse
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

# Use Serif Fonts
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

DEFAULT_SCATTER_PARAMS = {"s": 5, "alpha": 1, "linewidth": 0}


def parse_seconds(x):
    return float(x.rstrip("s"))


def read_results(results_file, propagations=False):
    df = pd.read_csv(
        results_file,
        sep=" ",
        dtype={
            "elaboratetime": "Float64",
            "elaborateresult": "Int64",
            "elaboratememory": "Int64",
            "cakeelaboratetime": "Float64",
            "cakeelaborateresult": "Int64",
            "trimtime": "Float64",
            "trimresult": "Int64",
            "trimmemory": "Int64",
            "caketrimtime": "Float64",
            "caketrimresult": "Int64",
            "caketrimmemory": "Int64",
        },
        na_values=["fail"],
    )

    return df


def scatter_plot_and_save(
    name,
    data_frames: list[pd.DataFrame],
    x_field,
    y_field,
    ax,
    plot_y_eq_x=True,
    plot_timeout=None,
    logscale=True,
    **kwargs,
):
    cmap = plt.get_cmap("Set1")  # or "tab10", "Dark2"
    colors = cmap.colors[2 : len(data_frames) + 2]
    markers = ["o", "v", "D", "s", "^", "v", "P", "X", "*"][
        : len(data_frames)
    ]  # distinct marker shapes
    has_memouts = False
    has_timeouts = False
    memout_shift = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    for df, color, marker in zip(data_frames, colors, markers):
        if y_field == "check time":
            memouts = df[df["exit code"] == 137]
            timeouts = df[df["exit code"] == 143]
            ax.scatter(
                memouts[x_field],
                np.ones(len(memouts)) * 1.05,
                transform=memout_shift,
                color=color,
                marker=marker,
                clip_on=False,
                **kwargs,
            )

            if len(memouts) > 0:
                has_memouts = True

            ax.scatter(
                timeouts[x_field],
                np.ones(len(timeouts)) * 7200,
                color=color,
                marker=marker,
                clip_on=False,
                **kwargs,
            )

        ax.scatter(
            df[x_field],
            df[y_field],
            color=color,
            marker=marker,
            **kwargs,
        )

    ax.set_xlabel(ax_labels[x_field])
    ax.set_ylabel(ax_labels[y_field])
    if logscale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_aspect("equal")
    # ax.set_box_aspect(1)
    ax.set_axisbelow(True)
    ax.grid()
    ax.grid(which="minor", alpha=0.3)

    if plot_y_eq_x:
        ax.axline(
            (0, 0), (1, 1), color="grey", alpha=0.8, lw=0.8, ls="--", label="$y = x$"
        )

    if has_memouts:
        ax.axline(
            (1, 1.05),
            (2, 1.05),
            lw=1,
            color="darkorange",
            ls=":",
            alpha=0.9,
            transform=memout_shift,
            label="8GB RAM limit",
            clip_on=False,
            zorder=-1,
        )

    if plot_timeout is not None:
        ax.axline(
            (1, 7200),
            (2, 7200),
            lw=0.8,
            color="red",
            ls="-",
            alpha=0.5,
            label="2 hr time limit",
        )

    if len(data_frames) > 1:
        ax.legend(frameon=True, markerscale=2)
    ax.minorticks_on()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_files", nargs="+")
    parser.add_argument("--split_column")
    parser.add_argument("--propagations", action="store_true")

    args = parser.parse_args()

    print("Reading input...")
    name = os.path.basename(args.results_files[0]).split("_")[0]
    dfs = []
    df_count = 0
    for file in args.results_files:
        df = read_results(file, propagations=args.propagations)
        split_df = [df]
        if args.split_column:
            split_df = [
                df[df[args.split_column] == True],
                df[df[args.split_column] == False],
            ]

        for df in split_df:
            dfs.append(df)
            df_count += 1

    ax_labels = {
        "elaboratetime": "Time for current VeriPB to elaborate",
        "cakeelaboratetime": "Time for CakePB to check elaborated proof",
        "trimtime": "Time for Trimmer to trim",
        "caketrimtime": "Time for CakePB to check trimmed proof",
    }

    fig, ax = plt.subplots(1, 2)
    scatter_plot_and_save(
        name, dfs, "elaboratetime", "cakeelaboratetime", ax[0], **DEFAULT_SCATTER_PARAMS
    )
    scatter_plot_and_save(
        name, dfs, "trimtime", "caketrimtime", ax[0], **DEFAULT_SCATTER_PARAMS
    )

    fig.savefig(args.results_files[0] + ".pdf", backend="pgf")
