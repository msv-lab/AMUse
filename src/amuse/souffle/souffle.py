from pathlib import Path
import itertools
import csv
from subprocess import run, DEVNULL, CalledProcessError
from tempfile import TemporaryDirectory, NamedTemporaryFile

from .souffle_parser import pprint


class Souffle:
    @staticmethod
    def load_relations(directory, relation_names=None):
        """returns mapping from relation name to a list of tuples"""
        relations = dict()
        if relation_names is None:
            fact_files = itertools.chain(
                Path(directory).glob("*.facts"), Path(directory).glob("*.csv")
            )
            for file in fact_files:
                relation_name = file.stem
                with open(file) as csvfile:
                    reader = csv.reader(
                        csvfile, delimiter="\t", quotechar="\u2028", doublequote=False
                    )
                    relations[relation_name] = list(reader)
        else:
            for relation_name in relation_names:
                file = Path(directory) / (relation_name + ".facts")
                with open(file) as csvfile:
                    reader = csv.reader(csvfile, delimiter="\t")
                    relations[relation_name] = list(reader)
        return relations

    @staticmethod
    def write_relations(directory, relations):
        """write relations tuples as csv *.facts"""
        for relation_name, tuples in relations.items():
            file = Path(directory) / (relation_name + ".facts")
            with file.open(mode="w") as file:
                writer = csv.writer(file, delimiter="\t")
                for tuple in tuples:
                    writer.writerow(tuple)

    @staticmethod
    def pprint_fact_dict(fact_dict):
        """pretty print a fact dict"""
        result = ""
        for relation_name, tuples in fact_dict.items():
            for tuple in tuples:
                result += relation_name + "(" + ", ".join(tuple) + ")." + "\n"
        return result

    @staticmethod
    def test_relations(relations, datalog_script):
        """
        create temp fact files based on provided relations and run souffle against it
        """
        with TemporaryDirectory() as input_directory:
            Souffle.write_relations(input_directory, relations)
            with TemporaryDirectory() as output_directory:
                cmd = [
                    "souffle",
                    "-F",
                    input_directory,
                    "-D",
                    output_directory,
                    datalog_script,
                ]
                try:
                    run(cmd, check=True, stdout=DEVNULL)
                except CalledProcessError:
                    print("Error Calling Souffle")
                    exit(1)

                return Souffle.load_relations(output_directory)

    @staticmethod
    def run_program(program, relations):
        def run_cmd(cmd):
            try:
                run(cmd, check=True, stdout=DEVNULL)  # , stderr=DEVNULL)
            except CalledProcessError:
                print("----- error while solving: ----")
                print(pprint(program))
                print("---- on -----------------------")
                print(relations)
                exit(1)

        with NamedTemporaryFile() as datalog_script:
            datalog_script.write(pprint(program).encode())
            datalog_script.flush()
            with TemporaryDirectory() as input_directory:
                Souffle.write_relations(input_directory, relations)
                with TemporaryDirectory() as output_directory:
                    cmd = [
                        "souffle",
                        datalog_script.name,
                        "-F",
                        input_directory,
                        "-D",
                        output_directory,
                        "-w",
                        "--jobs=auto",
                    ]
                    run_cmd(cmd)

                    return Souffle.load_relations(output_directory)
