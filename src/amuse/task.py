import os
import shutil
import json
import re


from enum import Enum, auto
from pathlib import Path
from amuse.graph_manager import GraphManager
from amuse.project import MisuseProject
from amuse.specification_miner import SpecificationMiner
from amuse.patcher import Patcher
from amuse.detector import FactGenerator
from amuse.config import config

from amuse.utils.logger import Logger
from amuse.synthesiser import try_synthesise
from amuse.utils.timeable import Timeable


class TaskType:
    DETECTION = auto()
    SYNTHESISE = auto()
    PLAYGROUND = auto()
    ALL = auto()  # run through the whole process
    TARGET = auto()


class Task(Timeable):
    patched_output = os.getenv("patched_output")

    def __init__(self, path_or_misuse_file, task_type=TaskType.ALL, APIs=[]):
        super().__init__(str(task_type))
        self.rm_graph_dir()
        self.task_type = task_type
        self.report_root = Path("report")
        self.synthesise = try_synthesise
        self.info = path_or_misuse_file
        self.curr_misuse_method = None

        if (type(self.info)) == list:
            self.misuse_projects = self._process_misuse_projects(self.info)
        else:
            self.misuse_projects = [
                MisuseProject(self.info, config.input_root / config.misuse_root)
            ]

        self.names = [self._get_name(project) for project in self.misuse_projects]

        self.interested_apis = APIs

        self._setup()

    def _process_misuse_projects(self, projects):
        return [
            MisuseProject(project, config.input_root / config.misuse_root)
            for project in projects
        ]

    def _get_name(self, project):
        return re.sub(r"\.java", "", project.unfixed_file_path.rsplit("/")[-1])

    def _write_elapsed_time(self):
        for record in Timeable.records:
            print(record)

    def run(self):
        self.start_timer()
        # self.specification_miner = SpecificationMiner(
        #     self.misuse_project.unfixed_file_path
        # )

        if self.task_type == TaskType.DETECTION:
            self._run_detections(self.misuse_projects)
        elif self.task_type == TaskType.SYNTHESISE:
            facts_path = self._run_detections(self.misuse_projects)
            self._run_synthesiser(
                facts_path, "-".join(self.names), self.interested_apis
            )
        elif self.task_type == TaskType.ALL:
            self._run_full()

        self.stop_timer()
        self._write_elapsed_time()

        # for now don't clean up to see all the output
        # self.cleanup()

    def _run_detections(self, projects):
        facts_path = []
        for project in projects:
            self.graph_manager = GraphManager(
                config.output_root / config.output_graph / self._get_name(project)
            )
            facts_path += [self._run_detection(project)]
        return facts_path

    def _run_detection(self, project):
        Logger.info("generating the facts")
        method_signature = self.generate_facts(project)
        # we output the generated facts into the env output folder
        return self._setup_facts_path(method_signature, project)

    def _run_synthesiser(self, facts_paths, output_name, apis):
        Logger.info("Synthesising from the facts at")
        # FIXME: debug
        # for path in facts_paths:
        #     Logger.info(f"folder {path}")
        count = 0

        current_path = config.output_root / config.synthesise_root / output_name

        if not current_path.exists():
            os.makedirs(current_path)

        for output in self.synthesise(facts_paths, apis):
            count += 1
            with open(current_path / ("synthesised_" + str(count) + ".dl"), "w") as f:
                f.write(output)

    def _setup_facts_path(self, method_name, project):
        path_name = project.unfixed_file_path.replace("/root/amuse/", "")
        path_name = re.sub(r"\.java", "/", path_name)
        facts_path = config.output_root / config.facts_root / path_name / method_name

        self.facts_path = facts_path
        return facts_path

    def _patched_output_path(self, project):
        return config.output_root / config.patched_path / self._get_name(project)

    def _call_graph_output_path(self):
        return config.output_root / config.json_facts_root

    def _facts_output_path(self):
        return config.output_root / config.facts_root

    def _run_full(self):  # full run process
        for project in self.misuse_projects:
            self.graph_manager = GraphManager(
                config.output_root / config.output_graph / self._get_name(project)
            )
            self._run_detection(project)

            # self.perform_detection(self.misuse_project.fixed_file_path)
            # REMARK: mock synthesise of datalog
            # datalog_path = self.synthesise_datalog()

            # apply the datalog to the misuse file
            # get the errors and patch the old misuse code
            # transplant it into the fixed code base
            # and run test

            # self.specification_miner.apply()

            patcher = Patcher(
                config.input_root / f"{config.crafted_datalog}/fix.dl",
                project.unfixed_file_path,
                project.unfixed_method_line,
                self._patched_output_path(project),
            )

            Logger.info("running patcher")
            fix_patches_path = patcher.patch(self.facts_path, self._get_name(project))
            print("fixes")
            print(fix_patches_path)
            # print("no generated patches....")

    def _setup(self):
        d = Path(config.facts_root)
        d.mkdir(parents=True, exist_ok=True)

    def synthesise_datalog(self):
        return self.specification_miner.synthesise()

    def generate_facts(self, project, api_names=[]):
        fact_generator = FactGenerator(
            Path(os.getcwd(), project.unfixed_file_path),
            project.unfixed_method_line,
            self._call_graph_output_path(),
            self._facts_output_path(),
        )
        method_signature = fact_generator.generate_call_graph()

        fact_generator.get_facts(
            project.unfixed_method_line,
            project.unfixed_file_path,
        )

        self.create_latest_graph(project.unfixed_file_path)
        return method_signature

    def extract_API_elements(self, api_class, api_method, facts_path):
        # get the API invocations issued by the same API class

        pass

    def rm_graph_dir(self):
        out_path = Path("graph")
        if out_path.exists():
            for filename in os.listdir(out_path):
                file_path = os.path.join(out_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print("Unable to delete the file %s. Due to: %s" % (file_path, e))
        out_path.mkdir(parents=True, exist_ok=True)

    def create_latest_graph(self, f_path):
        path_name = f_path.replace("/root/amuse/", "")
        temp = config.output_root / config.json_facts_root / path_name
        json_path = re.sub(r"\.java", ".json", str(temp))

        data = json.load(open(json_path))
        Logger.info("Creating CFG Graph")

        for element in data:
            self.curr_misuse_method = element["methodSignature"]
            self.graph_manager.create_graph(element)

    # def _detailed_name(self):
    #     return (
    #         "line:"
    #         + str(self.misuse_project.correct_method_line)
    #         + "method_name:"
    #         + self.misuse_project.method_name
    #     )

    def _move_graph(self, report_path):
        shutil.move(
            "graph/" + self.curr_misuse_method + ".pdf", report_path / "graph.pdf"
        )

    def cleanup(self):
        self.misuse_project.cleanup()
        self.rm_graph_dir()

        # fix these later, cleaner to be instance
        FactGenerator.cleanup()
        SpecificationMiner.cleanup()
