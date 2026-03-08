import argparse
import os
import re
import subprocess
import pandas as pd
import numpy as np
import sys
import inspect
from collections import namedtuple

SOLVERS = ["clique", "cp", "kissat-satsuma", "maxsat", "roundingsat", "sip", "umaxsat"]
RESULTS_DIRS = {
    "clique": "/cluster/ciaran/20260224-trimming/experiments/clique/results/glasgow-prove",
    "cp": "/cluster/ciaran/20260224-trimming/experiments/cp/results/gcs",
    "kissat-satsuma": "/cluster/ciaran/20260224-trimming/experiments/kissat-satsuma/results/kissat-satsuma",
    "maxsat": "/cluster/ciaran/20260224-trimming/experiments/maxsat/results/maxsat",
    "roundingsat": "/cluster/ciaran/20260224-trimming/experiments/roundingsat/results/roundingsat",
    "sip": "/cluster/ciaran/20260224-trimming/experiments/sip/results/glasgow-prove",
    "umaxsat": "/cluster/ciaran/20260224-trimming/experiments/umaxsat/results/uwmaxsat",
}

# on the nodes (01, 02, 03, 04, 07, 08, 09, 10)
PROOF_DIRS = {
    "clique": "/scratch/ciaran/20260224-trimming/clique-proofs",
    "cp": "/scratch/ciaran/20260224-trimming/cp-proofs",
    "kissat-satsuma": "/scratch/ciaran/20260224-trimming/kissat-satsuma-proofs",
    "maxsat": "/scratch/ciaran/20260224-trimming/maxsat-proofs",
    "roundingsat": "/scratch/ciaran/20260224-trimming/roundingsat-proofs",
    "sip": "/scratch/ciaran/20260224-trimming/sip-proofs",
    "umaxsat": "/scratch/ciaran/20260224-trimming/umaxsat-proofs",
}

ToolResult = namedtuple(
    "ToolResult",
    [
        "time",
        "exit_code",
        "peak_memory",
        "time_exit_code",
        "succeeded",
        "output_lines",
        "output_normalised",
    ],
)

RESULTS_EXTS = {
    "trim": {"time": ["trimtime"], "out": ["trimout"]},
    "elab": {
        "time": ["elaboratetime", "elaboratepbtime"],
        "out": ["elaborateout", "elaboratepbout"],
    },
    "verif_trim": {"time": ["cakeontrimtime"], "out": ["cakeontrimout"]},
    "verif_elab": {"time": ["cakeonelaboratetime"], "out": ["cakeonelaborateout"]},
}

SIZE_EXTS = {"orig": "pbp", "trim": "trimmedpb", "elab": "elaboratepb"}


TOOLS = ["trim", "elab", "verif_trim", "verif_elab"]
TOOL_LABELS = ["Trimmer", "VeriPB Elab.", "CakePB (on trim.)", "CakePB (on elab.)"]

CACHE_PATH = "/users/grad/mmcilree/projects/TrimmerExperiments/caches/"
if not os.path.exists(CACHE_PATH):
    CACHE_PATH = "/Users/matthewmcilree/PhD_Code/TrimmerExperiments/caches"


PROOFS_PATH = "/scratch/ciaran/20260224-trimming"
NODES = ["01", "02", "03", "04", "07", "08", "09"]

RE_PBP = re.compile(r"[^\s]*.pbp")
RE_PB_SUM = re.compile(r"((?:\d+ ~?x[\d_]+ ?)+)")
RE_POL_STATEMENT = re.compile(r"pol.*\\n")
RE_LIST_NUMS = re.compile(r"\d+ (\d+ )+")
RE_DIGITS = re.compile(r"\d+")
RE_EXPECTED_MSG = re.compile(r"Running VeriPB|Warning|Switched to proof version")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def dbg(val):
    frame = inspect.currentframe().f_back
    info = inspect.getframeinfo(frame)
    # Get the source line and extract the argument
    line = info.code_context[0].strip()
    print(f"[{info.filename}:{info.lineno}] {line} = {val!r}")
    return val


def tool_succeeded(tool, output_lines):
    if tool == "trim":
        return any("Proof is verified and Trimmed" in line for line in output_lines)
    elif (tool == "elab") or (tool == "verif_trim") or (tool == "verif_elab"):
        return any("s VERIFIED" in line for line in output_lines)
    else:
        raise ValueError(f"Unexpected tool value: {tool!r}")


def find_results_file(exts, results_dir, inst):
    for ext in exts:
        file_path = os.path.join(results_dir, inst + "." + ext)
        if os.path.exists(file_path):
            return file_path
    checked = [os.path.join(results_dir, inst + "." + ext) for ext in exts]
    eprint(f"Warning: results file missing; checked {checked}")
    return None


def parse_time(tool, results_dir, inst):
    file_path = find_results_file(RESULTS_EXTS[tool]["time"], results_dir, inst)
    if file_path is None:
        return (np.nan,) * 4

    lines = open(file_path).readlines()
    if not lines:
        eprint(f"Warning: {file_path} appears to be empty")
        return (np.nan,) * 4

    time_exit_status = 0
    if len(lines) > 1 and re.match(r"Command (exited|terminated)", lines[0]):
        time_exit_status = int(lines[0].split()[-1].strip())
    elif len(lines) > 1:
        eprint(f"Warning: {file_path} had unexpected lines:")
        eprint(*lines)

    split_line = tuple(lines[-1].strip().split() + [time_exit_status])
    if len(split_line) != 4:
        eprint(f"Warning: {file_path} did not split into 4 fields")
    return (float(split_line[0]), int(split_line[1]), int(split_line[2]), split_line[3])


def parse_output(tool, results_dir, inst):
    file_path = find_results_file(RESULTS_EXTS[tool]["out"], results_dir, inst)
    if file_path is None:
        return (np.nan, [], "")

    lines = open(file_path).readlines()
    if not lines:
        eprint(f"Warning: {file_path} appears to be empty")
        return (np.nan, [], "")

    msg = "".join(l for l in lines if not RE_EXPECTED_MSG.search(l))
    msg = msg.replace("\n", "\\n")
    msg = re.sub(RE_PBP, "<FILE>.pbp", msg)
    msg = re.sub(RE_PB_SUM, "<PB CONSTRAINT>", msg)
    msg = re.sub(RE_LIST_NUMS, "<LIST OF NUMS>", msg)
    msg = re.sub(RE_POL_STATEMENT, "<POL STATEMENT>", msg)
    if not ".rs" in msg:
        msg = re.sub(
            RE_DIGITS, "<N>", msg
        )  # replace all numbers, except rust line numbers

    if len(msg) >= 300:
        msg = msg[:300] + "<...truncated the rest>"
    return (True, lines, msg) if tool_succeeded(tool, lines) else (False, lines, msg)


def get_all_path_and_sizes_from_node(node, exts, dir):
    ext_pattern = " -o ".join(f"-name '*.{ext}'" for ext in exts)
    cmd = f"find {dir} \\( {ext_pattern} \\) -type f | xargs -I {{}} du -k {{}}"
    result = subprocess.run(
        ["ssh", "-tq", f"fataepyc-{node}", cmd], capture_output=True, text=True
    )
    sizes = {}
    file_paths = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            filename = os.path.basename(parts[1])
            sizes[filename] = int(parts[0])
            file_paths[filename] = f"fataepyc-{node}:" + parts[1]
    return sizes, file_paths


def get_all_paths_and_sizes(dir):
    sizes = {}
    file_paths = {}
    for node in NODES:
        eprint(f"Collecting sizes from fataepyc-{node}")
        sizes_from_node, paths_from_node = get_all_path_and_sizes_from_node(
            node, SIZE_EXTS.values(), dir
        )
        sizes.update(sizes_from_node)
        file_paths.update(paths_from_node)
    return sizes, file_paths


def collect_data(solver, force=False):
    cache_path = os.path.join(CACHE_PATH, f"{solver}.cache.parquet")

    if not force and os.path.exists(cache_path):
        return pd.read_parquet(cache_path)
    elif not force:
        eprint(f"No cache found {cache_path}")
        exit(1)

    sizes, paths = get_all_paths_and_sizes(PROOF_DIRS[solver])
    eprint(f"Results for {solver}")
    results_dir = RESULTS_DIRS[solver]
    if not os.path.exists(results_dir):
        eprint(f"Warning, results directory {results_dir} does not exist")
        return pd.DataFrame()

    all_results_files = os.listdir(results_dir)
    instances = set(".".join(file.split(".")[:-1]) for file in all_results_files)
    rows = []
    for inst in sorted(instances):
        row = {"instance": inst}
        for tool in RESULTS_EXTS:
            result = ToolResult(
                *parse_time(tool, results_dir, inst),
                *parse_output(tool, results_dir, inst),
            )
            for field in ToolResult._fields:
                row[f"{tool}_{field}"] = getattr(result, field)

        for tool, ext in SIZE_EXTS.items():
            size_key = f"{inst}.{ext}"
            row[f"{tool}_size"] = sizes.get(size_key, np.nan)
            row[f"{tool}_path"] = paths.get(size_key, "")

        rows.append(row)

    df = pd.DataFrame(rows).set_index("instance")
    df.to_parquet(cache_path)
    return df


def get_all_solver_data(force=False):
    dfs = {}
    for s in SOLVERS:
        dfs[s] = collect_data(s, force=force)

    # combine maxsat and umaxsat
    dfs["pacose"] = pd.concat([dfs["maxsat"], dfs["umaxsat"]])
    del dfs["maxsat"]
    del dfs["umaxsat"]
    return dfs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no_cache", action="store_true")
    args = parser.parse_args()
    dfs = get_all_solver_data(force=args.no_cache)
