import re
import json
import shutil
from pathlib import Path
from subprocess import CalledProcessError
from amuse.detector.extractor import Extractor
from amuse.spoon_bridge.spoon_bridge import SpoonBridge
from amuse.utils.logger import Logger


class FactGenerator:
    """
    1. Generate the json call graph
    2. Extract the facts from the call graph
    3. Perform more complicated facts generation with native spoon
    """

    def __init__(self, target_file, line_no, callgraph_output_path, facts_output_path):
        self.target_file = target_file
        self.callgraph_output_path = callgraph_output_path
        self.facts_output_path = facts_output_path
        self.line_no = line_no
        self.method_signature = ""

    def generate_call_graph(self):
        args = [self.target_file] + [str(self.line_no)] + [self.callgraph_output_path]

        try:
            Logger.info("Generating Call Graph")
            print(args)
            p = SpoonBridge.run_call_graph_generator(args)
            p.check_returncode()
            Logger.debug("Generated Call Graph \n" + p.stdout + "\n")
            self.method_signature = self._get_method_signature(p.stdout)
            return self.method_signature
        except CalledProcessError as e:
            print(e)
            Logger.critical("Failed Generating Call Graph EXITING....")
            exit(1)

    def run_factor(self, line_no, path):
        Logger.info("Using Factor to extract more facts")
        p = SpoonBridge.run_factor([str(self.target_file), str(line_no), path])
        Logger.debug(f"running Factor at {path}")
        Logger.debug(p.stdout)

    def get_facts(self, line_no, unfixed_file_path):
        temp = self.callgraph_output_path / re.sub(
            "/root/amuse/", "", str(self.target_file)
        )

        facts_path = Path(re.sub(r"\.java", ".json", str(temp)))
        Extractor.extract_callgraph_facts(facts_path)
        Logger.debug(f"Extracting facts from {facts_path}")

        factor_output_path = self.facts_output_path / re.sub(
            "/root/amuse/", "", str(self.target_file)
        )

        factor_output_path = Path(re.sub(r"\.java", "", str(factor_output_path)))
        factor_output_path = factor_output_path / self.method_signature
        self.run_factor(line_no, factor_output_path)
        Logger.info(f"Facts written to {factor_output_path}")

    def _get_method_signature(self, output):
        result = re.search("Target Method Name: #(.+)", output)
        if result.group(1):
            return result.group(1)

    def check_api_present(
        self, json_path, api_names
    ):  # naive check, if only one of the api is present we get its facts
        if api_names == []:
            return True

        f = open(str(json_path))
        data = str(json.load(f))
        potentials = re.findall(r'class: (\S+), method: (\S+)\(\) "', data)

        for potential in potentials:
            method_name = potential[1]
            class_name = potential[0]

            full_name = class_name + "." + method_name

            possible_method_names = [method_name, class_name, full_name]

            intersection = list(set(api_names).intersection(possible_method_names))

            if len(intersection) > 0:
                return True

        return False

    def cleanup():
        dirpath = Path("/root/amuse/detector/facts/misuse")
        if dirpath.exists() and dirpath.is_dir():
            shutil.rmtree(dirpath)  # cleanup the files for the facts

        dirpath = Path("/root/amuse/detector/json/misuse")
        if dirpath.exists() and dirpath.is_dir():
            shutil.rmtree(dirpath)  # cleanup the files created by the java callgraph
