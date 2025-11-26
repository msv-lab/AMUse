import os
import logging
from pathlib import Path


class Config:
    @property
    def patched_path(self):
        return Path(os.getenv("patched_output"))

    @property
    def info_root(self):
        return Path(os.getenv("info_root"))

    @property
    def facts_root(self):
        return Path(os.getenv("facts_root"))

    @property
    def json_facts_root(self):
        return Path(os.getenv("json_facts_root"))

    @property
    def output_root(self):
        return Path(os.getenv("root_output"))

    @property
    def output_graph(self):
        return Path(os.getenv("graph_output"))

    @property
    def input_root(self):
        return Path(os.getenv("root_input"))

    @property
    def misuse_root(self):
        return Path(os.getenv("misuse_root"))

    @property
    def synthesise_root(self):
        return Path(os.getenv("synthesised_root"))

    @property
    def crafted_datalog(self):
        return Path(os.getenv("crafted_datalog"))

    @property
    def logger_level(self):
        return logging.INFO if os.getenv("logger") == "default" else logging.DEBUG


config = Config()
