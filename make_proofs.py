from experiments import ExperimentConfig, run_with_config
from argparse import ArgumentParser


# generate instances.txt with
# find /cluster/PB24 \( -path "*/DEC-LIN/*" -o -path "*/OPT-LIN/*" \) -type f > instances.txt
def generate_args():
    with open("./pb24.txt") as inst_file:
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
    parser.add_argument("--timeout", default=300)

    args = parser.parse_args()

    config = ExperimentConfig(
        prog="/cluster/arthur/roundingsat/roundingsat/build/roundingsat",
        runner="/cluster/arthur/roundingsat/run_single.fish",
        nodes=(1, 2),
        host="130.209.251.5",  # fataepyc-02
        overwrite_results=args.overwrite,
        results_file="roundingsat_reslts.csv",
        results_id_fields=("instance"),
        results_fields=["instance"],
        generate_args=generate_args,
        stringify_args=stringify_args,
        timeout=args.timeout,
    )
    run_with_config(config)
