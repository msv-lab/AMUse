import json
from amuse.task import Task, TaskType
from amuse.config import config
from amuse.utils.logger import Logger
from copy import copy
from dotenv import load_dotenv


class TaskRunner:
    # this is a test
    def __init__(self, task_type=TaskType.ALL, use_cache=True):
        self._load_config()
        Logger.setLevel(config.logger_level)
        self.use_cache = use_cache
        self.queue = []
        self.run_type = task_type

    def run(self, file_or_files, task_type=None, APIs=[]):
        if len(file_or_files) == 1:
            self.queue += self.create_tasks(file_or_files[0], task_type, APIs)
        elif len(file_or_files) > 1:
            self.queue += self._process_batch_synthesis(file_or_files, task_type, APIs)
        self.start()

    def _process_batch_synthesis(self, files, task_type, APIs):
        output = []
        for file in files:
            output += self._process_json(file)

        return [Task(output, task_type, APIs)]

    def start(self):
        while len(self.queue) != 0:
            current_task = self.queue.pop(0)
            current_task.run()

    def _process_json(self, json_file):
        with open(json_file) as f:
            data = json.load(f)

            if "," in data.get("method_line"):
                method_line = list(map(str.strip, data.get("method_line").split(",")))
                method_line_before = list(
                    map(str.strip, data.get("method_line_before").split(","))
                )
                methods = list(map(str.strip, data.get("method").split(",")))
                output = []
                for index, item in enumerate(method_line):
                    d = copy(data)
                    d["method_line"] = item
                    d["method_line_before"] = method_line_before[index]
                    d["method"] = methods[index]
                    output.append(d)
                    # tasks.append(Task(d, run_type, APIs))

                return output
                # self.queue.append(Task(d, run_type, True, APIs))

            else:
                return [data]
                # tasks.append(Task(data, run_type, APIs))
                # self.queue.append(Task(data, run_type, False, APIs))

    def create_tasks(self, json_file, task_type=None, APIs=[]):
        run_type = self.run_type

        if task_type is not None:
            run_type = task_type
        else:
            run_type = self.run_type

        # batch synthesise

        return [Task(json, task_type, APIs) for json in self._process_json(json_file)]

    def _load_config(self):
        load_dotenv()
