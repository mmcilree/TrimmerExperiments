from get_results import get_all_solver_data, eprint, TOOLS, TOOL_LABELS
import re
from collections import Counter
from pathlib import Path
import subprocess

dfs = get_all_solver_data()

RE_PBP = re.compile(r"[^\s]*.pbp")
RE_PB_SUM = re.compile(r"((?:\d+ ~?x[\d_]+ ?)+)")
RE_POL_STATEMENT = re.compile(r"pol.*\\n")
RE_LIST_NUMS = re.compile(r"(\d+ )+")
RE_DIGITS = re.compile(r"\d+")
RE_IGNORE = re.compile(r"Running VeriPB|Warning|Switched to proof version")

INPUT_FILE_DIRS = {
    "pacose": [
        "/cluster/mse23-exact-unweighted-benchmarks/",
        "/cluster/mse23-exact-weighted-benchmarks/",
    ],
    "roundingsat": ["/cluster/roundingsat_proofs_to_trim/"],
    "kissat-satsuma": ["/cluster/satsuma_kissat_proofs_to_trim"],
    "sip": [],
    "clique": [],
}


def find_example_files(solver, inst):
    if not solver in INPUT_FILE_DIRS:
        return []
    result = subprocess.run(
        ["find", *INPUT_FILE_DIRS[solver], "-name", f"*{inst}*"],
        capture_output=True,
        text=True,
    )
    paths = result.stdout.splitlines()
    return paths


for solver in dfs.keys():
    df = dfs[solver]
    for tool, label in zip(TOOLS, TOOL_LABELS):
        failures = df[
            (df[f"{tool}_succeeded"] == 1) & (df[f"{tool}_time_exit_code"] != 124)
        ]

        msgs_raw = []
        msgs_normalised = []
        print(f"{label} - {solver}: ({len(failures)} non timeout failures)")
        print(f"------------")

        example_instance = {}
        for instance, lines in failures[f"{tool}_output_lines"].items():
            msg = "".join(l for l in lines if not RE_IGNORE.search(l))
            msg = msg.replace("\n", "\\n")
            raw = msg

            msg = re.sub(RE_PBP, "<FILE>.pbp", msg)
            msg = re.sub(RE_PB_SUM, "<PB CONSTRAINT>", msg)
            msg = re.sub(RE_LIST_NUMS, "<LIST OF NUMS>", msg)
            msg = re.sub(RE_POL_STATEMENT, "<POL STATEMENT>", msg)
            if not ".rs" in msg:
                msg = re.sub(RE_DIGITS, "<N>", msg)  # replace all numbers

            msgs_normalised.append(msg)
            if len(msg) >= 300:
                msg = msg[:300] + "<...truncated the rest>"
            if len(raw) >= 300:
                raw = raw[:300] + "<...truncated the rest>"

            example_instance[msg] = instance
            msgs_raw.append(raw)

        counts = Counter(msgs_normalised)
        for pattern, count in counts.most_common():
            # if count == 1:
            if count == 1:
                # find the original message that produced this pattern
                idx = msgs_normalised.index(pattern)
                print(f'   1x  "{msgs_raw[idx]}"')
            else:
                print(f'{count:4d}x  "{pattern}"')
            examples = find_example_files(solver, example_instance[pattern])
            print(f"Example: {" ".join(examples)}")
            print(f"------------")
        print()
