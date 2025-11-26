from pathlib import Path
import shutil
from subprocess import run
from amuse.config import config
import os
import re
import glob

# @mechtaev
# Your synthesiser

# the content that will be passed is the method string


class SpecificationMiner:
    def __init__(self, project_path, root_path=None, f_name="fix.dl"):
        if root_path is None:
            root_path = config.crafted_datalog
        # project_path is the path right up to the project name without the method folder
        self.project_path = config.facts_root / re.sub("\.java", "", project_path)
        self.root_path = root_path
        self.f_name = f_name

    def synthesise(self, method_content=""):  # returns the path to the synthesised file
        root = self.root_path
        root.mkdir(exist_ok=True)

        return self.root_path / self.f_name

    def _get_facts_folder(self):
        # glob and take the first folder that contains the facts
        folders = [
            x
            for x in glob.glob(os.path.join(self.project_path, "*", ""), recursive=True)
        ]
        return folders[0]

    def apply(self, f_path=""):
        # get the single folder that contain all the .facts
        facts_path = self._get_facts_folder()

        output = Path("output")

        if not output.exists():
            os.makedirs(output)

        # print(facts_path)

        command = "souffle -F {} -D {} {}".format(
            facts_path, "./output", self.root_path / self.f_name
        )
        run(command.split(" "))

    def cleanup():
        shutil.rmtree("synthesised")
        shutil.rmtree("output")
