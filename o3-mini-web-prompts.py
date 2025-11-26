import json
import csv
from typing import List, Dict
import os
from pathlib import Path


def load_and_merge_data(json_path: str, csv_path: str) -> List[Dict]:
    # Read JSON file
    with open(json_path, "r") as f:
        json_data = json.load(f)

    # Read CSV file
    csv_items = []
    with open(csv_path, "r") as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            if row["MUBench Project"] and row["Misuse name"]:  # Skip empty rows
                csv_items.append(row)

    # Create merged data structure
    merged_data = []

    # For each CSV row, try to find matching JSON entry
    for csv_item in csv_items:
        project_name = csv_item[
            "MUBench Project"
        ].lower()  # Convert to lowercase for matching
        bug_id = csv_item["Misuse name"]

        # Find matching JSON entry
        matching_json_entry = None
        for api_pattern, entries in json_data.items():
            for entry in entries:
                entry_id_parts = entry["id"].split(".")
                if len(entry_id_parts) >= 2:
                    entry_project = entry_id_parts[0].lower()
                    entry_bug_id = entry_id_parts[-1]

                    if entry_project == project_name and entry_bug_id == bug_id:
                        matching_json_entry = entry.copy()
                        matching_json_entry["api_pattern"] = api_pattern
                        break
            if matching_json_entry:
                break

        if matching_json_entry:
            # Create merged entry with both CSV and JSON data
            merged_entry = {"csv_data": csv_item, "json_data": matching_json_entry}
            merged_data.append(merged_entry)

    return merged_data


def create_prompt(merged_entry: Dict, output_dir: str) -> None:
    """Create and save a prompt file for a given merged entry."""

    # Extract necessary information
    project_name = merged_entry["csv_data"]["MUBench Project"]
    bug_id = merged_entry["csv_data"]["Misuse name"]
    file_path = merged_entry["json_data"]["file_path"]

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Construct output file name
    output_file = f"{project_name}_{bug_id}.txt"
    output_path = os.path.join(output_dir, output_file)

    try:
        # Read the source code from the file path in json_data
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Construct the prompt
        prompt = (
            "Check if the following code does not have API misuse. "
            "If it does not, return 'correct'. "
            "If it does, return 'incorrect' and give a corrected version of the code:\n\n"
            f"{source_code}"
        )

        # Save the prompt
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt)

    except FileNotFoundError:
        print(f"Warning: Could not find source file: {file_path}")
    except Exception as e:
        print(f"Error processing {project_name}_{bug_id}: {str(e)}")


def generate_prompts(merged_data: List[Dict], output_dir: str) -> None:
    """Generate prompts for all merged entries."""
    for entry in merged_data:
        create_prompt(entry, output_dir)


# Example usage:
def main():
    json_path = "mubench.json"
    csv_path = "mubench-final.csv"
    output_dir = "prompts"

    merged_data = load_and_merge_data(json_path, csv_path)
    generate_prompts(merged_data, output_dir)

    print(f"Generated {len(merged_data)} prompts in {output_dir}/")


if __name__ == "__main__":
    main()
