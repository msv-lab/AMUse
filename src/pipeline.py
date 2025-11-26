import os
import subprocess
import json
import shutil
from amuse.spoon_bridge.spoon_bridge import SpoonBridge


BUGGY_TAG = "buggy"
FIXED_TAG = "fixed"
FACT_TAG = "facts"
ROOT = "/root/amuse"
EVAL_ROOT = os.path.join(ROOT, "evaluations")


def run_command(command):
    """Executes a shell command and returns the output."""
    try:
        output = subprocess.check_output(command, shell=True).decode("utf-8").strip()
        print(output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Command '{command}' failed with error: {e}")


def clone_and_checkout(repo_url, commit_hash, destination):
    """Clones a git repository to the specified destination and checks out a specific commit."""

    run_command(f"git clone {repo_url} {destination}")
    os.chdir(destination)
    run_command(f"git checkout {commit_hash}")


def parse_datalog_facts(arguments):
    """Parses datalog facts for the current repo using the provided java command."""
    ret = SpoonBridge.run_factor(arguments.split(" "))
    print(ret.stdout)
    print(ret.stderr)


def run_souffle_on_facts(datalog_file, facts_path):
    """Runs Souffle on the given datalog facts."""
    run_command(f"souffle {datalog_file} -F {facts_path} -w")


def setup_path_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def project_path(id, is_fixed):
    tag = FIXED_TAG if is_fixed else BUGGY_TAG
    path = os.path.join(EVAL_ROOT, id, tag)
    setup_path_if_not_exists(path)
    return path


def file_path(id, is_fixed, relative_file_path):
    path = os.path.join(project_path(id, is_fixed), relative_file_path)
    setup_path_if_not_exists(path)
    return path


def fact_path(id, is_fixed):
    # make directory for facts
    setup_path_if_not_exists(os.path.join(project_path(id, is_fixed), FACT_TAG))
    return os.path.join(project_path(id, is_fixed), FACT_TAG)


def souffle_path(id):
    return os.path.join(ROOT, "documentation", "crafted_dl", f"{id}.dl")


def factor_args(id, is_fixed, parsing_mode, relative_file_path, method_line):
    mode_arg = f"--mode={parsing_mode}"
    file_arg = file_path(id, is_fixed, relative_file_path)
    proj_arg = project_path(id, is_fixed)

    if parsing_mode == "INTRA_PROC":
        return " ".join(
            [mode_arg, proj_arg, file_arg, method_line, fact_path(id, is_fixed)]
        )
    elif parsing_mode == "INTER_PROC":
        return " ".join(
            [mode_arg, proj_arg, file_arg, method_line, fact_path(id, is_fixed)]
        )


def process_repo(id, repo_url, commit_hash, is_fixed, mode, file_path, method_line):
    clone_and_checkout(repo_url, commit_hash, project_path(id, is_fixed))
    args = factor_args(id, is_fixed, mode, file_path, method_line)
    parse_datalog_facts(args)
    run_souffle_on_facts(souffle_path(id), fact_path(id, is_fixed))


def main(json_file_path):
    # Load JSON configuration
    with open(json_file_path, "r") as file:
        config = json.load(file)

    # Setup evaluation directories
    setup_path_if_not_exists(EVAL_ROOT)

    mode = config.get("analyse_mode", "INTRA_PROC")

    # Process buggy repo
    process_repo(
        config["id"],
        config["repo"],
        config["buggy_version"],
        False,
        mode,
        config["file_path"],
        config["method_line"],
    )

    # Process fixed repo
    fixed_method_line = config.get("fixed_method_line", config["method_line"])
    process_repo(
        config["id"],
        config["repo"],
        config["revision"],
        True,
        mode,
        config["file_path"],
        fixed_method_line,
    )


if __name__ == "__main__":
    main("/root/amuse/input/info/closure-2.json")
