import os
import subprocess
from gen_fact import generate_facts_from_json

MUBENCH_NOT_READY = 0
PASS = 1
FAIL = 2


def count_files_in_directory(directory):
    """Count the number of files in a directory."""
    return sum([len(files) for r, d, files in os.walk(directory)])


def is_csv_empty(file_path):
    """Check if a CSV file is empty."""
    return os.path.exists(file_path) and os.path.getsize(file_path) == 0


def evaluate_souffle_on_projects(souffle_file, facts_root_folder):
    """Evaluate a Souffle file on each project in the facts root folder."""
    for project_folder in os.listdir(facts_root_folder):
        project_path = os.path.join(facts_root_folder, project_folder)
        if os.path.isdir(project_path) and count_files_in_directory(project_path) > 10:
            evaluate_souffle_on_project(souffle_file, project_path)


def eval_program_on_facts(program_path, json_file_path, api_resource_sig):
    cache_dirs, bugs_cnt = generate_facts_from_json(json_file_path, api_resource_sig)
    if not cache_dirs:
        return MUBENCH_NOT_READY
    for cache_dir in cache_dirs:
        if not cache_dir or not os.path.exists(cache_dir):
            print(f"Cache directory {cache_dir} does not exist")
            continue
        fail_cnt = 0
        is_pass = evaluate_souffle_on_project(program_path, cache_dir)
        if not is_pass:
            print(f"The program {program_path} failed on {cache_dir}")
            fail_cnt += 1

    if fail_cnt > 0:
        return FAIL, bugs_cnt, fail_cnt

    return PASS, bugs_cnt


def eval(synthesis_cache_folder, json_file_path):
    csv_lines = []
    for api_resource_sig in os.listdir(synthesis_cache_folder):
        # get the final_sat_program.dl
        final_sat_program_path = os.path.join(
            synthesis_cache_folder, api_resource_sig, "final_sat_program.dl"
        )
        if not os.path.exists(final_sat_program_path):
            csv_lines.append(f"{api_resource_sig}, NO_ANALYSER\n")
            continue
        # evaluate the final_sat_program.dl on the facts
        eval_result = eval_program_on_facts(
            final_sat_program_path, json_file_path, api_resource_sig
        )

        if eval_result == MUBENCH_NOT_READY:
            csv_lines.append(f"{api_resource_sig}, MUBENCH_NOT_READY\n")
        elif isinstance(eval_result, tuple) and eval_result[0] == PASS:
            csv_lines.append(f"{api_resource_sig}, PASS, {eval_result[1]}\n")
        elif isinstance(eval_result, tuple) and eval_result[0] == FAIL:
            csv_lines.append(
                f"{api_resource_sig}, FAIL, {eval_result[1]}, {eval_result[2]}\n"
            )

    with open("eval_result.csv", "w") as f:
        f.writelines(csv_lines)


def evaluate_souffle_on_project(souffle_file, project_path):
    try:
        subprocess.run(
            [
                "souffle",
                souffle_file,
                "-F",
                project_path,
                "-D",
                project_path,
                "-w",
            ],
            check=True,
        )
        correct_usage_path = os.path.join(project_path, "correct_usage.csv")
        incorrect_usage_path = os.path.join(project_path, "incorrect_usage.csv")

        # if not (
        #     is_csv_empty(correct_usage_path) and not is_csv_empty(incorrect_usage_path)
        # ):
        #     print(f"Unsatisfied condition for project: {project_path}")
        #     return False
        if is_csv_empty(incorrect_usage_path):
            print(f"Unsatisfied condition for project: {project_path}")
            return False
        else:
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error evaluating Souffle for project {project_path}: {e}")


if __name__ == "__main__":
    eval_program_on_facts(
        "/root/amuse/cache/java.util.Map@get/final_sat_program.dl",
        "/root/amuse/evaluation/mubench.json",
        "java.util.Map@get",
    )

    # eval("/root/amuse/cache", "/root/amuse/evaluation/mubench.json")
