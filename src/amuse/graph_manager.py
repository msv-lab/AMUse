import re
import os
from subprocess import run
from amuse.utils.logger import Logger


class GraphManager:
    def __init__(self, root_path="./"):
        self.out_path = root_path
        Logger.info("GraphManager created")

    def create_dot_file(self, data):
        os.makedirs(self.out_path, exist_ok=True)
        out_path = os.path.join(self.out_path, "graph.dot")
        f = open(out_path, "w")
        content = data["methodGraph"].split("\n")

        # Fix the quotation marks inside another quotation mark which is not allowed in graphviz
        for line in content:
            selected = re.search('label="(.+) "]', line)

            if selected and re.search('"', selected.group(1)):
                fixed = re.sub('"', '\\"', selected.group(1))
                line = re.sub('label="(.+)"]', 'label="' + fixed + ' "]', line)

            f.write(line + "\n")
        f.close()
        Logger.info(f"created the file {out_path}")

    def create_graph(self, data):
        self.create_dot_file(data)
        run(
            [
                "dot",
                "-Tpdf",
                os.path.join(self.out_path, "graph.dot"),
                "-o",
                os.path.join(self.out_path, data["methodSignature"] + ".pdf"),
            ]
        )
        Logger.info("Generated PDF")
