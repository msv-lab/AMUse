import os
from itertools import product


def open_usages(api):
    with open("evaluation/ANALYZER_EVAL.txt", "r") as f:
        info_lines = []
        for line in f:
            project_id, api_, method, location, detected_output = line.strip().split(
                "\t"
            )
            if api_ == api:
                info_lines.append("\t".join([project_id, api_, method, location]))
                os.system(f"code -g {location}")

    # print the info lines
    for line in info_lines:
        print(line)


def compare_with_ground_truth(api):
    eval_file = "evaluation/ANALYZER_EVAL.txt"
    ground_truth_file = "/root/amuse/full_eval.csv"

    eval_api_uses = []

    with open(eval_file, "r") as f:
        for line in f:
            project_id, api_, method_folder, location, detected_output = (
                line.strip().split("\t")
            )
            if api_ == api:
                eval_api_uses.append(
                    (project_id, api_, method_folder, location, detected_output)
                )

    ground_truth_api_uses = []
    with open(ground_truth_file, "r") as f:
        for line in f:
            if api in line:
                location, ground_truth = None, None
                for item in line.split("\t"):
                    if "java:" in item:
                        location = item
                    elif "positive" in item:
                        ground_truth = "positive"
                    elif "negative" in item:
                        ground_truth = "negative"
                if location and ground_truth:
                    ground_truth_api_uses.append((api, location, ground_truth))
                if location and not ground_truth:
                    print(f"Ground truth not found for {api} in {location}")
    # compare the two lists
    for eval_use, ground_truth_use in product(eval_api_uses, ground_truth_api_uses):
        if eval_use[1] == ground_truth_use[0] and eval_use[3] == ground_truth_use[1]:
            detected_output = eval_use[4]
            ground_truth = ground_truth_use[2]
            if detected_output == "incorrect" and "positive" not in ground_truth:
                print(f"False positive: {eval_use[0]} {eval_use[1]} {eval_use[3]}")
            elif detected_output == "correct" and "negative" not in ground_truth:
                print(f"False negative: {eval_use[0]} {eval_use[1]} {eval_use[3]}")
            elif detected_output == "none" and "negative" not in ground_truth:
                print(f"False negative: {eval_use[0]} {eval_use[1]} {eval_use[3]}")


if __name__ == "__main__":
    compare_with_ground_truth("java.sql.Statement.setFetchSize")
