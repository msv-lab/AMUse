import copy
from difflib import SequenceMatcher
from pprint import pprint


class Candidate:
    misuse_context = None
    type_table = None

    def __init__(self, relations, initial_patch_block=None):
        self._datalog_facts = copy.deepcopy(relations)
        self._patch_block = {}
        if initial_patch_block is not None:
            self._patch_block = copy.deepcopy(initial_patch_block)

    def get_facts(self):
        return copy.deepcopy(self._datalog_facts)

    def get_patch_block(self):
        return copy.deepcopy(self._patch_block)

    def _remove_content(self, statement, property, candidate, index, expected_len):
        updated_content = [
            content
            for content in candidate[property]
            if len(content) == expected_len and int(content[index]) != statement
        ]
        candidate[property] = updated_content

    def similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def get_statements(self):
        return copy.deepcopy(self._datalog_facts["label"])

    def _remove_datalog_invocation(self, statement):
        candidate = copy.deepcopy(self._datalog_facts)
        self._remove_content(statement, "arguments", candidate, 1, 2)
        self._remove_content(statement, "assigned", candidate, 1, 2)
        self._remove_content(statement, "assign", candidate, 1, 2)
        self._remove_content(statement, "instance_call", candidate, 2, 3)
        self._remove_content(statement, "call", candidate, 1, 3)
        self._remove_content(statement, "null_check", candidate, 1, 2)
        self._remove_content(statement, "not_null_check", candidate, 1, 2)
        self._remove_content(statement, "value", candidate, 1, 2)
        self._remove_content(statement, "try", candidate, 0, 2)
        self._remove_content(statement, "true_flow", candidate, 0, 2)
        self._remove_content(statement, "false_flow", candidate, 0, 2)
        self._remove_content(statement, "throw", candidate, 0, 1)
        self._remove_content(statement, "static_method", candidate, 1, 2)
        self._remove_content(statement, "return_value", candidate, 1, 2)
        self._remove_content(statement, "return", candidate, 0, 1)
        self._remove_content(statement, "exceptions_pos", candidate, 1, 2)
        self._remove_content(statement, "defined", candidate, 1, 2)
        self._remove_content(statement, "condition_variable", candidate, 3, 4)
        self._remove_content(statement, "condition", candidate, 0, 1)
        return candidate

    def _get_max_depth(self):
        return int(
            max(
                [
                    depth_statement[0]
                    for depth_statement in self._datalog_facts["depth_statement"]
                ]
            )
        )

    def _possible_arguments(self):
        output = []
        for variable in Candidate.misuse_context["variables"]:
            output.append({"rule": "variable", "variable": variable[0]})
        return output

    def generate_possible_invocation(self, statement, block_selection=""):
        candidates = []
        for variable in Candidate.misuse_context["variables"]:
            for method in Candidate.misuse_context["methods"]:
                candidate = copy.deepcopy(self.get_facts())
                curr_patch_block = copy.deepcopy(self.get_patch_block())

                parent_patch_block = None
                if block_selection != "":
                    curr_patch_block = {}
                    parent_patch_block = copy.deepcopy(self._patch_block)

                # variable_type = Candidate.type_table.get(variable[0], None)

                # if (
                #     variable_type is not None
                #     and self.similar(variable_type, method[0]) > 0.6
                # ):

                candidate["instance_call"].append([variable[0], method[0], statement])
                candidate["flow"].append([statement, str(int(statement) + 1)])

                curr_patch_block["type"] = "INSERT"
                curr_patch_block["rule"] = "instance_call"

                for argument in self._possible_arguments() + [None]:
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
                    print(adjusted_patch)
                    candidates.append(Candidate(candidate, adjusted_patch))

        return candidates

    def generate_possible_depth(self, statement):
        candidate_objects = []
        for depth in range(0, self._get_max_depth() + 1):
            candidate = copy.deepcopy(self._datalog_facts)
            cloned_patch_block = copy.deepcopy(self._patch_block)
            cloned_patch_block["depth"] = depth
            candidate["depth_statement"].append([depth, statement])
            candidate_objects.append(Candidate(candidate, cloned_patch_block))

        return candidate_objects

    def _remove_statement(self, statement):
        return {
            "preprocess": {"remove": {"type": "statement", "pos": statement}},
        }

    def remove_invocation(self, statement):
        mutated_datalog_candidate = self._remove_datalog_invocation(statement)
        mutated_patch_block = self._remove_statement(statement)
        return Candidate(mutated_datalog_candidate, mutated_patch_block)

    def set_start_pos(self, statement):
        cloned_patch_block = copy.deepcopy(self._patch_block)
        cloned_patch_block["start_pos"] = statement

        return Candidate(self._datalog_facts, cloned_patch_block)

    def generate_possible_tries(self, statement):
        candidates = []
        max_statement = int(max(self.get_statements())[0])
        for x in range(1, max_statement):
            candidate = copy.deepcopy(self._datalog_facts)
            if int(statement) + x <= max_statement:
                candidate["try"].append([statement, str(int(statement) + x)])
                for exception in Candidate.misuse_context["exceptions"]:
                    candidate["exceptions_pos"].append(
                        [exception[0], str(int(statement) + x)]
                    )

                    patch = {
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
                        "catch_pos": str(int(statement) + x),
                    }

                    candidates.append(Candidate(candidate, patch))

        return candidates

    def generate_null_not_null(self, variable, statement, relations):
        candidates = []
        fact_types = []
        fact_names = ["null_check", "not_null_check"]

        for fact_name in fact_names:
            candidate = copy.deepcopy(relations)
            candidate[fact_name].append([variable, statement])
            candidates.append(candidate)
            fact_types.append(fact_name)
        return [fact_names, candidates]

    def attempt_null_check(self, statement, facts):
        output_candidates = []
        for variable in Candidate.misuse_context["variables"]:
            types, candidates = self.generate_null_not_null(
                variable[0], statement, facts
            )
            print("the length of null and not null")
            print(len(candidates))
            for candidate_type, candidate in zip(types, candidates):
                candidate["true_flow"].append([statement, str(int(statement) + 1)])
                candidate["flow"].append([statement, str(int(statement) + 1)])
                candidate["flow"].append([statement, str(int(statement) + 2)])
                candidate["false_flow"].append([statement, str(int(statement) + 2)])
                # candidate["false_flow"].append()
                # candidate["depth_statement"].append([depth, statement])
                curr_patch_block = self.get_patch_block()
                curr_patch_block["contents"] = []
                curr_patch_block["rule"] = candidate_type
                curr_patch_block["condition"] = {
                    "rule": "variable",
                    "variable": variable[0],
                }

                self._patch_block = curr_patch_block
                self._datalog_facts = candidate
                # patch_block = {
                #     "type": "INSERT",
                #     "rule": candidate_type,
                #     "contents": [],
                #     "condition": {"rule": "variable", "variable": variable[0]},
                #     "start_pos": statement,
                #     # "depth": depth,
                #     "depth": candidate["depth_statement"][-1][
                #         0
                #     ],  # take the last added item and take that depth
                # }

                # if len(self.misuse_context["return_values"]) + len(
                #     self.misuse_context["variables"]
                # ):
                #     output_candidates += self.attempt_return(
                #         candidate,
                #         curr_patch_block,
                #         statement,
                #         "contents",
                #     )

                output_candidates += self.generate_possible_invocation(
                    str(int(statement) + 1), "contents"
                )
                # output_candidates += self.attempt_add_invocation(
                #     str(int(statement) + 1), candidate, curr_patch_block, "contents"
                # )

                # output_candidates += self.attempt_assign(
                #     candidate,
                #     curr_patch_block,
                #     statement,
                #     [["123"], [""]],
                #     "contents",
                # )

        return output_candidates

    def generate_possible_conditions(self, statement):
        output_candidates = []
        facts = copy.deepcopy(self._datalog_facts)
        facts["condition"].append([statement])

        print("the length")
        print(len(self.attempt_null_check(statement, facts)))

        output_candidates += self.attempt_null_check(statement, facts)
        return output_candidates
