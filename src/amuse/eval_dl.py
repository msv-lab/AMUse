import os
import subprocess
from amuse.utils.logger import Logger


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

        if not (
            not is_csv_empty(correct_usage_path) and is_csv_empty(incorrect_usage_path)
        ):
            Logger.error(f"Unsatisfied condition for project: {project_path}")
            return False
        else:
            return True
    except subprocess.CalledProcessError as e:
        Logger.error(f"Error evaluating Souffle for project {project_path}: {e}")


if __name__ == "__main__":
    souffle_file = "/root/amuse/cache/java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream/test.dl"
    facts_root_folder = "/root/amuse/cache/java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream"  # Replace with your total facts folder path
    # facts_root_folder = "/root/amuse/cache/java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream"
    evaluate_souffle_on_projects(souffle_file, facts_root_folder)
