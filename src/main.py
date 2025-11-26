import os
import sys
import argparse
import re
import shutil
from amuse.task import TaskType
from amuse.task_runner import TaskRunner
from amuse.config import config
from amuse.utils.logger import Logger
from amuse.spoon_bridge.spoon_bridge import SpoonBridge
from pathlib import Path
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile, TemporaryDirectory


def get_json_file(project_id):
    root_path = config.input_root / config.info_root
    files = list(root_path.glob(f"{project_id}.json"))

    if len(files) != 1:
        return None

    return files[0]


def generate_facts_task(file_path, out_path):
    with open(out_path.name, "w") as f:
        output = SpoonBridge.generate_info_file([file_path]).stdout
        f.write(output)
        f.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse the inputs")

    # for targeting the whole misuse project
    parser.add_argument(
        "-target", action="store_true", help="provide project with misuse"
    )
    parser.add_argument("-classpath", type=str, help="classpath of the project")
    parser.add_argument("-project_root", type=str, help="root of the misuse project")

    # for testing with single file

    parser.add_argument("-project", type=str, help="project name")

    parser.add_argument(
        "-crafted", action="store_true", help="use the manually crafted datalog"
    )

    parser.add_argument(
        "-facts",
        type=str,
        help="mode to generate the facts and see its output of a test file",
    )

    parser.add_argument(
        "-o", "--output", type=str, help="path to the facts output that you want"
    )

    parser.add_argument("-synthesise", type=str, help="synthesise from facts")

    parser.add_argument("-apis", nargs="*", help="the api you would like to search for")

    parser.add_argument("-clean", action="store_true", help="clean up the output files")
    parsed = parser.parse_args(sys.argv[1:])

    if parsed.project:
        Logger.info(f"running to fix single file for project {parsed.project}")

        task_runner = TaskRunner()
        file = get_json_file(parsed.project)
        if file:
            Logger.info("found info file and running task")
            task_runner.run([file], TaskType.ALL)
    elif parsed.facts:
        load_dotenv()
        selected_files = [config.input_root / parsed.facts]
        splitted_path = parsed.facts.rsplit("/", 1)
        # os.environ["misuse_root"] = splitted_path[0]

        if len(splitted_path) and not re.search(r"\.java", splitted_path[-1]):
            # provided a path
            file_path = Path(parsed.facts)
            selected_files = list(file_path.glob("**/*.java"))
            os.environ["misuse_root"] = parsed.facts

        if parsed.output:
            os.environ["facts_root"] = parsed.output

        task_runner = TaskRunner(TaskType.DETECTION)
        for selected_file in selected_files:
            with NamedTemporaryFile() as tmp:
                generate_facts_task(str(selected_file), tmp)
                tmp.flush()

                task_runner.run([tmp.name], TaskType.DETECTION, parsed.apis)

    elif parsed.synthesise:
        load_dotenv()
        selected_files = [parsed.synthesise]
        splitted_path = parsed.synthesise.rsplit("/", 1)

        os.environ["misuse_root"] = splitted_path[0]

        if len(splitted_path) and not re.search(r"\.java", splitted_path[-1]):
            # provided a path
            file_path = Path(config.input_root / parsed.synthesise)
            selected_files = [
                "/".join(str(x).split("/")[1:]) for x in list(file_path.glob("*.java"))
            ]
            os.environ["misuse_root"] = parsed.synthesise

        task_runner = TaskRunner(TaskType.SYNTHESISE)

        if len(selected_files) == 1:
            selected_file = selected_files[0]
            with NamedTemporaryFile() as tmp:
                generate_facts_task(config.input_root / selected_file, tmp)
                tmp.flush()
                task_runner.run([tmp.name], TaskType.SYNTHESISE, parsed.apis)
        elif len(selected_files) > 1:
            with TemporaryDirectory() as tmp_directory:
                files = [NamedTemporaryFile() for _ in selected_files]

                for selected_file, tmp in zip(selected_files, files):
                    generate_facts_task(config.input_root / selected_file, tmp)
                    tmp.flush()

                task_runner.run(
                    [file.name for file in files], TaskType.SYNTHESISE, parsed.apis
                )

    elif parsed.clean:
        load_dotenv()
        for filename in os.listdir(config.output_root):
            file_path = os.path.join(config.output_root, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception:
                print("Unable to delete the file / folder")

    elif parsed.target:
        # pass in java project
        # pass the class path
        # FOR NOW BROKEN, because of other changes
        pass
