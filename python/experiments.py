import collections
import datetime
import dispy
import pandas as pd
import os
import signal
import sys
import time
from dataclasses import dataclass

DEFAULT_RUN_CMD = "/users/grad/mmcilree/projects/ThesisExperiments/runner.fish"
DEFAULT_RUN_ARGS = ()
DEFAULT_SECRET = "dispy_secret_gumbo"
DEFAULT_NODES = (1, 2, 3, 4)
DEFAULT_HOST = "130.209.251.4"
DEFAULT_PORT = 11223
DEFAULT_MEM_MAX = 12
ERROR_LOG = "errors.log"
DEFAULT_RESULTS_FIELDS = (
    "n",
    "short reasons",
    "seed",
    "propagators",
    "recursions",
    "failures",
    "propagations",
    "max depth",
    "solutions",
    "solve time",
    "prove time",
    "proof size kb",
    "check time",
    "exit code",
    "total time",
)


@dataclass(frozen=True)
class ExperimentConfig:
    prog: str
    overwrite_results: bool
    results_file: str
    results_id_fields: tuple[str, ...]
    generate_args: callable
    stringify_args: callable
    timeout: int
    results_fields: tuple[str, ...] = DEFAULT_RESULTS_FIELDS
    runner: str = DEFAULT_RUN_CMD
    runner_args: list[str] = DEFAULT_RUN_ARGS
    mem_max: int = DEFAULT_MEM_MAX
    secret: str = DEFAULT_SECRET
    nodes: tuple[int, ...] = DEFAULT_NODES
    host: str = DEFAULT_HOST
    port: str = DEFAULT_PORT


def computation(
    cmd,
    prog,
    memory_max,
    timeout,
    runner_args: list[str],
    prog_args_dict: dict,
    prog_args: list[str],
    use_systemd=True,
):
    import subprocess

    run_prefix = (
        [
            "systemd-run",
            "--scope",
            "-p",
            f"MemoryMax={memory_max}G",
            "-p",
            "MemorySwapMax=0",
            "-p",
            f"RuntimeMaxSec={timeout}s",
            "--user",
            cmd,
            prog,
        ]
        if use_systemd
        else [cmd, prog]
    )
    run_command = run_prefix + runner_args + prog_args

    start_time = time.monotonic()
    result = subprocess.run(run_command, capture_output=True, text=True)
    elapsed = time.monotonic() - start_time

    return (prog_args_dict, result.returncode, result.stdout, result.stderr, elapsed)


def submit_jobs(
    cluster: dispy.JobCluster,
    config: ExperimentConfig,
) -> list[dispy.DispyJob]:
    jobs = []
    current_id = 0

    previous_results = set()
    if not config.overwrite_results and os.path.exists(config.results_file):
        df = pd.read_csv(config.results_file)
        previous_results = set(
            zip(*[df[id_field] for id_field in config.results_id_fields])
        )

    for args in config.generate_args():
        if tuple(args.values()) not in previous_results:
            job = cluster.submit(
                config.runner,
                config.prog,
                config.mem_max,
                config.timeout,
                list(config.runner_args),
                args,
                config.stringify_args(args),
            )
            job.id = current_id
            jobs.append(job)

        current_id += 1
    return jobs


def parse_results(
    return_code, total_time, args, raw_output: str, config: ExperimentConfig
) -> dict[str, str]:
    results_dict = dict(args)

    for line in raw_output.splitlines():
        try:
            key, val = line.split(": ")
            results_dict[key] = val.strip()
        except Exception as e:
            print(f"Warning: output line failed to parse, see {ERROR_LOG}")
            with open(ERROR_LOG, "a") as error_log:
                error_log.write(
                    f"=== results parse error at {datetime.datetime.now()} ==\n"
                )
                error_log.write(f"Non-zero exit status: {return_code}\n")
                error_log.write(f"{args=}\n")
                error_log.write("=== begin python exception ===\n")
                error_log.write(str(e))
                error_log.write("=== begin stout ===\n")
                error_log.write(raw_output)
                error_log.write("=== results parse error ===\n")
                error_log.write("\n")

    results_dict["total time"] = total_time
    results_dict["exit code"] = return_code

    for key in config.results_fields:
        if key not in results_dict:
            results_dict[key] = "NaN"

    return results_dict


def write_results(results: dict[str, str], config: ExperimentConfig) -> None:
    import csv, os

    file_exists = os.path.exists(config.results_file)

    with open(config.results_file, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists or os.stat(config.results_file).st_size == 0:
            writer.writerow(config.results_fields)
        writer.writerow([results[k] for k in config.results_fields])


def status_to_text(status: int) -> str:
    return {
        5: "Created",
        6: "Running",
        7: "ProvisionalResult",
        8: "Cancelled",
        9: "Terminated",
        10: "Abandoned",
        11: "Finished",
    }.get(status, f"Unknown ({status})")


def handle_finished_job(job, config, error_log_file):
    args, return_code, output, stderr, total_time = job()
    if return_code != 0:
        print(f"Warning: non-zero exit status, see {error_log_file}")
        with open(error_log_file, "a") as error_log:
            error_log.write(f"=== job error at {datetime.datetime.now()} ==\n")
            error_log.write(f"Non-zero exit status: {return_code}\n")
            error_log.write(f"{job.id=}\n")
            error_log.write(f"{args=}\n")
            error_log.write("=== begin stout ===\n")
            error_log.write(output)
            error_log.write("=== begin stderr ===\n")
            error_log.write(stderr)
            error_log.write("=== end job error ===\n")
            error_log.write("\n")

    # results = parse_results(return_code, total_time, args, output, config)
    # write_results(results, config)


def run_with_config(config: ExperimentConfig):
    if config.overwrite_results and os.path.exists(config.results_file):
        os.unlink(config.results_file)

    error_log_file = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M") + ERROR_LOG
    cluster = dispy.JobCluster(
        computation,
        nodes=[f"fataepyc-{i:02d}" for i in config.nodes],
        secret=config.secret,
        host=config.host,
        dispy_port=config.port,
    )

    jobs = submit_jobs(cluster, config)
    print(datetime.datetime.now(), f" Submitted {len(jobs)} jobs")

    def handle_sigint(signum, frame):
        print("\nCancelling all jobs.")
        for job in jobs:
            cluster.cancel(job)
        cluster.shutdown()
        print("Done.")
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    finished = False
    if not jobs:
        finished = True

    while not finished:
        if cluster.wait(timeout=10):
            finished = True

        num_jobs_with_status: dict[int, int] = collections.defaultdict(int)
        for job in jobs:
            num_jobs_with_status[job.status] += 1
            if job.status == dispy.DispyJob.Finished:
                handle_finished_job(job, config, error_log_file)

        print(datetime.datetime.now())
        for status, count in num_jobs_with_status.items():
            print(f"{status_to_text(status)}: {count=}")

        jobs = [job for job in jobs if job.status != dispy.DispyJob.Finished]

        for job in jobs:
            if job.status == dispy.DispyJob.Terminated:
                print(f"ERR: {job.exception}")

    print("All jobs complete.")
