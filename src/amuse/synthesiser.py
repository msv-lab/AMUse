import copy
from amuse.detector.API_elements_extractor import (
    APIElementsExtractor,
    flow_id_index_map,
)
from amuse.spoon_bridge.spoon_bridge import SpoonBridge
from amuse.utils.logger import Logger
from amuse.souffle import (
    Souffle,
    parse,
    collect,
    pprint,
    Literal,
    Rule,
    Variable,
    String,
    Number,
    Program,
)
from amuse.semantic_mapper import SemanticMapper, Location
from amuse.eval_dl import evaluate_souffle_on_project

import json
from typing import Dict, List, Tuple
from copy import deepcopy
from tempfile import TemporaryDirectory, NamedTemporaryFile

# from mlxtend.frequent_patterns import apriori
# from mlxtend.preprocessing import TransactionEncoder
from itertools import product, combinations
import os
from collections import defaultdict, namedtuple
import shutil


COMPONENT_RULE_PREDS = [
    "must_call_followed_before_exit",
    "must_call_preceded_after_entry",
    "must_call_name_followed_before_exit",
    "var_dep",
    "condition_dominate",
    "in_try_catch",
]

LARGE_INT = 1000000000


class Fact(namedtuple("Fact", ["relation_name", "args"])):
    def __repr__(self) -> str:
        return f"{self.relation_name}({', '.join(self.args)})"

    def __str__(self) -> str:
        return f"{self.relation_name}({', '.join(self.args)})"

    def __hash__(self):
        return hash((self.relation_name, self.args))

    def __eq__(self, other):
        return self.relation_name == other.relation_name and self.args == other.args


# APIElement = namedtuple("APIElement", ["element", "semantics", "aux_info", "type"])
# APIElement.__new__.__defaults__ = (None,) * len(APIElement._fields)

APIElement = namedtuple("APIElement", ["literal"])  # let the literal be the APIElement

api_element_label_map = {
    Location("call", 0): 1,
    Location("must_call_followed_before_exit", 0): 1,
    Location("must_call_followed", 0): 1,
    Location("must_call_followed", 3): 4,
    Location("must_call_preceded_after_entry", 0): 1,
    Location("must_call_preceded", 0): 1,
    Location("must_call_preceded", 3): 4,
    Location("condition_dominate", 0): 1,
    Location("condition_dominate", 3): 4,
    Location("call_name", 0): 1,
    Location("must_call_name_followed_before_exit", 0): 1,
}

api_element_in_method_map = {
    Location("call", 0): 3,
    Location("must_call_followed_before_exit", 0): 2,
    Location("must_call_followed", 0): 2,
    Location("must_call_followed", 3): 5,
    Location("must_call_preceded_after_entry", 0): 2,
    Location("must_call_preceded", 0): 2,
    Location("must_call_preceded", 3): 5,
    Location("condition_dominate", 0): 2,
    Location("condition_dominate", 3): 5,
    Location("must_call_name_followed_before_exit", 0): 2,
}

VAR_PREFIX = "V_"


def all_length_combinations(lst):
    """
    This function takes a list and returns a list of all combinations
    of all possible lengths for the elements of the list.
    """
    return [comb for r in range(0, len(lst) + 1) for comb in combinations(lst, r)]


class Synthesizer:
    def __init__(self, api_resource_sig, api_signature, resource_config_path) -> None:
        self.api_resource_sig = api_resource_sig
        self.api_sig = api_signature
        self.resource_config_path = resource_config_path
        self._api_ele_id = 0
        self._api_ele_id_map = {}

    def synthesise(
        self, api_elements_list, component_rules_path, target_api_elements=None
    ):
        """Synthesise the Datalog rules for detecting API misuse."""
        samples_config = self.load_samples_config()
        facts_path_list = self.get_samples_facts(samples_config)

        # load component rules from the given path
        with open(component_rules_path, "r") as f:
            raw_rules = f.read()
            component_material = parse(raw_rules)

        tmp_component_literals = [
            x.head
            for x in collect(
                component_material,
                lambda x: isinstance(x, Rule) and x.head.name in COMPONENT_RULE_PREDS,
            )
        ]

        # only keep the component literal whose name is distinct
        seen_names = set()
        component_literals = [
            comp_literal
            for comp_literal in tmp_component_literals
            if comp_literal.name not in seen_names
            and not seen_names.add(comp_literal.name)
        ]

        all_synthesised_programs = []
        for idx, api_elements in enumerate(api_elements_list):
            target_api_literal, *other_api_ele_literals = api_elements
            target_api_literal = target_api_literal.literal
            other_api_ele_literals = [x.literal for x in other_api_ele_literals]

            if target_api_elements is not None:
                target_api_literal = target_api_elements[idx].literal
                other_api_ele_literals = [
                    x.literal for x in api_elements if x != target_api_elements[idx]
                ]

            # insert candidate rules in between of the api elements
            adj_pairs = [
                (api_elements[i], api_elements[i + 1])
                for i in range(len(api_elements) - 1)
            ]

            synthesised_programs = self.run_synthesis(
                adj_pairs,
                component_literals,
                target_api_literal,
                other_api_ele_literals,
            )
            all_synthesised_programs.extend(synthesised_programs)

        # evaluate the synthesied program on the collected facts and filter out the unsat programs
        sat_synthesied_programs = self.eval_filter(
            all_synthesised_programs, facts_path_list
        )

        if not sat_synthesied_programs:
            Logger.error("Failed to find a sat program.")
            return None

        # select the final sat program which has the most number of component literals in the correct_usage rule
        final_sat_program = self.select_final_sat_program(sat_synthesied_programs)
        # save the final sat program to the facts folder
        facts_root_folder = os.path.dirname(os.path.dirname(facts_path_list[0]))
        with open(facts_root_folder + "/final_sat_program.dl", "w") as f:
            f.write(pprint(final_sat_program))
        return final_sat_program

    def select_final_sat_program(self, sat_synthesied_programs):
        max_num_comp_literals = -1
        final_sat_program = None
        for sat_program in sat_synthesied_programs:
            correct_usage_rule = next(
                (
                    rule
                    for rule in sat_program.rules
                    if rule.head.name == "correct_usage"
                ),
                None,
            )
            if not correct_usage_rule:
                continue
            num_comp_literals = len(
                [
                    literal
                    for literal in correct_usage_rule.body
                    if literal.name in COMPONENT_RULE_PREDS
                ]
            )
            if num_comp_literals > max_num_comp_literals:
                max_num_comp_literals = num_comp_literals
                final_sat_program = sat_program
        return final_sat_program

    def get_samples_facts(self, samples_config):
        facts_path_list = []

        # get facts of each sample
        for config in samples_config:
            # get the facts from the sampled program
            facts_path = self._prepare_facts(
                config["file_path"], config["method_line_no"]
            )
            if not facts_path:
                continue
            Logger.info(f"facts_path: {facts_path}")
            facts_path_list.append(facts_path)

        return facts_path_list

    def eval_filter(self, synthe_programs, facts_path_list, sat_ratio=0.2):
        sat_programs = []
        covered_samples_map = defaultdict(set)

        for synthe_program in synthe_programs:
            with NamedTemporaryFile() as datalog_script:
                datalog_script.write(pprint(synthe_program).encode())
                datalog_script.flush()

                for facts_path in facts_path_list:
                    # evaluate the synthesised program on the collected facts
                    is_pass = evaluate_souffle_on_project(
                        datalog_script.name, facts_path
                    )
                    if is_pass:
                        covered_samples_map[str(synthe_program)].add(facts_path)
                    else:
                        Logger.info(f"Failed to pass {facts_path}")
                    # Logger.info(
                    #     f"Failed to pass {facts_path} with:\n {pprint(synthe_program)}"
                    # )

            pass_ratio = (
                len(covered_samples_map[str(synthe_program)]) / len(facts_path_list)
                if len(facts_path_list)
                else 0
            )

            if (
                pass_ratio >= sat_ratio
                and len(facts_path_list)
                and synthe_program not in sat_programs
            ):
                sat_programs.append(synthe_program)

        facts_root_folder = os.path.dirname(os.path.dirname(facts_path_list[0]))

        # store all synthesised programs to the facts folder
        for idx, synthe_program in enumerate(synthe_programs):
            with open(
                os.path.join(facts_root_folder, f"synthe_program_{idx}.dl"), "w"
            ) as f:
                f.write(pprint(synthe_program))

        # check if the sat programs cover all the samples
        covered_samples = {
            sample for samples in covered_samples_map.values() for sample in samples
        }

        if len(covered_samples) != len(facts_path_list):
            Logger.error(
                f"Failed to cover all the samples. Covered samples: {covered_samples}. Uncovered samples: {set(facts_path_list) - covered_samples}."
            )
            return []

        # store the sat programs to the facts folder
        for idx, sat_program in enumerate(sat_programs):
            with open(
                os.path.join(facts_root_folder, f"sat_program_{idx}.dl"), "w"
            ) as f:
                f.write(pprint(sat_program))

        return sat_programs

    def instantiate_comp_literal(
        self, comp_literal: Literal, api_pair: List[APIElement]
    ):
        """Instantiate the component literal with the api element"""

        api_literal1, api_literal2 = api_pair[0].literal, api_pair[1].literal

        comp_literal_semantics_map = {
            "must_call_followed_before_exit": [
                [("call_sig", 0), ("variable", 1), ("flow_id", 2), ("in_meth_sig", 3)],
                [("call_sig", 4), ("variable", 5)],
            ],
            "must_call_preceded_after_entry": [
                [("call_sig", 0), ("variable", 1), ("flow_id", 2), ("in_meth_sig", 3)],
                [("call_sig", 4), ("variable", 5)],
            ],
            "must_call_name_followed_before_exit": [
                [("call_name", 0), ("variable", 1), ("flow_id", 2), ("in_meth_sig", 3)],
                [("call_name", 4), ("variable", 5)],
            ],
            "var_dep": [
                [("variable", 0), ("flow_id", 1), ("in_meth_sig", 2)],
                [("variable", 3), ("flow_id", 4), ("in_meth_sig", 5)],
            ],
            "condition_dominate": [
                [("call_sig", 0)],
                [("variable", 1), ("flow_id", 2), ("in_meth_sig", 3)],
            ],
            "in_try_catch": [
                [("call_sig", 0), ("variable", 1), ("flow_id", 2), ("in_meth_sig", 3)],
                [("flow_id", 4), ("exception_type", 5)],
            ],
        }

        api_literal_semantics_map = {
            "call": ["call_sig", "flow_id", "variable", "in_meth_sig"],
            "call_name": ["call_name", "flow_id", "variable", "in_meth_sig"],
            "catch": [
                "exception_type",
                "variable",
                "flow_id",
                "flow_id",
                "flow_id",
                "in_meth_sig",
            ],
        }

        # divide the semantics into two parts: the semantics of the first api literal and the second api literal
        comp_semantics1, comp_semantics2 = comp_literal_semantics_map.get(
            comp_literal.name, []
        )

        api_semantics1, api_semantics2 = api_literal_semantics_map.get(
            api_literal1.name, []
        ), api_literal_semantics_map.get(api_literal2.name, [])

        comp_literal_args = list(comp_literal.args)

        # find the corresponding semantics in the api literals
        for idx, api_semantic1 in enumerate(api_semantics1):
            comp_semantic1_idx = next(
                (
                    comp_semantic[1]
                    for comp_semantic in comp_semantics1
                    if comp_semantic[0] == api_semantic1
                ),
                None,
            )
            if comp_semantic1_idx is None:
                continue
            # replace the argument with the corresponding argument in the api element
            comp_literal_args[comp_semantic1_idx] = api_literal1.args[idx]

        for idx, api_semantic2 in enumerate(api_semantics2):
            comp_semantic2_idx = next(
                (
                    comp_semantic[1]
                    for comp_semantic in comp_semantics2
                    if comp_semantic[0] == api_semantic2
                ),
                None,
            )
            if comp_semantic2_idx is None:
                continue
            # replace the argument with the corresponding argument in the api element
            comp_literal_args[comp_semantic2_idx] = api_literal2.args[idx]

        return Literal(
            comp_literal.name, tuple(comp_literal_args), comp_literal.positive
        )

    def run_synthesis(
        self,
        adj_api_ele_pairs,
        component_literals,
        target_api_literal,
        other_api_ele_literals,
    ):
        synthe_literal_map = defaultdict(lambda: defaultdict(list))

        def get_ele_position_args(element):
            literal = element.literal
            literal_pos_map = {"call": [1, 3], "call_name": [1, 3], "assigned": [1, 2]}
            pos = literal_pos_map.get(literal.name, [])
            args = [literal.args[idx] for idx in pos]
            return args

        for pair in adj_api_ele_pairs:
            # if the pair is on the same line, we do not need to synthesise the component literals
            ele1, ele2 = pair
            if get_ele_position_args(ele1) == get_ele_position_args(ele2):
                continue
            for comp_literal in component_literals:
                # instantiate the comp_literal according to the pair of api elements
                synth_comp_literal = self.instantiate_comp_literal(comp_literal, pair)
                synthe_literal_map[pair][comp_literal].append(synth_comp_literal)

        # construct component literal level rules
        pair_combs = defaultdict(list)
        comb_list = []
        for pair in adj_api_ele_pairs:
            combs = all_length_combinations(component_literals)
            pair_combs[pair].extend(combs)
            comb_list.append(combs)

        result = []

        for prod in product(*comb_list):
            # prod: ((literal1, literal2), (literal3, literal4), ...)
            # construct the rule by combining the literals

            # For each product, it contains all literals to form the program.
            # For each element in the product, it represents the list of literals
            # between a pair of adjacent api elements.

            synthe_literals_list = []

            for pair, comb in zip(adj_api_ele_pairs, prod):
                ele1, ele2 = pair
                if get_ele_position_args(ele1) == get_ele_position_args(ele2):
                    continue
                for comp_literal in comb:
                    synthe_literals_list.append(synthe_literal_map[pair][comp_literal])

            # For each element in the synthe_literals_list, it represents the
            # list of synthe_literals under the pair-literal.
            # So, we need to take the product of them.
            # construct the rule by combining the literals
            for synthe_literals in product(*synthe_literals_list):
                # extend the synthe_literals with the usage template
                program1 = self.add_template(
                    synthe_literals,
                    target_api_literal,
                    other_api_ele_literals,
                )
                if program1 not in result:
                    result.append(program1)
                # if program2 not in result:
                #     result.append(program2)

            # add the basic template if no component literal is used
            if all([len(x) == 0 for x in synthe_literals_list]):
                program1 = self.add_template(
                    [],
                    target_api_literal,
                    other_api_ele_literals,
                )
                if program1 not in result:
                    result.append(program1)
                # if program2 not in result:
                #     result.append(program2)

        return result

    def add_template(
        self,
        synth_literals,
        target_api_literal,
        other_api_ele_literals,
    ):
        """add the template to the synth_literals"""

        api_literal = target_api_literal

        rules = []
        synth_literals = list(synth_literals)
        usage_literals = synth_literals + other_api_ele_literals

        # to avoid unground errors, we need to create literals where constants are replaced with underscores
        aux_literals = []
        for other_api_ele_literal in other_api_ele_literals:
            args = []
            for arg in other_api_ele_literal.args:
                if isinstance(arg, String) or isinstance(arg, Number):
                    args.append(arg)
                else:
                    args.append(Variable("_"))

            aux_literals.append(
                Literal(
                    other_api_ele_literal.name,
                    tuple(args),
                    other_api_ele_literal.positive,
                )
            )

        # correct usage rule
        correct_usage_head = Literal("correct_usage", api_literal.args, True)
        correct_usage_body = [api_literal] + usage_literals
        correct_usage_rule = Rule(correct_usage_head, correct_usage_body)
        rules.append(correct_usage_rule)

        # incorrect usage rule
        incorrect_usage_head = Literal("incorrect_usage", api_literal.args, True)
        for literal in synth_literals:
            negated_literal = Literal(literal.name, literal.args, not literal.positive)
            incorrect_usage_body = (
                [api_literal] + [negated_literal] + other_api_ele_literals
            )
            incorrect_usage_rule = Rule(incorrect_usage_head, incorrect_usage_body)
            rules.append(incorrect_usage_rule)

        # the rules for the program where all api literals must appear
        all_api_rules = copy.deepcopy(rules)

        for literal in aux_literals:
            negated_literal = Literal(literal.name, literal.args, not literal.positive)
            incorrect_usage_body = [api_literal] + [negated_literal]
            incorrect_usage_rule = Rule(incorrect_usage_head, incorrect_usage_body)
            rules.append(incorrect_usage_rule)

        # construct the program
        declarations = {
            "correct_usage": ["symbol", "number", "symbol", "symbol"],
            "incorrect_usage": ["symbol", "number", "symbol", "symbol"],
        }

        program1 = Program(
            declarations,
            inputs=[],
            outputs=["correct_usage", "incorrect_usage"],
            include=["/root/amuse/documentation/crafted_dl/analyser_new.dl"],
            rules=all_api_rules,
        )

        program2 = Program(
            declarations,
            inputs=[],
            outputs=["correct_usage", "incorrect_usage"],
            include=["/root/amuse/documentation/crafted_dl/analyser_new.dl"],
            rules=rules,
        )

        # check if the 'condition_dominate' literal is used in the synth_literals
        if any([literal.name == "condition_dominate" for literal in synth_literals]):
            # this rule requires all the api literals to appear
            return program1

        return program2

    def load_samples_config(self):
        with open(self.resource_config_path, "r") as f:
            all_config = json.load(f)
            if self.api_resource_sig not in all_config:
                raise ValueError(
                    f"API signature {self.api_resource_sig} not found in"
                    f" {self.resource_config_path}"
                )
            return all_config[self.api_resource_sig]

    def _prepare_facts(self, file_path, api_line_no):
        # create the cache dir based on the last two components of the file path.
        cache_dir = os.path.join(
            "cache",
            file_path.split("/")[-2] + "/" + file_path.split("/")[-1].split(".")[0],
        )
        os.makedirs(cache_dir, exist_ok=True)
        args = [
            "--mode=INTRA_PROC",
            file_path,
            file_path,
            str(api_line_no),
            cache_dir,
        ]
        try:
            Logger.info(f"Generating sample facts of {file_path}\n")
            p = SpoonBridge.run_factor(args)
            p.check_returncode()
            Logger.info(f"Generated sample facts are written to {cache_dir}\n")
            Logger.debug(p.stdout)

        except Exception as e:
            Logger.error(f"Failed to generate sample facts of {cache_dir}\n")
            Logger.error(e)

            # remove the cache dir
            shutil.rmtree(cache_dir)

            return None

        # find the only folder in the cache_dir
        facts_dir = None
        for folder in os.listdir(cache_dir):
            if os.path.isdir(os.path.join(cache_dir, folder)):
                facts_dir = os.path.join(cache_dir, folder)
                break

        return facts_dir


if __name__ == "__main__":
    # # 1. synthesiser of the android.database.Cursor.close() API

    # syn = Synthesizer(
    #     "android.database@Cursor@close+android.database.sqlite@SQLiteDatabase@query",
    #     "android.database.Cursor.close()",
    #     "/root/amuse/synthesis_resource.json",
    # )

    # ele1 = APIElement(
    #     Literal(
    #         "call_name",
    #         tuple(
    #             [
    #                 String("android.database.sqlite.SQLiteDatabase.query"),
    #                 Variable("label_1"),
    #                 Variable("target_1"),
    #                 Variable("in_meth_1"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # ele2 = APIElement(
    #     Literal(
    #         "call_name",
    #         tuple(
    #             [
    #                 String("android.database.Cursor.close"),
    #                 Variable("label_2"),
    #                 Variable("target_2"),
    #                 Variable("in_meth_2"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # api_elements = [ele1, ele2]

    # result = syn.synthesise(
    #     [api_elements], "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    # )

    # # 2. synthesiser of the java.io.DataOutputStream.flush() API
    # syn = Synthesizer(
    #     "java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream",
    #     "java.io.ByteArrayOutputStream.toByteArray()",
    #     "/root/amuse/synthesis_resource.json",
    # )

    # ele1 = APIElement(
    #     Literal(
    #         "call",
    #         tuple(
    #             [
    #                 String("java.io.ByteArrayOutputStream.toByteArray()"),
    #                 Variable("label_1"),
    #                 Variable("target_1"),
    #                 Variable("in_meth_1"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # ele2 = APIElement(
    #     Literal(
    #         "call",
    #         tuple(
    #             [
    #                 String("java.io.DataOutputStream.flush()"),
    #                 Variable("label_2"),
    #                 Variable("target_2"),
    #                 Variable("in_meth_2"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # api_elements = [ele1, ele2]

    # api_elements_list = [[ele1, ele2]]

    # result = syn.synthesise(
    #     api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    # )

    # # 3. synthesiser of the java.sql.ResultSet.close() API
    # syn = Synthesizer(
    #     "java.sql@PreparedStatement@executeQuery+java.sql@ResultSet@close",
    #     "java.sql.ResultSet.close()",
    #     "/root/amuse/synthesis_resource.json",
    # )

    # ele1 = APIElement(
    #     Literal(
    #         "call",
    #         tuple(
    #             [
    #                 String("java.sql.PreparedStatement.executeQuery()"),
    #                 Variable("label_1"),
    #                 Variable("target_1"),
    #                 Variable("in_meth_1"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # ele2 = APIElement(
    #     Literal(
    #         "call",
    #         tuple(
    #             [
    #                 String("java.sql.ResultSet.close()"),
    #                 Variable("label_2"),
    #                 Variable("target_2"),
    #                 Variable("in_meth_2"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # api_elements = [ele1, ele2]

    # api_elements_list = [[ele1, ele2]]

    # result = syn.synthesise(
    #     api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    # )

    # # it is passed on the correct collected samples

    # # 4. synthesiser of the java.lang.String.getBytes API
    # syn = Synthesizer(
    #     "java.lang.String@getBytes",
    #     "java.lang.String.getBytes",
    #     "/root/amuse/synthesis_resource.json",
    # )

    # ele1 = APIElement(
    #     "java.lang.String.getBytes(java.lang.String)",
    #     "call_signature",
    # )

    # ele2 = APIElement(
    #     "UTF_8",
    #     "argument",
    # )

    # ele3 = APIElement(
    #     "Charsets.ISO_8859_1",
    #     "argument",
    # )

    # ele4 = APIElement(
    #     "US_ASCII",
    #     "argument",
    # )

    # ele5 = APIElement(
    #     "Charsets.UTF_8",
    #     "argument",
    # )

    # api_elements_list = [[ele1, ele2], [ele1, ele3], [ele1, ele4], [ele1, ele5]]

    # result = syn.synthesise(
    #     api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    # )

    # # 5. synthesiser of the java.net.URLDecoder.decode API
    # syn = Synthesizer(
    #     "java.net.URLDecoder@decode",
    #     "java.net.URLDecoder.decode",
    #     "/root/amuse/synthesis_resource.json",
    # )

    # ele1 = APIElement(
    #     "java.net.URLDecoder.decode(java.lang.String,java.lang.String)",
    #     "call_signature",
    # )

    # ele2 = APIElement(
    #     '"UTF-8"',
    #     "argument",
    # )

    # result = syn.synthesise(
    #     [[ele1, ele2]], "/root/amuse/documentation/crafted_dl/analyser.dl"
    # )

    # # 6. synthesiser of the com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype()
    # syn = Synthesizer(
    #     "com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype()",
    #     "com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype()",
    #     "/root/amuse/synthesis_resource.json",
    # )

    # ele1 = APIElement(
    #     Literal(
    #         "assigned",
    #         tuple([Variable("target_2"), Variable("label_1"), Variable("in_meth_1")]),
    #         True,
    #     ),
    # )

    # ele2 = APIElement(
    #     Literal(
    #         "call",
    #         tuple(
    #             [
    #                 String(
    #                     "com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype()"
    #                 ),
    #                 Variable("label_1"),
    #                 Variable("target_1"),
    #                 Variable("in_meth_1"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # ele3 = APIElement(
    #     Literal(
    #         "call",
    #         tuple(
    #             [
    #                 Variable("_"),
    #                 Variable("label_2"),
    #                 Variable("target_2"),
    #                 Variable("in_meth_2"),
    #             ]
    #         ),
    #         True,
    #     )
    # )

    # result = syn.synthesise(
    #     [[ele1, ele2, ele3]],
    #     "/root/amuse/documentation/crafted_dl/analyser_new.dl",
    #     [ele2],
    # )

    # 7. synthesiser of the java.util.Iterator.next() API
    syn = Synthesizer(
        "java.util@Iterator@hasNext+java.util@Iterator@next",
        "java.util.Iterator.next()",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.util.Iterator.hasNext()"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.util.Iterator.next()"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list,
        "/root/amuse/documentation/crafted_dl/analyser_new.dl",
        [ele2],
    )

    # 8. synthesiser of the return of java.util.Map.get()
    syn = Synthesizer(
        "java.util.Map@get",
        "java.util.Map.get",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "assigned",
            tuple([Variable("target_2"), Variable("label_1"), Variable("in_meth_1")]),
            True,
        ),
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Map.get"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele3 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    Variable("_"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2, ele3]]

    result = syn.synthesise(
        api_elements_list,
        "/root/amuse/documentation/crafted_dl/analyser_new.dl",
        [ele2],
    )

    # 9. synthesiser of the java.util.Enumeration.nextElement API
    syn = Synthesizer(
        "java.util.Enumeration@nextElement",
        "java.util.Enumeration.nextElement",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.util.Enumeration.hasMoreElements()"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.util.Enumeration.nextElement()"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list,
        "/root/amuse/documentation/crafted_dl/analyser_new.dl",
        [ele2],
    )

    # 10. synthesiser of the java.util.Scanner.next API
    syn = Synthesizer(
        "java.util.Scanner@next",
        "java.util.Scanner.next",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.util.Scanner.hasNext()"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.util.Scanner.next()"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list,
        "/root/amuse/documentation/crafted_dl/analyser_new.dl",
        [ele2],
    )

    # 11. synthesiser of the android.app@Dialog.dismiss API
    syn = Synthesizer(
        "android.app@Dialog@dismiss",
        "android.app.Dialog.dismiss",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("android.app.Dialog.isShowing()"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("android.app.Dialog.dismiss()"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list,
        "/root/amuse/documentation/crafted_dl/analyser_new.dl",
        [ele2],
    )

    # 12. synthesiser of the javax.swing.JFrame.setVisible API
    syn = Synthesizer(
        "javax.swing@JFrame@setVisible",
        "javax.swing.JFrame.setVisible",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.awt.Window.setVisible(boolean)"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.awt.Window.pack()"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 13. synthesiser of the java.sql.Connection.prepareStatement API
    syn = Synthesizer(
        "java.sql.Connection.prepareStatement+java.sql.PreparedStatement.close",
        "java.sql.Connection.prepareStatement",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.sql.Connection.prepareStatement"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.sql.Statement.close"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 14. synthesiser of the java.io.DataOutputStream.close API
    syn = Synthesizer(
        "java.io.DataOutputStream.close",
        "java.io.DataOutputStream.close",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String(
                        "java.io.DataOutputStream.java.io.DataOutputStream(java.io.OutputStream)"
                    ),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.io.FilterOutputStream.close()"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 15. synthesiser of the java.io.PrintWriter.close API
    syn = Synthesizer(
        "java.io.PrintWriter.close",
        "java.io.PrintWriter.close",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.io.PrintWriter._init_"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.io.PrintWriter.close"),
                    Variable("label_2"),
                    Variable("target_1"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 16. synthesiser of the java.nio.ByteBuffer.flip API
    syn = Synthesizer(
        "java.nio.ByteBuffer.flip",
        "java.nio.ByteBuffer.flip",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.nio.channels.FileChannel.write(java.nio.ByteBuffer)"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.nio.Buffer.flip()"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_2"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 17. synthesiser of the java.lang.Short.parseShort API
    syn = Synthesizer(
        "java.lang.Short.parseShort",
        "java.lang.Short.parseShort",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.lang.Short.parseShort(java.lang.String)"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "catch",
            tuple(
                [
                    String("NumberFormatException"),
                    Variable("_"),
                    Variable("catch_label"),
                    Variable("_"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 18. synthesiser of the java.lang.Long.parseLong API
    syn = Synthesizer(
        "java.lang.Long.parseLong",
        "java.lang.Long.parseLong",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.lang.Long.parseLong(java.lang.String)"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "catch",
            tuple(
                [
                    String("NumberFormatException"),
                    Variable("_"),
                    Variable("catch_label"),
                    Variable("_"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 19. synthesiser of the java.lang.Long.parseLong API
    syn = Synthesizer(
        "java.lang.Long.parseLong",
        "java.lang.Long.parseLong",
        "/root/amuse/synthesis_resource.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.lang.Long.parseLong(java.lang.String)"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "catch",
            tuple(
                [
                    String("NumberFormatException"),
                    Variable("_"),
                    Variable("catch_label"),
                    Variable("_"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # popular APIs from Tabnine

    # 1.
    syn = Synthesizer(
        "java.lang.String.equals",
        "java.lang.String.equals",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call",
            tuple(
                [
                    String("java.lang.String.equals(java.lang.Object)"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument",
            tuple(
                [
                    String("java.lang.String.equals(java.lang.Object)"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 2.
    syn = Synthesizer(
        "java.util.List.add",
        "java.util.List.add",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.List.add"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.util.List.add"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 3. java.lang.Object.getClass
    syn = Synthesizer(
        "java.lang.Object.getClass",
        "java.lang.Object.getClass",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Object.getClass"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 4. java.util.Map.put
    syn = Synthesizer(
        "java.util.Map.put",
        "java.util.Map.put",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Map.put"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.util.Map.put"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Number(0),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele3 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.util.Map.put"),
                    Variable("target_3"),
                    Variable("label_1"),
                    Number(1),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2, ele3]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 5. java.lang.Class.getName
    syn = Synthesizer(
        "java.lang.Class.getName",
        "java.lang.Class.getName",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Class.getName"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 6. java.util.HashMap._init_
    syn = Synthesizer(
        "java.util.HashMap._init_",
        "java.util.HashMap._init_",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.HashMap.<init>"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.HashMap.put"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 7. java.util.Set.add
    syn = Synthesizer(
        "java.util.Set.add",
        "java.util.Set.add",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Set.add"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.util.Set.add"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )
    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 8. java.lang.IllegalArgumentException._init_
    syn = Synthesizer(
        "java.lang.IllegalArgumentException._init_",
        "java.lang.IllegalArgumentException._init_",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.IllegalArgumentException.<init>"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 9. java.lang.StringBuilder.append
    syn = Synthesizer(
        "java.lang.StringBuilder.append",
        "java.lang.StringBuilder.append",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.StringBuilder.append"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.lang.StringBuilder.append"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )
    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 10. java.util.Arrays.asList
    syn = Synthesizer(
        "java.util.Arrays.asList",
        "java.util.Arrays.asList",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Arrays.asList"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.util.Arrays.asList"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )
    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 11. java.util.Collections.emptyList
    syn = Synthesizer(
        "java.util.Collections.emptyList",
        "java.util.Collections.emptyList",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Collections.emptyList"),
                    Variable("label_1"),
                    String("Collections"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 12. java.lang.Integer.parseInt
    syn = Synthesizer(
        "java.lang.Integer.parseInt",
        "java.lang.Integer.parseInt",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Integer.parseInt"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "catch",
            tuple(
                [
                    String("NumberFormatException"),
                    Variable("_"),
                    Variable("catch_label"),
                    Variable("_"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 14. java.io.File._init_
    syn = Synthesizer(
        "java.io.File._init_",
        "java.io.File._init_",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.io.File.<init>"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.io.File.exists"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 15. java.util.Map$Entry.getValue
    syn = Synthesizer(
        "java.util.Map$Entry.getValue",
        "java.util.Map$Entry.getValue",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Map$Entry.getValue"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Map$Entry.getKey"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 16.java.lang.Exception.getMessage
    syn = Synthesizer(
        "java.lang.Exception.getMessage",
        "java.lang.Exception.getMessage",
        "/root/amuse/synthesis_resource2.json",
    )
    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Exception.getMessage"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 17. org.slf4j.Logger.info
    syn = Synthesizer(
        "org.slf4j.Logger.info",
        "org.slf4j.Logger.info",
        "/root/amuse/synthesis_resource2.json",
    )
    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("org.slf4j.Logger.info"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 18. java.lang.Thread.currentThread
    syn = Synthesizer(
        "java.lang.Thread.currentThread",
        "java.lang.Thread.currentThread",
        "/root/amuse/synthesis_resource2.json",
    )
    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Thread.currentThread"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Thread.interrupt"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 19. java.io.IOException._init_
    syn = Synthesizer(
        "java.io.IOException._init_",
        "java.io.IOException._init_",
        "/root/amuse/synthesis_resource2.json",
    )
    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.io.IOException.<init>"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 20. java.util.HashSet._init_ #TODO: suan he cd
    syn = Synthesizer(
        "java.util.HashSet._init_",
        "java.util.HashSet._init_",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.HashSet.<init>"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Set.add"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 21. java.util.Collection.size
    syn = Synthesizer(
        "java.util.Collection.size",
        "java.util.Collection.size",
        "/root/amuse/synthesis_resource2.json",
    )
    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.Collection.size"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 22. java.lang.Math.min #NOTE: path name has $ will cause issue
    syn = Synthesizer(
        "java.lang.Math.min",
        "java.lang.Math.min",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Math.min"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.lang.Math.min"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Number(0),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele3 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.lang.Math.min"),
                    Variable("target_3"),
                    Variable("label_1"),
                    Number(1),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2, ele3]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 23. java.lang.Boolean.valueOf
    syn = Synthesizer(
        "java.lang.Boolean.valueOf",
        "java.lang.Boolean.valueOf",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.Boolean.valueOf"),
                    Variable("label_1"),
                    Variable("target_1"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    ele2 = APIElement(
        Literal(
            "actual_argument_name",
            tuple(
                [
                    String("java.lang.Boolean.valueOf"),
                    Variable("target_2"),
                    Variable("label_1"),
                    Variable("_"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    ele2 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.util.ArrayList.add"),
                    Variable("label_2"),
                    Variable("target_2"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1, ele2]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )

    # 25. java.lang.System.currentTimeMillis
    syn = Synthesizer(
        "java.lang.System.currentTimeMillis",
        "java.lang.System.currentTimeMillis",
        "/root/amuse/synthesis_resource2.json",
    )

    ele1 = APIElement(
        Literal(
            "call_name",
            tuple(
                [
                    String("java.lang.System.currentTimeMillis"),
                    Variable("label_1"),
                    String("System"),
                    Variable("in_meth_1"),
                ]
            ),
            True,
        )
    )

    api_elements_list = [[ele1]]

    result = syn.synthesise(
        api_elements_list, "/root/amuse/documentation/crafted_dl/analyser_new.dl"
    )
