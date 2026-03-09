from experiments import ExperimentConfig, run_with_config
from argparse import ArgumentParser


# generated with
# awk -F '/' '{ print $5 }' track_main_2025_and__result_unsat_or_result___unknown_.uri | xargs -I% find /cluster/sat25-instances/ -name "%*" > sat_or_unknown_instances.txt
def generate_args():
    with open("./2024_sat_or_unknown_instances.txt") as inst_file:
        for instance in inst_file.readlines():
            instance = instance.strip()
            if instance != "":
                print(instance)
                yield {"instance": instance}


def stringify_args(args: dict) -> list[str]:
    argv = [args["instance"]]
    return argv


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--overwrite", default=False)
    parser.add_argument("--timeout", default=1000)

    args = parser.parse_args()

    config = ExperimentConfig(
        prog="/users/grad/mmcilree/projects/TrimmerExperiments/solvers/satsuma-kissat-sc/run.sh",
        runner="/users/grad/mmcilree/projects/TrimmerExperiments/fish/run_single_satsuma_kissat.fish",
        nodes=(1, 2, 3, 4, 7, 8, 9, 10),
        host="130.209.251.1",  # fataepyc-head
        overwrite_results=args.overwrite,
        results_file="satsuma_results.csv",
        results_id_fields=("instance"),
        results_fields=["instance"],
        generate_args=generate_args,
        stringify_args=stringify_args,
        timeout=args.timeout,
    )
    run_with_config(config)
