from pprint import pprint, pformat
from pathlib import Path
import csv
from subprocess import CalledProcessError
from amuse.spoon_bridge import SpoonBridge
import itertools
import copy
import re
import os
import hashlib

from amuse.souffle import Souffle
from amuse.candidate import Candidate
from amuse.utils.logger import Logger
from amuse.utils.timeable import Timeable


class Patcher(Timeable):
    def __init__(self, synthesised_path, file_path, method_line, output_path):
        super().__init__()
        self.type_table = dict()
        self.instance_variables = dict()
        self.target_file = file_path
        self.synthesised_path = synthesised_path
        self.method_line = str(method_line)
        self.possible_patches = []
        self.datalog_methods = []
        self.datalog_exceptions = []
        self.datalog_throws = []
        self.datalog_return_values = []
        self.output_path = output_path
        self.misuse_context = dict()

    def _remove_duplicate_files(self, path):
        print("checking the path")
        print(path)
        # Listing out all the files
        # inside our root folder.
        list_of_files = os.walk(Path(path))

        # In order to detect the duplicate
        # files we are going to define an empty dictionary.
        unique_files = dict()

        for root, folders, files in list_of_files:
            # Running a for loop on all the files
            for file in files:
                # Finding complete file path
                file_path = Path(os.path.join(root, file))

                # Converting all the content of
                # our file into md5 hash.
                Hash_file = hashlib.md5(open(file_path, "rb").read()).hexdigest()

                # If file hash has already #
                # been added we'll simply delete that file
                if Hash_file not in unique_files:
                    unique_files[Hash_file] = file_path
                else:
                    os.remove(file_path)
                    print(f"{file_path} has been deleted")

    def _patch_code_block(self, name):
        target_path = Path(f"{os.getcwd()}/{self.target_file}")
        with open("patcher_log.txt", "w") as f:
            try:
                f.write(
                    SpoonBridge.run_patcher(
                        [
                            str(self.possible_patches),
                            target_path,
                            self.method_line,
                            self.output_path,
                        ]
                    ).stdout
                )
            except CalledProcessError:
                print("something went wrong with the patcher")

        self._remove_duplicate_files(self.output_path)

        return self.output_path

    def patch(self, relations, name):
        self.start_timer()
        self.setup(relations)

        self.repair(Souffle.load_relations(relations), self.synthesised_path)
        self.stop_timer()
        return self._patch_code_block(name)

    def _get_supplementary_info(self, directory):
        """returns mapping from relation name to a list of tuples"""
        relations = dict()
        for file in itertools.chain(
            Path(directory).glob("*.facts"), Path(directory).glob("*.csv")
        ):
            relation_name = file.stem
            with open(file) as csvfile:
                reader = csv.reader(csvfile, delimiter="\t")
                relations[relation_name] = list(reader)

        return relations

    def setup(self, relations):
        info = self._get_supplementary_info(relations)
        assign_types = info.get("assign_type", None)
        if assign_types is not None:
            for assign_type in assign_types:
                self.type_table[assign_type[1]] = assign_type[0]

        with open("instance_variables.txt") as f:
            lines = f.readlines()
            for line in lines:
                info = line.split("\t")
                self.instance_variables[info[1].strip()] = info[0].strip()

        with open("/amuse" / self.synthesised_path, "r") as textfile:
            methods = []
            exceptions = []
            throws = []
            returns = []

            for line in textfile:
                methods += re.findall(r"static_method\(\"(.+)\", [a-zA-Z]\)", line)
                methods += re.findall(
                    r"instance_call\([a-zA-Z],[ ]*\"(.+)\", [a-zA-Z]\).", line
                )
                exceptions += re.findall(r"exceptions_pos\(\"(.+)\", [a-zA-Z]\)", line)
                throws += re.findall(r"throw\(\"(.+)\", \"(.+)\", [a-zA-Z]\)", line)
                returns += re.findall(r"return_value\(\"(.+)\"", line)

            self.datalog_methods = methods
            self.datalog_exceptions = exceptions
            self.datalog_throws = throws
            self.datalog_return_values = returns

        loaded_relations = Souffle.load_relations(relations)

        self.misuse_context = {
            "variables": self.filter_duplicate(
                loaded_relations["variable"]
                # + [[x] for x in list(self.instance_variables.keys())]
            ),
            # "variables": [["ctx"]],
            # "methods": [["io.netty.channel.ChannelHandlerContext.close"]],
            # "methods": [["java.nio.ByteBuffer.flip"]],
            "methods": self.filter_duplicate(
                loaded_relations["method"] + [[x] for x in self.datalog_methods]
            ),
            "exceptions": self.filter_duplicate(
                loaded_relations["exceptions"] + [[x] for x in self.datalog_exceptions]
            ),
            "throws": self.filter_duplicate([[x] for x in self.datalog_throws]),
            "return_values": self.filter_duplicate(
                [[x] for x in self.datalog_return_values]
            ),
            "max_depth": int(
                max(
                    [
                        depth_statement[0]
                        for depth_statement in loaded_relations["depth_statement"]
                    ]
                )
            ),
        }

    def possible_arguments(self):
        output = []
        for variable in self.misuse_context["variables"]:
            output.append({"rule": "variable", "variable": variable[0]})
        return output

    def shift_facts(self, relations, property, indices, threshold, amount):
        # we need to shift the arguments, instance_call, call, false_flow, true_flow
        candidate = copy.deepcopy(relations)
        for selected_property in candidate[property]:
            index = None
            if len(indices) == 1:
                index = indices[0]
                if int(selected_property[index]) > threshold:
                    selected_property[index] = str(int(selected_property[index]) + 1)
        return candidate

    def attempt_add_invocation(
        self, statement, relations, patch_block, block_selection=""
    ):
        candidates = []
        for variable in self.misuse_context["variables"]:
            for method in self.misuse_context["methods"]:
                candidate = copy.deepcopy(relations)
                curr_patch_block = copy.deepcopy(patch_block)
                parent_patch_block = None
                if block_selection != "":
                    curr_patch_block = {}
                    parent_patch_block = copy.deepcopy(patch_block)

                # variable_type = self.type_table.get(variable[0], None)

                # if (
                #     variable_type is not None
                #     and self.similar(variable_type, method[0]) > 0.6
                # ):
                candidate["instance_call"].append([variable[0], method[0], statement])
                candidate["flow"].append([statement, str(int(statement) + 1)])
                # candidate = self.shift_facts(
                #     candidate, "instance_call", [2], int(statement), 1
                # )

                # candidate = self.shift_facts(
                #     candidate, "true_flow", [1], int(statement), 1
                # )

                # candidate = self.shift_facts( // does not work because it increments the thing to 10
                #     candidate, "false_flow", [1], int(statement), 1
                # )

                curr_patch_block["type"] = "INSERT"
                curr_patch_block["rule"] = "instance_call"

                for argument in self.possible_arguments() + [None]:
                    adjusted_patch = copy.deepcopy(curr_patch_block)
                    temp = {
                        "variable": variable[0],
                        "method": method[0],
                        "arguments": [] if argument is None else [argument],
                    }
                    adjusted_patch["content"] = temp
                    if block_selection != "":
                        curr_patch = copy.deepcopy(parent_patch_block)
                        curr_patch[block_selection].append(adjusted_patch)
                        adjusted_patch = curr_patch

                    candidates.append(
                        {
                            "content": candidate,
                            "patch": adjusted_patch,
                            # "patch": {
                            #     "type": "INSERT",
                            #     "depth": candidate["depth_statement"][-1][0],
                            #     "rule": "instance_call",
                            #     "start_pos": statement,
                            #     "content": {
                            #         "variable": variable[0],
                            #         "method": method[0],
                            #         "arguments": [],
                            #     },
                            # },
                        }
                    )
        return candidates

    def attempt_try_block(self, statement, max_statement, relations):
        candidates = []
        for x in range(1, max_statement):
            candidate = copy.deepcopy(relations)
            if statement + x <= max_statement:
                candidate["try"].append([statement, statement + x])
                for exception in self.misuse_context["exceptions"]:
                    candidate["exceptions_pos"].append([exception[0], statement + x])

                    candidates.append(
                        {
                            "content": candidate,
                            "patch": {
                                "type": "INSERT",
                                "rule": "try",
                                "depth": candidate["depth_statement"][-1][0],
                                "content": {
                                    "block_content": [],
                                    "catch_content": {
                                        "rule": "catch_content",
                                        "exception_type": exception[0],
                                        "content": [
                                            {
                                                "content": {
                                                    "rule": "throw",
                                                    "type": "INSERT",
                                                    "start_pos": "9",
                                                    "content": {
                                                        "rule": "initialisation",
                                                        "type": "INSERT",
                                                        "start_pos": "10",
                                                        "content": {
                                                            "arguments": "",
                                                            "class": "NullException",
                                                        },
                                                    },
                                                },
                                                "rule": "statement",
                                            }
                                        ],
                                    },
                                    "rule": "try_content",
                                },
                                "start_pos": statement,
                                "catch_pos": statement + x,
                            },
                        }
                    )

        return candidates

    def attempt_value(self, return_value):
        return {"rule": "variable", "variable": return_value}

    def attempt_return(
        self,
        previous_candidate,
        previous_content_block,
        statement,
        block_selection="contents",
    ):
        candidates = []

        if len(self.misuse_context["variables"]):
            for return_value in self.filter_duplicate(
                self.misuse_context["variables"] + self.misuse_context["return_values"]
            ):
                for x in range(statement + 1, statement + 2):
                    candidate = copy.deepcopy(previous_candidate)
                    candidate["return"].append([x])
                    candidate["return_value"].append([return_value[0], x])
                    patch = copy.deepcopy(previous_content_block)
                    patch[block_selection].append(
                        {
                            "type": "INSERT",
                            "rule": "return",
                            "content": {
                                "rule": "return_value",
                                "value": self.attempt_value(return_value[0]),
                            },
                        }
                    )
                    candidates.append({"content": candidate, "patch": patch})

        return candidates

    def attempt_assign(
        self,
        previous_candidate,
        previous_content_block,
        statement,
        values,
        block_selection="contents",
    ):
        candidates = []
        for variable in self.misuse_context["variables"]:
            for value in values:
                # assigning values only on the next statement
                for x in range(statement + 1, statement + 2):
                    candidate = copy.deepcopy(previous_candidate)
                    candidate["assign"].append([variable[0], x])
                    candidate["value"].append([value[0], x])
                    patch = copy.deepcopy(previous_content_block)
                    patch[block_selection].append(
                        {
                            "type": "INSERT",
                            "rule": "assign",
                            "variable": variable[0],
                            "content": value[0],
                        }
                    )
                    candidates.append({"content": candidate, "patch": patch})
        return candidates

    def possible_variable_conditions(self, variables, block):
        blocks = []
        for variable in variables:
            cloned_block = copy.deepcopy(block)
            cloned_block["condition"] = {"rule": "variable", "variable": variable[0]}
            blocks.append(cloned_block)

        return blocks

    def attempt_different_block_size(self, candidate, template_block, statement):
        output = []
        for i in range(1, 100):
            if statement + i < 5:
                candidate = copy.deepcopy(candidate)
                candidate["true_flow"].append([statement, statement + 1])
                candidate["false_flow"].append([statement, statement + i])
                new_template_block = copy.deepcopy(template_block)
                new_template_block["block_size"] = i
                output.append((candidate, new_template_block))
        return output

    def read_datalog_script(self, file):
        f = open(file)
        content = f.read()

        f.close()
        return content

    def filter_duplicate(self, inputs):
        new_output = []
        for curr in inputs:
            if curr not in new_output:
                new_output.append(curr)
        return new_output

    def repair(self, relations, datalog_script):
        possible_patches = []
        current_candidates = []

        candidate_object = Candidate(relations, {})
        Candidate.misuse_context = self.misuse_context
        Candidate.type_table = self.type_table
        # statically set the misuse_context

        statements = candidate_object.get_statements()

        for remove_statement in statements:
            removed_statement_candidate = candidate_object.remove_invocation(
                remove_statement[0]
            )

        for statement in statements:
            if statement == remove_statement:
                continue

            start_pos_candidate = removed_statement_candidate.set_start_pos(
                statement[0]
            )

            depth_candidates = start_pos_candidate.generate_possible_depth(statement[0])

            for depth_candidate in depth_candidates:
                for (
                    invocation_candidate
                ) in depth_candidate.generate_possible_invocation(statement[0]):
                    current_candidates.append(invocation_candidate)

                # for try_candidate in depth_candidate.generate_possible_tries(
                #     statement[0]
                # ):
                #     current_candidates.append(try_candidate)

                # current_candidates += self.attempt_try_block(
                #     int(statement[0]),
                #     int(max(statements)[0]),
                #     curr_candidate,
                # )
                # for (
                #     condition_candidate
                # ) in depth_candidate.generate_possible_conditions(statement[0]):
                #     print(condition_candidate)
                #     current_candidates.append(condition_candidate)

                # current_candidates += self.attempt_condition(
                #     statement[0], curr_candidate, curr_patch_block
                # )

                for candidate in current_candidates:
                    if (
                        len(
                            Souffle.test_relations(
                                candidate.get_facts(), datalog_script
                            )["incorrect_usage"]
                        )
                        == 0
                    ):
                        possible_patches.append(candidate.get_patch_block())

        self.possible_patches = possible_patches
        Logger.info(f"{len(possible_patches)} patch code snippets generated")
        Logger.debug("Generated Patch Snippets \n" + pformat(possible_patches))
