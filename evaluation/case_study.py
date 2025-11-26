import os
import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler("case_study.log"))


def is_csv_empty(file_path):
    """Check if a CSV file is empty."""
    return os.path.exists(file_path) and os.path.getsize(file_path) == 0


def run_souffle_on_target(souffle_file, project_path, out_path):
    try:
        subprocess.run(
            ["souffle", souffle_file, "-F", project_path, "-D", out_path, "-w", "-j64"],
            check=True,
        )
        correct_usage_path = os.path.join(out_path, "correct_usage.csv")
        incorrect_usage_path = os.path.join(out_path, "incorrect_usage.csv")

        if not is_csv_empty(incorrect_usage_path):
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        print(f"Error evaluating Souffle for project {project_path}: {e}")


def main():
    closure_facts_path = "/root/closure-facts"
    synthesis_resource2_path = "/root/amuse/synthesis_resource2.json"
    souffle_path = "/root/amuse/cache"
    case_study_res_path = "/root/amuse/evaluation/case_study/"

    # load synthesis resource2.json
    with open(synthesis_resource2_path, "r") as f:
        data = json.load(f)

    # read the case_study.log file
    with open("case_study.log", "r") as f:
        log = f.read()

    # enumerate all keys to find the souffle file
    for key in data:
        final_program_path = os.path.join(souffle_path, key, "final_sat_program.dl")

        if not os.path.exists(final_program_path):
            logger.info(f"Souffle file not found for {key}")
            continue

        case_study_res_path = os.path.join(case_study_res_path, key)
        os.makedirs(case_study_res_path, exist_ok=True)

        for folder in os.listdir(closure_facts_path):

            # check if the key, folder is already evaluated
            if f"Souffle evaluation for {key} on {folder} completed." in log:
                continue

            func_path = os.path.join(closure_facts_path, folder)

            # run souffle on the target project
            if run_souffle_on_target(
                final_program_path, func_path, case_study_res_path
            ):
                logger.info(f"Found incorrect usage in {key} for {folder}")

            logger.info(f"Souffle evaluation for {key} on {folder} completed.")

        logger.info(f"Case study evaluation for {key} completed.")


if __name__ == "__main__":
    main()
    print("Case study evaluation completed.")
